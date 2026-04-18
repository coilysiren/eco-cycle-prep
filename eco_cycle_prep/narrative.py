"""Read a WorldPreview.gif + WorldGenerator.eco and produce a short
narrative description of the generated world.

Intended for use during a roll's Discord post. For now, exposed via
`inv narrate` and fully separate from the `inv roll` pipeline while we
iterate on wording.
"""

import json
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx
from PIL import Image

from . import preview, worldgen

PREVIEW_URL = preview.PREVIEW_URL


# Palette match tolerance. The server keeps block colors stable across
# generations, so we mostly see exact hits; the small window absorbs the
# occasional off-by-one from GIF quantization.
COLOR_TOLERANCE = 6

# Distinct RGB → block-name table. Distilled from the block color map
# the server ships with; each entry corresponds to a block that can
# plausibly show up on top of a chunk column in a freshly generated
# world. `kind` groups blocks into narrative buckets.
# kind values: water, grass, sand, desert, rainforest, cold_forest,
# warm_forest, wetland, taiga, tundra, ice, snow, dirt, limestone,
# sandstone, granite, basalt, ocean_floor, tree_debris, ore, flower, other
BLOCK_CATALOG: list[tuple[int, str, str]] = [
    (0x2B4695, "Water", "water"),
    (0x2B4696, "Water", "water"),
    (0x69AE29, "Grass", "grass"),
    (0xE8D781, "Sand", "sand"),
    (0xD3AD0F, "DesertSand", "desert"),
    (0x007149, "RainforestSoil", "rainforest"),
    (0x2E6739, "ColdForestSoil", "cold_forest"),
    (0x617315, "WarmForestSoil", "warm_forest"),
    (0x467865, "WetlandsSoil", "wetland"),
    (0xB0D1C3, "TaigaSoil", "taiga"),
    (0xB6D5D6, "TundraSoil", "tundra"),
    (0xE2E2E2, "Ice", "ice"),
    (0xF5F5F5, "Snow", "snow"),
    (0x714A32, "Dirt", "dirt"),
    (0xE1E6D2, "Limestone", "limestone"),
    (0xBE7F6C, "Sandstone", "sandstone"),
    (0xA1A1A1, "Granite", "granite"),
    (0x4C4C4C, "Basalt", "basalt"),
    (0x716C53, "OceanSand", "ocean_floor"),
    (0x87673E, "TreeDebris", "tree_debris"),
    (0x303030, "Coal", "ore"),
    (0x975752, "IronOre", "ore"),
    (0xB07620, "CopperOre", "ore"),
    (0xEAC80C, "GoldOre", "ore"),
    (0xFFDBFF, "Fireweed", "flower"),
]

# Kinds that come from biome soil blocks and therefore directly imply
# a biome. Kinds like "grass" or "sand" are ambiguous across biomes.
BIOME_SOIL_KINDS = {
    "rainforest", "cold_forest", "warm_forest", "wetland",
    "taiga", "tundra", "desert",
}

# Kinds that cover land regardless of biome.
LAND_KINDS = {
    "grass", "sand", "desert", "rainforest", "cold_forest", "warm_forest",
    "wetland", "taiga", "tundra", "ice", "snow", "dirt", "limestone",
    "sandstone", "granite", "basalt", "tree_debris", "ore", "flower",
    "other",
}


@dataclass
class Features:
    # Image
    width: int
    height: int
    palette_entries_used: int
    # Palette index → (r, g, b, kind, block_name, pixel_count)
    palette_map: dict[int, dict] = field(default_factory=dict)
    # Pixel breakdown
    total_pixels: int = 0
    water_pixels: int = 0
    land_pixels: int = 0
    kind_pixels: dict[str, int] = field(default_factory=dict)
    # Shapes
    continent_count: int = 0
    island_count: int = 0
    landmass_sizes: list[int] = field(default_factory=list)  # sorted descending
    largest_landmass_pixels: int = 0
    largest_landmass_centroid: tuple[float, float] = (0.0, 0.0)  # normalized [-1, 1]
    lake_count: int = 0
    open_ocean_pixels: int = 0
    coastline_pixels: int = 0
    ice_cap_north: bool = False
    ice_cap_south: bool = False
    # Per-kind spatial stats, normalized to [-1, 1] with origin at map center.
    # cx>0 = east, cy>0 = south. spread is mean pixel distance from centroid
    # in the same normalized space (0 = all in one spot, ~0.5 = map-wide).
    kind_centroids: dict[str, tuple[float, float]] = field(default_factory=dict)
    kind_spreads: dict[str, float] = field(default_factory=dict)
    # Config
    seed: int = 0
    world_w: int = 0
    world_h: int = 0
    map_preset: str = ""
    crater_enabled: bool = False
    biome_weights: dict[str, float] = field(default_factory=dict)
    num_continents_range: tuple[int, int] = (0, 0)
    num_islands_range: tuple[int, int] = (0, 0)
    num_lakes_range: tuple[int, int] = (0, 0)
    num_rivers_range: tuple[int, int] = (0, 0)

    @property
    def land_fraction(self) -> float:
        return self.land_pixels / self.total_pixels if self.total_pixels else 0.0

    @property
    def water_fraction(self) -> float:
        return self.water_pixels / self.total_pixels if self.total_pixels else 0.0

    def land_kind_fraction(self, kind: str) -> float:
        return self.kind_pixels.get(kind, 0) / self.land_pixels if self.land_pixels else 0.0

    @property
    def world_meters(self) -> int:
        """World edge in meters. GIF is 1 pixel per voxel-column, which
        is 1m × 1m in Eco."""
        return self.width


def _classify_rgb(r: int, g: int, b: int) -> tuple[str, str]:
    """Return (block_name, kind). Nearest-neighbour over BLOCK_CATALOG;
    fallback to 'Unknown'/'other' if nothing is within tolerance."""
    best: tuple[str, str] = ("Unknown", "other")
    best_d = 10_000
    for hex_rgb, name, kind in BLOCK_CATALOG:
        br = (hex_rgb >> 16) & 0xFF
        bg = (hex_rgb >> 8) & 0xFF
        bb = hex_rgb & 0xFF
        d = max(abs(r - br), abs(g - bg), abs(b - bb))
        if d < best_d:
            best_d = d
            best = (name, kind)
    if best_d > COLOR_TOLERANCE:
        return "Unknown", "other"
    return best


def _load_image(gif: bytes | Path) -> Image.Image:
    if isinstance(gif, (str, Path)):
        im = Image.open(gif)
    else:
        from io import BytesIO
        im = Image.open(BytesIO(gif))
    im.seek(0)
    if im.mode != "P":
        im = im.convert("P")
    return im


def _components(mask: list[list[bool]]) -> list[int]:
    """Pixel-counts of 4-connected components where mask[y][x] is True."""
    h = len(mask)
    w = len(mask[0]) if h else 0
    seen = [[False] * w for _ in range(h)]
    sizes: list[int] = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0][x0] or seen[y0][x0]:
                continue
            size = 0
            q: deque[tuple[int, int]] = deque([(x0, y0)])
            seen[y0][x0] = True
            while q:
                x, y = q.popleft()
                size += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            sizes.append(size)
    return sizes


def _water_components(water_mask: list[list[bool]]) -> tuple[int, int, int]:
    """Return (open_ocean_pixels, lake_count, ocean_component_count).

    Heuristic: the component(s) touching the image edge are ocean; interior
    components ≥ MIN_LAKE_PIXELS are lakes. Anything smaller is noise
    (river segment artefacts, isolated single-pixel submerged cells)."""
    h = len(water_mask)
    w = len(water_mask[0]) if h else 0
    MIN_LAKE_PIXELS = max(16, (w * h) // 2000)  # ~0.05% of world
    seen = [[False] * w for _ in range(h)]
    open_ocean = 0
    lakes = 0
    oceans = 0
    for y0 in range(h):
        for x0 in range(w):
            if not water_mask[y0][x0] or seen[y0][x0]:
                continue
            size = 0
            touches_edge = False
            q: deque[tuple[int, int]] = deque([(x0, y0)])
            seen[y0][x0] = True
            while q:
                x, y = q.popleft()
                size += 1
                if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                    touches_edge = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and water_mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if touches_edge:
                open_ocean += size
                oceans += 1
            elif size >= MIN_LAKE_PIXELS:
                lakes += 1
    return open_ocean, lakes, oceans


def _largest_component_centroid(
    mask: list[list[bool]],
) -> tuple[int, tuple[float, float]]:
    """Return (size_of_largest, centroid_normalized). Normalized centroid
    is (cx, cy) in [-1, 1] with origin at the image center, +x east, +y
    south (image-space conventions; callers map to compass words)."""
    h = len(mask)
    w = len(mask[0]) if h else 0
    if not w or not h:
        return 0, (0.0, 0.0)
    seen = [[False] * w for _ in range(h)]
    best_size = 0
    best_cx = 0.0
    best_cy = 0.0
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0][x0] or seen[y0][x0]:
                continue
            size = 0
            sx = 0
            sy = 0
            q: deque[tuple[int, int]] = deque([(x0, y0)])
            seen[y0][x0] = True
            while q:
                x, y = q.popleft()
                size += 1
                sx += x
                sy += y
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if size > best_size:
                best_size = size
                best_cx = (sx / size) / (w / 2) - 1.0
                best_cy = (sy / size) / (h / 2) - 1.0
    return best_size, (best_cx, best_cy)


def _coastline_count(
    water_mask: list[list[bool]], land_mask: list[list[bool]]
) -> int:
    """Count land pixels with at least one 4-neighbor water pixel.

    High counts relative to the square-root of land area indicate a ragged,
    inlet-heavy coastline; low counts indicate smooth continental edges."""
    h = len(water_mask)
    w = len(water_mask[0]) if h else 0
    count = 0
    for y in range(h):
        for x in range(w):
            if not land_mask[y][x]:
                continue
            if (
                (x > 0 and water_mask[y][x - 1]) or
                (x < w - 1 and water_mask[y][x + 1]) or
                (y > 0 and water_mask[y - 1][x]) or
                (y < h - 1 and water_mask[y + 1][x])
            ):
                count += 1
    return count


def _kind_spatial_stats(
    pixel_rows: list[list[int]],
    palette_map: dict[int, dict],
    width: int,
    height: int,
) -> tuple[dict[str, tuple[float, float]], dict[str, float]]:
    """Return per-kind centroids (normalized [-1, 1]) and per-kind
    dispersion (mean pixel distance from centroid in normalized units).

    Single pass over all pixels: accumulate sum_x, sum_y, sum_x2, sum_y2,
    and count per kind, then solve for mean + stddev."""
    sums: dict[str, list[int]] = {}  # kind -> [sum_x, sum_y, sum_x2, sum_y2, n]
    for y, row in enumerate(pixel_rows):
        for x, idx in enumerate(row):
            kind = palette_map.get(idx, {}).get("kind", "other")
            s = sums.get(kind)
            if s is None:
                s = [0, 0, 0, 0, 0]
                sums[kind] = s
            s[0] += x
            s[1] += y
            s[2] += x * x
            s[3] += y * y
            s[4] += 1

    hx, hy = width / 2, height / 2
    centroids: dict[str, tuple[float, float]] = {}
    spreads: dict[str, float] = {}
    for kind, (sx, sy, sx2, sy2, n) in sums.items():
        if n == 0:
            continue
        mx = sx / n
        my = sy / n
        var_x = max(0.0, sx2 / n - mx * mx)
        var_y = max(0.0, sy2 / n - my * my)
        # Normalize to [-1, 1] and record centroid + isotropic spread.
        centroids[kind] = (mx / hx - 1.0, my / hy - 1.0)
        spread = ((var_x + var_y) ** 0.5) / max(hx, hy)
        spreads[kind] = spread
    return centroids, spreads


def _ice_caps(
    pixel_rows: list[list[int]],
    palette_map: dict[int, dict],
    height: int,
    width: int,
) -> tuple[bool, bool]:
    """Detect ice/snow bands at the top or bottom edge of the map.

    True if any of the top (or bottom) BAND rows have at least
    MIN_ICE_FRACTION of their width covered by ice/snow pixels."""
    BAND = max(3, height // 20)  # top/bottom 5% band
    MIN_ICE_FRACTION = 0.06
    ice_kinds = {"ice", "snow"}

    def _band_has_ice(y_range: Iterable[int]) -> bool:
        ice = 0
        for y in y_range:
            row = pixel_rows[y]
            for idx in row:
                kind = palette_map.get(idx, {}).get("kind")
                if kind in ice_kinds:
                    ice += 1
        return ice >= MIN_ICE_FRACTION * BAND * width

    return _band_has_ice(range(BAND)), _band_has_ice(range(height - BAND, height))


def extract_features(gif: bytes | Path, config: dict) -> Features:
    im = _load_image(gif)
    w, h = im.size
    palette = im.getpalette() or []
    pixels = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    counts = Counter(pixels)

    palette_map: dict[int, dict] = {}
    kind_pixels: dict[str, int] = {}
    water_pixels = 0
    land_pixels = 0
    for idx, count in counts.items():
        r = palette[idx * 3] if len(palette) > idx * 3 else 0
        g = palette[idx * 3 + 1] if len(palette) > idx * 3 + 1 else 0
        b = palette[idx * 3 + 2] if len(palette) > idx * 3 + 2 else 0
        name, kind = _classify_rgb(r, g, b)
        palette_map[idx] = dict(rgb=(r, g, b), name=name, kind=kind, count=count)
        kind_pixels[kind] = kind_pixels.get(kind, 0) + count
        if kind == "water":
            water_pixels += count
        elif kind in LAND_KINDS:
            land_pixels += count

    # Reshape pixels into rows for connected-component work.
    pixel_rows: list[list[int]] = [pixels[y * w : (y + 1) * w] for y in range(h)]
    water_mask = [[palette_map[p]["kind"] == "water" for p in row] for row in pixel_rows]
    land_mask = [[palette_map[p]["kind"] in LAND_KINDS for p in row] for row in pixel_rows]

    land_sizes = sorted(_components(land_mask), reverse=True)
    largest_size, largest_centroid = _largest_component_centroid(land_mask)
    open_ocean, lake_count, _ = _water_components(water_mask)
    coastline_pixels = _coastline_count(water_mask, land_mask)
    kind_centroids, kind_spreads = _kind_spatial_stats(pixel_rows, palette_map, w, h)

    # Continent vs island split: anything ≥ 1% of total pixels is a continent.
    total_pixels = w * h
    continent_threshold = max(400, total_pixels // 100)
    continent_count = sum(1 for s in land_sizes if s >= continent_threshold)
    # Drop tiny "islands" that are almost certainly single stray pixels
    # from quantization or one-pixel peninsulas.
    min_island = max(4, total_pixels // 10_000)
    island_count = sum(1 for s in land_sizes if min_island <= s < continent_threshold)

    ice_cap_n, ice_cap_s = _ice_caps(pixel_rows, palette_map, h, w)

    # Config slice
    inner = config.get("HeightmapModule", {}).get("Source", {}).get("Config", {})
    crater = config.get("Crater", {}) or {}
    dims = config.get("Dimensions", {}) or {}
    weights = {
        "desert": inner.get("DesertWeight", 0.0),
        "warm_forest": inner.get("WarmForestWeight", 0.0),
        "cool_forest": inner.get("CoolForestWeight", 0.0),
        "taiga": inner.get("TaigaWeight", 0.0),
        "tundra": inner.get("TundraWeight", 0.0),
        "ice": inner.get("IceWeight", 0.0),
        "rainforest": inner.get("RainforestWeight", 0.0),
        "wetland": inner.get("WetlandWeight", 0.0),
        "steppe": inner.get("SteppeWeight", 0.0),
        "high_desert": inner.get("HighDesertWeight", 0.0),
    }

    def _range(d: dict, field: str) -> tuple[int, int]:
        r = d.get(field, {}) or {}
        return int(r.get("min", 0)), int(r.get("max", 0))

    return Features(
        width=w,
        height=h,
        palette_entries_used=len(counts),
        palette_map=palette_map,
        total_pixels=total_pixels,
        water_pixels=water_pixels,
        land_pixels=land_pixels,
        kind_pixels=kind_pixels,
        continent_count=continent_count,
        island_count=island_count,
        landmass_sizes=land_sizes,
        largest_landmass_pixels=largest_size,
        largest_landmass_centroid=largest_centroid,
        lake_count=lake_count,
        open_ocean_pixels=open_ocean,
        coastline_pixels=coastline_pixels,
        kind_centroids=kind_centroids,
        kind_spreads=kind_spreads,
        ice_cap_north=ice_cap_n,
        ice_cap_south=ice_cap_s,
        seed=int(inner.get("Seed", 0)),
        world_w=int(dims.get("WorldWidth", w)),
        world_h=int(dims.get("WorldLength", h)),
        map_preset=str(config.get("MapSizePreset", "")),
        crater_enabled=bool(crater.get("Frequency", 0)) and bool(crater.get("RadiusRange", {}).get("max", 0)),
        biome_weights=weights,
        num_continents_range=_range(inner, "NumContinentsRange"),
        num_islands_range=_range(inner, "NumSmallIslandsRange"),
        num_lakes_range=_range(inner, "NumLakesRange"),
        num_rivers_range=_range(inner, "NumRiversRange"),
    )


# Biome kinds in descending narrative priority (ranked by "how interesting
# is it as a feature"). Ice cap beats rainforest beats desert beats plain
# forest beats grassland.
BIOME_LABELS = {
    "rainforest": "rainforest",
    "cold_forest": "cold forest",
    "warm_forest": "warm forest",
    "wetland": "wetland",
    "taiga": "taiga",
    "tundra": "tundra",
    "desert": "desert",
    "ice": "ice cap",
    "snow": "snowfield",
    "grass": "grassland",
    "sand": "sand",
    "dirt": "bare earth",
}


def _top_biomes(features: Features, n: int = 5) -> list[tuple[str, float]]:
    """Return the top-N biome-indicating land kinds by fraction of land."""
    ranked: list[tuple[str, float]] = []
    for kind in BIOME_SOIL_KINDS | {"ice", "snow"}:
        frac = features.land_kind_fraction(kind)
        if frac >= 0.015:  # ≥1.5% of land
            ranked.append((kind, frac))
    ranked.sort(key=lambda kv: kv[1], reverse=True)
    return ranked[:n]


# Config biome weight field → kind mapping, for realized-vs-target deltas.
# "cool_forest" in config = our "cold_forest" kind.
CONFIG_TO_KIND = {
    "desert": "desert",
    "warm_forest": "warm_forest",
    "cool_forest": "cold_forest",
    "rainforest": "rainforest",
    "wetland": "wetland",
    "taiga": "taiga",
    "tundra": "tundra",
    "ice": "ice",
}


def _direction(cx: float, cy: float, *, edge_bias: float = 0.25) -> str:
    """Map a normalized centroid (cx, cy) with cx>0 east / cy>0 south into
    a compass-ish phrase. Returns "center" if the centroid sits near the
    origin relative to `edge_bias`. This uses image-up == north convention,
    which is how players read a top-down preview."""
    ns = -cy  # flip y so positive == north
    ew = cx
    # "center" when both magnitudes are small.
    if abs(ns) < edge_bias and abs(ew) < edge_bias:
        return "center of the map"

    def axis(mag: float, pos: str, neg: str) -> str:
        if mag > edge_bias:
            return pos
        if mag < -edge_bias:
            return neg
        return ""

    ns_word = axis(ns, "north", "south")
    ew_word = axis(ew, "east", "west")
    parts = [p for p in (ns_word, ew_word) if p]
    if len(parts) == 2:
        return f"{parts[0]}{parts[1]}"  # "northeast", "southwest", etc.
    if len(parts) == 1:
        return parts[0]
    return "center"


def _locational_phrase(kind: str, f: Features, *, terse: bool = False) -> str:
    """'in the southeast' / 'spread across the map' depending on spread.

    If terse=True, collapses long-form phrasings into compact forms
    suitable for appearing inside a comma-separated list."""
    center = f.kind_centroids.get(kind)
    spread = f.kind_spreads.get(kind, 0.0)
    if center is None:
        return ""
    direction = _direction(*center)
    central = direction == "center of the map"
    # Tight cluster.
    if spread <= 0.28:
        if central:
            return "clustered near the center"
        return f"clustered in the {direction}"
    # Medium spread.
    if spread <= 0.40:
        if central:
            return "distributed unevenly across the interior"
        if terse:
            return f"favoring the {direction}"
        return f"concentrated toward the {direction}"
    # Large spread.
    if central:
        return "scattered across the map"
    if terse:
        return f"leaning {direction}"
    return f"spread broadly, leaning {direction}"


def _paragraph_shape(f: Features) -> str:
    water_pct = round(f.water_fraction * 100)
    land_pct = 100 - water_pct
    world_m = f.world_meters
    chunks = f.world_w  # Dimensions.WorldWidth is in chunks

    if f.continent_count == 0:
        return (
            f"A {world_m}-meter square world that reads as almost pure ocean "
            f"({water_pct}% open water). No landmass is large enough to call "
            "a continent; whatever land appears is scattered micro-islands."
        )

    continent_words = {1: "A single continent", 2: "Two continents",
                       3: "Three continents", 4: "Four continents",
                       5: "Five continents"}
    continent_word = continent_words.get(f.continent_count,
                                          f"{f.continent_count} continents")
    continent_verb = "occupies" if f.continent_count == 1 else "occupy"

    # Relative scale of the largest vs total land.
    largest_frac = f.largest_landmass_pixels / f.total_pixels if f.total_pixels else 0
    largest_dir = _direction(*f.largest_landmass_centroid, edge_bias=0.20)

    # Islands clause
    if f.island_count == 0:
        island_clause = "with no separate islands of note"
    elif f.island_count == 1:
        island_clause = "plus one outlying island"
    elif f.island_count <= 4:
        island_clause = f"flanked by {f.island_count} smaller islands"
    else:
        island_clause = f"ringed by an archipelago of {f.island_count} islands"

    # Opening sentence.
    lead = (
        f"{continent_word} {continent_verb} {land_pct}% of a {world_m}-meter "
        f"({chunks}-chunk) square world, {island_clause}."
    )

    # Second sentence: anchoring and scale.
    anchor_line = ""
    if f.continent_count == 1 and largest_dir != "center of the map":
        anchor_line = f" The main landmass is anchored in the {largest_dir}."
    elif f.continent_count > 1 and largest_frac > 0.40:
        if largest_dir != "center of the map":
            anchor_line = (f" The biggest landmass anchors the {largest_dir} "
                           f"and dwarfs its neighbors.")
        else:
            anchor_line = " One landmass fills the middle of the world and dwarfs the rest."
    elif f.continent_count > 1 and 0.25 < largest_frac <= 0.40:
        anchor_line = " The continents differ noticeably in scale but none overwhelms the others."

    # Lake + coastline sentence.
    lake_words = {0: "no inland lakes",
                  1: "one inland lake",
                  2: "two inland lakes",
                  3: "three inland lakes",
                  4: "four inland lakes",
                  5: "five inland lakes",
                  6: "six inland lakes",
                  7: "seven inland lakes"}
    lake_phrase = lake_words.get(f.lake_count, f"{f.lake_count} inland lakes")

    import math
    coast_desc = ""
    if f.land_pixels > 0:
        # Ratio of coast-adjacent land pixels to sqrt(land area). Calibrated
        # from samples: ~0.9 for a single smooth island, ~1.1+ for moderately
        # ragged, 1.5+ for finger-like coasts.
        ruggedness = f.coastline_pixels / (math.sqrt(f.land_pixels) * 4.0)
        if ruggedness > 1.5:
            coast_desc = "deeply indented, full of inlets and peninsulas"
        elif ruggedness > 1.1:
            coast_desc = "moderately ragged, with a few pronounced bays"
        else:
            coast_desc = "smooth, with few bays or peninsulas"

    if f.lake_count == 0:
        water_line = f" No lakes break up the interior; the coastlines are {coast_desc}." if coast_desc else ""
    else:
        lake_verb = "breaks" if f.lake_count == 1 else "break"
        water_line = (
            f" {lake_phrase.capitalize()} {lake_verb} up the interior, and "
            f"the coastlines are {coast_desc}." if coast_desc
            else f" {lake_phrase.capitalize()} {lake_verb} up the interior."
        )

    return lead + anchor_line + water_line


def _paragraph_biomes(f: Features) -> str:
    top = _top_biomes(f, n=5)
    if not top:
        return "The preview doesn't resolve clear biome signatures from soil colors alone."

    # Dominant biome clause.
    first_kind, first_frac = top[0]
    first_label = BIOME_LABELS.get(first_kind, first_kind)
    first_loc = _locational_phrase(first_kind, f, terse=True)
    if first_frac >= 0.30:
        lead = f"The land is dominated by {first_label}"
    elif first_frac >= 0.20:
        lead = f"{first_label.capitalize()} leads the biome mix"
    elif first_frac >= 0.10:
        lead = f"{first_label.capitalize()} is the single biggest biome"
    else:
        lead = f"{first_label.capitalize()} narrowly edges out the others"

    lead += f" ({round(first_frac * 100)}% of land, {first_loc})"

    # Runners-up with their own locations — keeps the paragraph from
    # being a flat list. Terse locational phrasing inside the list so
    # three back-to-back entries don't all repeat "spread broadly."
    runner_bits: list[str] = []
    for kind, frac in top[1:4]:
        label = BIOME_LABELS.get(kind, kind)
        loc = _locational_phrase(kind, f, terse=True)
        runner_bits.append(f"{label} at {round(frac * 100)}% {loc}")
    if runner_bits:
        if len(runner_bits) == 1:
            lead += f". Behind it, {runner_bits[0]}"
        else:
            lead += (". Behind it, "
                     + ", ".join(runner_bits[:-1])
                     + f", and {runner_bits[-1]}")
    lead += "."

    # Config-vs-realized commentary for the handful of biomes with
    # non-trivial targets. Call out big misses in either direction.
    deltas: list[str] = []
    for cfg_key, kind in CONFIG_TO_KIND.items():
        target = f.biome_weights.get(cfg_key, 0.0)
        if target < 0.02:
            continue  # not worth commenting on
        realized = f.land_kind_fraction(kind)
        delta = realized - target
        if delta > 0.08:
            deltas.append(
                f"{BIOME_LABELS.get(kind, kind)} overshot its "
                f"{round(target * 100)}% target (now {round(realized * 100)}%)"
            )
        elif delta < -0.08 and target >= 0.10:
            deltas.append(
                f"{BIOME_LABELS.get(kind, kind)} underperformed its "
                f"{round(target * 100)}% target (only {round(realized * 100)}%)"
            )
        elif realized < 0.01 and target >= 0.03:
            deltas.append(
                f"{BIOME_LABELS.get(kind, kind)} is nearly invisible on the "
                f"preview despite a {round(target * 100)}% target"
            )

    climate = ""
    if deltas:
        if len(deltas) == 1:
            climate = f" Compared to the config weights, {deltas[0]}."
        else:
            climate = (" Compared to the config weights, "
                       + ", ".join(deltas[:-1])
                       + f", and {deltas[-1]}.")

    # Polar cap callout
    cap = ""
    if f.ice_cap_north and f.ice_cap_south:
        cap = " Ice caps ride both the northern and southern edges."
    elif f.ice_cap_north:
        cap = " A visible ice cap rides the northern edge."
    elif f.ice_cap_south:
        cap = " A visible ice cap rides the southern edge."

    # Overall climate characterization from the biome mix.
    hot = f.land_kind_fraction("desert") + f.land_kind_fraction("rainforest") + f.land_kind_fraction("warm_forest")
    cold = f.land_kind_fraction("cold_forest") + f.land_kind_fraction("taiga") + f.land_kind_fraction("tundra") + f.land_kind_fraction("ice") + f.land_kind_fraction("snow")
    wet = f.land_kind_fraction("rainforest") + f.land_kind_fraction("wetland")
    dry = f.land_kind_fraction("desert")
    mood_bits: list[str] = []
    if hot - cold > 0.12:
        mood_bits.append("warm overall")
    elif cold - hot > 0.12:
        mood_bits.append("cool overall")
    if wet - dry > 0.08:
        mood_bits.append("wet")
    elif dry - wet > 0.06:
        mood_bits.append("dry")
    mood = ""
    if mood_bits:
        mood = f" Climate reads {' and '.join(mood_bits)}."

    return lead + mood + climate + cap


def _paragraph_geology(f: Features) -> str:
    """Third paragraph: surface stone, ore, notable geological features."""
    bits: list[str] = []

    granite = f.land_kind_fraction("granite")
    sandstone = f.land_kind_fraction("sandstone")
    limestone = f.land_kind_fraction("limestone")
    basalt_frac = f.kind_pixels.get("basalt", 0) / f.total_pixels if f.total_pixels else 0
    ocean_floor = f.kind_pixels.get("ocean_floor", 0) / f.total_pixels if f.total_pixels else 0
    dirt_frac = f.land_kind_fraction("dirt")

    stone_bits: list[str] = []
    if granite > 0.04:
        stone_bits.append(f"granite ({round(granite * 100)}%) cutting through the forested zones")
    elif granite > 0.01:
        stone_bits.append(f"granite outcrops ({round(granite * 100)}%)")
    if limestone > 0.02:
        stone_bits.append(f"limestone ({round(limestone * 100)}%) exposed across grassland and coast")
    elif limestone > 0.005:
        stone_bits.append(f"limestone ({round(limestone * 100)}%)")
    if sandstone > 0.02:
        stone_bits.append(f"sandstone ({round(sandstone * 100)}%) rising out of the desert")
    elif sandstone > 0.005:
        stone_bits.append(f"sandstone ({round(sandstone * 100)}%)")

    if stone_bits:
        if len(stone_bits) == 1:
            bits.append("Visible stone is mostly " + stone_bits[0])
        else:
            bits.append("Visible stone is mixed: "
                       + ", ".join(stone_bits[:-1])
                       + f", and {stone_bits[-1]}")
    else:
        bits.append("Stone exposure is light; most rock sits under soil rather than breaking through")

    # Ore seams on the surface — a real player-facing tell.
    ore_px = f.kind_pixels.get("ore", 0)
    if ore_px > 0:
        # Inspect which ore kinds are visible.
        ore_names: list[str] = []
        for idx_meta in f.palette_map.values():
            if idx_meta.get("kind") != "ore":
                continue
            name = idx_meta.get("name", "")
            if name == "IronOre":
                ore_names.append("iron")
            elif name == "Coal":
                ore_names.append("coal")
            elif name == "CopperOre":
                ore_names.append("copper")
            elif name == "GoldOre":
                ore_names.append("gold")
        ore_names = sorted(set(ore_names))
        if ore_names:
            bits.append("Seams of "
                       + ("/".join(ore_names))
                       + " break through to the surface — an early read on mining accessibility")
        else:
            bits.append("A few unidentified ore patches break through to the surface")

    # Ocean-floor glimpses (shallow water or coastal basalt).
    if basalt_frac > 0.01 or ocean_floor > 0.005:
        bits.append(
            "shallow coastal water shows seafloor through it in places"
        )

    # Tundra/dirt exposure implies frost damage; callers can read that as
    # 'tough starting biome'.
    if dirt_frac > 0.05:
        bits.append(
            f"bare earth occupies {round(dirt_frac * 100)}% of the land, usually a sign of tundra and high-elevation peaks"
        )

    # Crater-bearing worlds (disabled by default on Sirens).
    if f.crater_enabled:
        bits.append("and impact craters scar the terrain, visible as dark circular pits")

    # Render: join into 1–2 sentences.
    if not bits:
        return ""
    # First bit is a lead-in; subsequent bits are appended with commas/periods.
    if len(bits) == 1:
        return bits[0] + "."
    return bits[0] + ". " + ". ".join(b[0].upper() + b[1:] for b in bits[1:]) + "."


def narrate(features: Features) -> str:
    paras = [
        _paragraph_shape(features),
        _paragraph_biomes(features),
    ]
    geo = _paragraph_geology(features)
    if geo:
        paras.append(geo)
    return "\n\n".join(paras)


def _fetch_live_gif() -> bytes:
    r = httpx.get(PREVIEW_URL, params={"discriminator": int(time.time())},
                  timeout=httpx.Timeout(20.0, connect=10.0))
    r.raise_for_status()
    return r.content


def run(
    *,
    gif_path: Path | None = None,
    config_path: Path | None = None,
    show_features: bool = False,
) -> None:
    cfg_path = config_path or worldgen.WORLDGEN_PATH
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))

    if gif_path is not None:
        gif_data: bytes | Path = Path(gif_path)
        source = str(gif_path)
    else:
        gif_data = _fetch_live_gif()
        source = PREVIEW_URL

    features = extract_features(gif_data, cfg)

    if show_features:
        print("=== features ===")
        print(f"source:                 {source}")
        print(f"size:                   {features.width}x{features.height}")
        print(f"palette entries used:   {features.palette_entries_used}")
        print(f"water / land:           "
              f"{features.water_fraction:.1%} / {features.land_fraction:.1%}")
        print(f"continents / islands:   "
              f"{features.continent_count} / {features.island_count}")
        print(f"lakes:                  {features.lake_count}")
        print(f"ice cap N / S:          "
              f"{features.ice_cap_north} / {features.ice_cap_south}")
        print(f"seed:                   {features.seed}")
        print(f"crater enabled:         {features.crater_enabled}")
        print(f"coastline pixels:       {features.coastline_pixels}")
        print(f"largest landmass ctr:   "
              f"({features.largest_landmass_centroid[0]:+.2f}, "
              f"{features.largest_landmass_centroid[1]:+.2f}) "
              f"[-1..1, +x east, +y south]")
        print("biome pixel breakdown (land fraction, centroid, spread):")
        for kind in sorted(features.kind_pixels, key=lambda k: -features.kind_pixels[k]):
            frac = features.land_kind_fraction(kind)
            if frac > 0 or kind == "water":
                label = "water" if kind == "water" else kind
                cx, cy = features.kind_centroids.get(kind, (0.0, 0.0))
                sp = features.kind_spreads.get(kind, 0.0)
                print(f"  {label:15s} {features.kind_pixels[kind]:>10d}  "
                      f"{frac * 100:5.1f}% of land  "
                      f"ctr=({cx:+.2f},{cy:+.2f}) spread={sp:.2f}")
        print()
        print("=== narrative ===")
    print(narrate(features))

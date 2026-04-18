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
    largest_landmass_pixels: int = 0
    lake_count: int = 0
    open_ocean_pixels: int = 0
    ice_cap_north: bool = False
    ice_cap_south: bool = False
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
    open_ocean, lake_count, _ = _water_components(water_mask)

    # Continent vs island split: anything ≥ 1% of total pixels is a continent.
    total_pixels = w * h
    continent_threshold = max(400, total_pixels // 100)
    continent_count = sum(1 for s in land_sizes if s >= continent_threshold)
    island_count = sum(1 for s in land_sizes if s < continent_threshold)
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
        largest_landmass_pixels=land_sizes[0] if land_sizes else 0,
        lake_count=lake_count,
        open_ocean_pixels=open_ocean,
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


def _top_biomes(features: Features, n: int = 4) -> list[tuple[str, float]]:
    """Return the top-N biome-indicating land kinds by fraction of land."""
    ranked: list[tuple[str, float]] = []
    for kind in BIOME_SOIL_KINDS | {"ice", "snow"}:
        frac = features.land_kind_fraction(kind)
        if frac >= 0.015:  # ≥1.5% of land
            ranked.append((kind, frac))
    ranked.sort(key=lambda kv: kv[1], reverse=True)
    return ranked[:n]


def _shape_sentence(f: Features) -> str:
    water_pct = round(f.water_fraction * 100)
    land_pct = 100 - water_pct
    if f.continent_count == 0:
        # Pathological — the whole world is water or nearly so.
        return (
            f"An almost entirely submerged world ({water_pct}% open water, "
            f"no landmass large enough to call a continent)."
        )
    continent_words = {1: "One continent", 2: "Two continents", 3: "Three continents",
                       4: "Four continents", 5: "Five continents"}
    continent_word = continent_words.get(f.continent_count, f"{f.continent_count} continents")

    if f.island_count == 0:
        island_clause = ""
    elif f.island_count == 1:
        island_clause = "; one outlying island"
    elif f.island_count <= 4:
        island_clause = f", flanked by {f.island_count} smaller islands"
    else:
        island_clause = f"; a scattered archipelago of {f.island_count} islands surrounds them"

    largest_frac = f.largest_landmass_pixels / f.total_pixels if f.total_pixels else 0
    dominant_note = ""
    if f.continent_count >= 2 and largest_frac > 0.35:
        dominant_note = ". The largest dwarfs the rest"

    lake_words = {1: "One inland lake", 2: "Two inland lakes",
                  3: "Three inland lakes", 4: "Four inland lakes",
                  5: "Five inland lakes"}
    if f.lake_count == 0:
        lake_clause = ""
    elif f.lake_count == 1:
        lake_clause = " One inland lake breaks up the interior."
    else:
        word = lake_words.get(f.lake_count, f"{f.lake_count} inland lakes")
        lake_clause = f" {word} break up the interior."

    return (
        f"{continent_word} on a {land_pct}% land / {water_pct}% water map"
        f"{island_clause}{dominant_note}.{lake_clause}"
    )


def _climate_sentence(f: Features) -> str:
    top = _top_biomes(f, n=4)
    if not top:
        return "The preview doesn't resolve clear biome signatures."

    first_kind, first_frac = top[0]
    first_label = BIOME_LABELS.get(first_kind, first_kind)

    # Adjective scales with how dominant the top biome is.
    if first_frac >= 0.35:
        lead = f"The land is dominated by {first_label}"
    elif first_frac >= 0.20:
        lead = f"The land leans heavily toward {first_label}"
    elif first_frac >= 0.10:
        lead = f"The biggest biome on land is {first_label}"
    else:
        lead = f"{first_label.capitalize()} is the largest single biome, though no one biome dominates"

    lead = f"{lead} ({round(first_frac * 100)}%)"

    rest = top[1:]
    if rest:
        parts = [f"{BIOME_LABELS.get(k, k)} at {round(frac * 100)}%"
                 for k, frac in rest]
        if len(parts) == 1:
            lead += f", backed by {parts[0]}"
        else:
            lead += ", with " + ", ".join(parts[:-1]) + f", and {parts[-1]} filling in"

    cap_bits: list[str] = []
    if f.ice_cap_north and f.ice_cap_south:
        cap_bits.append("ice caps at both poles")
    elif f.ice_cap_north:
        cap_bits.append("an ice cap along the northern edge")
    elif f.ice_cap_south:
        cap_bits.append("an ice cap along the southern edge")
    if cap_bits:
        lead += f", and {cap_bits[0]}"

    return lead + "."


def _geology_sentence(f: Features) -> str:
    """Optional third sentence: rare/notable features worth calling out."""
    bits: list[str] = []
    granite = f.land_kind_fraction("granite")
    sandstone = f.land_kind_fraction("sandstone")
    limestone = f.land_kind_fraction("limestone")
    basalt = f.kind_pixels.get("basalt", 0) / f.total_pixels if f.total_pixels else 0

    if granite > 0.05:
        bits.append("granite cliffs cut through the forests")
    elif sandstone > 0.03:
        bits.append("sandstone ridges rise out of the desert")
    elif limestone > 0.03:
        bits.append("limestone outcrops stripe the plains")

    # Ore exposure — usually tiny, but any visible presence is narrative-worthy.
    ore = f.kind_pixels.get("ore", 0)
    if ore > 10:
        bits.append("with a few surface ore seams visible from the air")

    if basalt > 0.02:
        bits.append("basalt showing through shallow coastal water")

    if f.crater_enabled:
        bits.append("impact craters scar the terrain")

    if not bits:
        return ""
    return ", ".join(bits).capitalize().rstrip(".") + "."


def narrate(features: Features) -> str:
    lines = [
        _shape_sentence(features),
        _climate_sentence(features),
    ]
    tail = _geology_sentence(features)
    if tail:
        lines.append(tail)
    return "\n\n".join(lines)


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
        print("biome pixel breakdown (land fraction):")
        for kind in sorted(features.kind_pixels, key=lambda k: -features.kind_pixels[k]):
            frac = features.land_kind_fraction(kind)
            if frac > 0 or kind == "water":
                label = "water" if kind == "water" else kind
                print(f"  {label:15s} {features.kind_pixels[kind]:>10d}  "
                      f"{frac * 100:5.1f}% of land")
        print()
        print("=== narrative ===")
    print(narrate(features))

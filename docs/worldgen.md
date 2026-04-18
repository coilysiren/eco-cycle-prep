# World generation reference

Reference notes for anything in this repo that reads `WorldGenerator.eco`
or parses `WorldPreview.gif`. Sourced from the public Eco modding wiki
(<https://wiki.play.eco/en/Modding>), the auto-generated modding docs
(<https://docs.play.eco/>), the EcoModKit reference repo
(<https://github.com/StrangeLoopGames/EcoModKit>), the shape of our own
`eco-configs/Configs/WorldGenerator.eco`, and direct observation of the
preview GIF the server renders.

Motivation: the `inv roll` pipeline posts a preview GIF to Discord after
each seed roll (see `eco_cycle_prep/roll.py`). We want to attach a short
narrative ("three continents, a dominant cold-forest in the east, two
rivers, a polar ice cap in the north") alongside the image. That
narrative is derived from two inputs:

1. The **config JSON** at `eco-configs/Configs/WorldGenerator.eco` — plus
   the current `Seed`. Gives us target biome weights, continent/island
   counts, lake/river counts, world size, crater frequency.
2. The **rendered preview GIF** at
   `http://eco.coilysiren.me:3001/Layers/WorldPreview.gif`. Gives us the
   actual realized biome distribution, rough continent shapes, and water
   layout.

## The generation pipeline (high level)

1. **Seed the RNG** — `HeightmapModule.Source.Config.Seed` in
   `WorldGenerator.eco`. `0` means "pick one at generation time"; our
   `worldgen.py` always writes a concrete value before rolling.
2. **Sample cell centers** via a Poisson-disc sampler. Approximate cell
   count is `(worldSize / PointRadius)²`. With our `PointRadius=10` on a
   100×100 world that's ~100 cells; on the default 720×720 it's ~5,000.
3. **Build a Voronoi graph** over those cells. Sites wrap at the world
   edges so the map tiles seamlessly.
4. **Lay out continents and islands** — `NumContinents` and
   `NumSmallIslands` are drawn once from their `...Range` fields and
   scaled by world size. `LandPercent` controls ocean/land split.
5. **Assign biomes** greedily against the `*Weight` knobs, respecting
   "bad neighbor" exclusions (deserts repel forests, rainforests repel
   cold forests, taigas/tundras/ice repel grassland — see the biome
   catalog below).
6. **Compute elevation per cell** from noise plus the biome's elevation
   range, clamped by distance-from-ocean via `MaxElevationOceanDistance`
   and `ElevationPower`.
7. **Place rivers and lakes**. `NumRivers` and `NumLakes` are sampled
   from ranges. Lakes only spawn in forest / grassland / taiga / wetland
   biomes. Rivers flow downhill from high cells to ocean or lakes,
   avoiding each other by `RiverCellAvoidance` meters.
8. **Spawn surface blocks** per column using the `TerrainModule` chain —
   each biome has a `BiomeTerrainModule` that picks blocks at each
   depth (dirt over rockysoil over limestone, etc.).
9. **Cliff extrusion and craters** run after the base terrain.
   `(WorldWidth * WorldLength) * Crater.Frequency` is the expected
   crater count; Sirens currently has `Frequency = 0` so there are
   none.
10. **Render preview GIF** — one frame, top-block color at every (x, y),
    with water override for submerged columns.

## `WorldGenerator.eco` — fields we care about

Top-level shape:

```
{
  "Dimensions":        { "WorldLength": N, "WorldWidth": N },
  "MaxBuildHeight":    int,
  "MaxGenerationHeight": int,
  "MapSizePreset":     "Small" | "Medium" | "Large",
  "Crater":            { "Frequency": f, "RadiusRange": {min,max}, "DepthRange": {min,max} },
  "HeightmapModule": {
    "$type":  "Eco.WorldGenerator.EcoTerraceNode, Eco.WorldGenerator",
    "Power":  int,
    "TerracePoints": int,
    "Source": {
      "$type": "Eco.WorldGenerator.VoronoiModule, Eco.WorldGenerator",
      "OutputIndex": 0,
      "Config": { ...VoronoiWorldGeneratorConfig... }
    }
  },
  "RainfallModule":    { ..., "Config": {"$ref": ...}, "OutputIndex": 2 },
  "TemperatureModule": { ..., "Config": {"$ref": ...}, "OutputIndex": 3 },
  "TerrainModule":     { "Modules": [ BiomeTerrainModule per biome ] }
}
```

The inner `Config` block (`VoronoiWorldGeneratorConfig`) — all knobs a
narrative generator can reason about:

| Field | Default | What it controls |
|---|---|---|
| `Seed` | 0 = random | RNG seed |
| `PointRadius` | 10m | Voronoi cell size; smaller = more, finer cells |
| `LandPercentRange` | .65–.75 | Ocean/land split (randomized within range) |
| `CoastlineSize` | 1 | Cells deep of coast |
| `ShallowOceanSize` | 2 | Cells deep of shallow ocean |
| `DesertWeight` | .15 | Biome target % (land-weighted) |
| `WarmForestWeight` | .20 | " |
| `CoolForestWeight` | .22 | " |
| `TaigaWeight` | .08 | " |
| `TundraWeight` | .03 | " |
| `IceWeight` | .01 | " |
| `RainforestWeight` | .15 | " |
| `WetlandWeight` | .04 | " |
| `SteppeWeight` | .10 | " (high-elevation grassland) |
| `HighDesertWeight` | .05 | " (high-elevation desert) |
| `NumContinentsRange` | 1–3 | # landmasses, randomized |
| `NumSmallIslandsRange` | 1–3 | # islands |
| `IslandWeight` | .05 | % of land-like cells that become islands |
| `ContinentAvoidRange` | 8–16 | Min distance between continents |
| `IslandAvoidRange` | 4–8 | " for islands |
| `NumRainforests / NumWarmForests / NumCoolForests / NumTaigas / NumTundras / NumIces / NumDeserts / NumWetlands / NumHighDeserts / NumSteppes` | 1 each | Min # distinct biome blobs (can merge) |
| `NumLakesRange` | 2–4 | Lakes to try to place |
| `LakeSizeRange` | .0018–.003 | Fraction of world per lake |
| `NumRiversRange` | 1–3 | Rivers to try to place |
| `RiverCellWidth` | 10m | Visual width of rivers in preview |
| `RiverCellAvoidance` | 2m | Min gap between rivers |
| `MaxElevationOceanDistance` | 12 | Higher = steeper mountains inland |
| `ElevationPower` | 2 | Gradient exponent — higher = flatter coasts, steeper peaks |
| `AutoScale` / `AutoScaleExponent` | true / .25 | Autoscale biome/continent counts off the 720m baseline |

**Sirens' current tuning** (live `WorldGenerator.eco` as of this writing):
72-chunk world (**720×720-pixel preview**), `MaxElevationOceanDistance=10`,
`ElevationPower=2`, `TerracePoints=41`, **craters disabled**
(`Frequency=0`), 4–8 lakes, 2–5 rivers, 1–3 continents, 1–3 islands.
Biome weights match defaults with minor tweaks
(`CoolForestWeight=.22`, `SteppeWeight=.10`). Each `Num*` biome count
is 1.

**Autoscale note**: `ScaleModifier = (pixelSize / 720)^AutoScaleExponent`.
At our current 720-pixel size that's exactly `1.0`, so `NumContinents`,
`NumLakes`, `NumRivers`, and `NumSmallIslands` are used unscaled. If
Sirens ever drops below (or pushes above) the 720-baseline, narrative
code that quotes "this world has N continents" from config alone
should apply the scaling factor — or just count realized land blobs in
the GIF, which is what `narrative.py` does.

## The biome catalog

Thirteen primary biomes plus two sub-biomes. Each has an
`ElevationRange`, `TemperatureRange` (0–1), `MoistureRange` (0–1), a
minimap color (what you see in-game on the map panel), and a prevailing
rock (what appears on cliffs and extruded overhangs):

| Biome | Elev | Temp | Moist | Minimap color | Prevailing rock | Surface in preview |
|---|---|---|---|---|---|---|
| DeepOcean | −1…−.4 | 0….4 | 0…1 | SteelBlue | Basalt | water (see below) |
| Ocean | −.3…−.05 | .4…1 | 0…1 | LightSkyBlue | Basalt | water |
| Coast | .02….1 | any | any | LightGoldenrodYellow | Limestone | Limestone / Sand |
| WarmCoast | .05….1 | any | any | LightGoldenrodYellow | Sandstone | Sand |
| ColdCoast | .05….1 | any | any | LightCyan | Limestone | Limestone |
| Grassland | .02….4 | .4….8 | .3….5 | LightGreen | Limestone | Grass |
| Steppe | .325….4 | .4….8 | .3….5 | LightGreen | Limestone | Grass |
| WarmForest | .1….5 | .5….8 | .5….6 | DarkGoldenrod | Granite | Grass + warm tree stumps |
| ColdForest | .1….7 | .2….5 | .5….6 | ForestGreen | Granite | Grass + cold tree stumps |
| RainForest | .1….5 | .6….8 | .7…1 | LightSeaGreen | Shale | Grass + ceiba/redwood debris |
| Desert | .02….2 | .7…1 | 0….3 | SandyBrown | Sandstone | Sand |
| HighDesert | .225….3 | .7…1 | 0….3 | SandyBrown | Sandstone | Sand |
| Taiga | .3…1 | .2….3 | .2….5 | OliveDrab | Granite | Grass (cool) |
| Tundra | .4…1 | .1….2 | 0….6 | DarkKhaki | Granite | Dirt |
| Ice | .6…1 | 0….1 | 0….6 | White | Granite | Ice |
| Wetland | .02….3 | .4….6 | .6….8 | DarkGreen | Shale | Grass (swampy) |

"Bad neighbor" exclusions that shape generated worlds:

- Rainforest repels ColdForest (range 3)
- ColdForest repels all coasts (range 3)
- Desert repels ColdForest, WarmForest, RainForest, Wetland (range 1)
- Taiga / Tundra / Ice all repel Grassland (ranges 2, 1, 1)
- Wetland repels RainForest (range 3)

## `WorldPreview.gif` — layout and palette

Key facts for a Python parser:

- **Format**: GIF89a, 8-bit indexed, 256-color global palette.
- **Frames**: **one.** The server writes a single static frame per
  generation, not an animation. If `Pillow`'s `n_frames` comes back as
  anything other than 1, that's a signal that upstream behavior has
  changed — worth re-validating before shipping narrative based on it.
- **Dimensions**: **pixel size = `WorldWidth × 10` in each axis** (Eco
  chunks are 10 voxels wide; each voxel-column renders as one pixel).
  `Dimensions.WorldWidth / .WorldLength` in the config are **chunks,
  not pixels.** Sirens currently runs `WorldWidth = WorldLength = 72`,
  which produces a **720×720** GIF.
- **Content rule**: each pixel is the palette index of the top block at
  that (x, y). Submerged columns are overridden to a single reserved
  "water" palette index, so rivers and lakes read as one flat color
  regardless of depth.
- **Palette**: 256 × 3 bytes. Entry 0 is black. Entries 1..N are RGB
  tuples, one per unique top-block color actually present in the
  world. Realized palette size tracks how many distinct block kinds
  happened to land on top — a freshly-rolled Sirens world typically
  uses ~20–30 entries out of 256. Index 254 is reserved in the format;
  index 255 is transparent and unused in the single-frame output.

### Block hex colors most relevant to biome inference

Use these to reverse a GIF pixel back to a biome guess. Match on RGB in
the palette — alpha is forced to `0xFF` at write time (water keeps its
`0x64` alpha in the raw block color but renders opaque in the GIF).

**Every biome has its own `<Biome>Soil` block**, with a distinctive
color. That gives us a direct pixel → biome mapping for land, not just
the generic grass/sand fallbacks an earlier draft of this file
described.

| Block | Hex | Kind | Maps to biome |
|---|---|---|---|
| Water | `0x2B4696` | water | Ocean / DeepOcean / rivers / lakes |
| Grass | `0x69AE29` | grass | Grassland, Steppe, forest tops generally |
| Sand | `0xE8D781` | sand | WarmCoast, beaches, ambient desert sand |
| DesertSand | `0xD3AD0F` | desert | **Desert** biome (specifically) |
| RainforestSoil | `0x007149` | rainforest | **RainForest** biome |
| ColdForestSoil | `0x2E6739` | cold_forest | **ColdForest** biome |
| WarmForestSoil | `0x617315` | warm_forest | **WarmForest** biome |
| WetlandsSoil | `0x467865` | wetland | **Wetland** biome |
| TaigaSoil | `0xB0D1C3` | taiga | **Taiga** biome |
| TundraSoil | `0xB6D5D6` | tundra | **Tundra** biome |
| Snow | `0xF5F5F5` | snow | Ice biome, high-elevation peaks |
| Ice | `0xE2E2E2` | ice | Ice biome, frozen water |
| Dirt | `0x714A32` | dirt | Exposed earth, often Tundra edges |
| Limestone | `0xE1E6D2` | limestone | ColdCoast, Grassland rocks |
| Sandstone | `0xBE7F6C` | sandstone | Desert cliffs |
| Granite | `0xA1A1A1` | granite | Forest / Taiga / Tundra cliffs |
| Basalt | `0x4C4C4C` | basalt | DeepOcean floor when above water |
| OceanSand | `0x716C53` | ocean_floor | Shallow ocean floor |
| TreeDebris | `0x87673E` | tree_debris | Forest-floor leaf litter under trunks |
| Coal / IronOre / CopperOre / GoldOre | `0x303030` / `0x975752` / `0xB07620` / `0xEAC80C` | ore | Surface ore exposures (rare) |
| Fireweed | `0xFFDBFF` | flower | Flower patches — ignore for biome inference |

These hexes are stable across game versions but can drift slightly when
SLG tweaks block art. Match with a small RGB tolerance
(`max(|dr|,|dg|,|db|) ≤ 6`) rather than exact equality; if no catalog
entry is within tolerance, bucket it as "other" and keep going.

**Caveat**: Grassland and Steppe both surface as plain `Grass`. The
forest biomes show a mix of their soil color *plus* `Grass` where the
canopy gap is wide — the soil pixels are the diagnostic ones. `Desert`
is distinguishable from generic beach sand by the `DesertSand` block;
if you only see `Sand`, it's almost certainly a coast or HighDesert
edge rather than the biome itself.

## Sibling GIFs at `/Layers/`

The web server at `:3001/Layers/` exposes every layer GIF the sim
maintains. Useful neighbors of `WorldPreview.gif`:

- `HeightMap.gif` — **animated**, per-tile max-Y grayscale (0–254).
  Each frame is a historical snapshot; the latest frame is current
  state. Uses a 48-shade grayscale palette. Great for detecting
  mountainous vs flat worlds and crater depressions. Tree canopy is
  invisible here.
- `Terrain.gif` — animated top-block map, same palette as
  `WorldPreview`, changes over time. Not useful for a fresh-world
  narrative (first frame is effectively what `WorldPreview` already
  shows).
- `HeightMapLatest.gif`, `TerrainLatest.gif`, `WorldPreviewLatest.gif`
  — single-frame "collapsed history" variants of the same data.
- Per-layer GIFs named after the underlying `WorldLayer` —
  `Rainfall.gif`, `Temperature.gif`, `Fertility.gif`, `Oil.gif`,
  `Coal.gif`, etc. Each is grayscale (`0` = min, `254` = max for that
  layer's render range). Very useful for "a cold, wet world" or
  "oil-heavy world" flavor.

A future narrative generator can fetch these in addition to
`WorldPreview.gif` (our `preview.py` only pulls the one today).

## What you can infer — cheat sheet

**From config alone, no GIF:**

- World size, build height, map preset.
- Whether craters are enabled at all (`Crater.Frequency == 0` means
  none; Sirens runs with them off).
- Expected biome weights (target %, not realized — the balancer may
  deviate if exclusions crowd things out).
- Upper/lower bounds on continents, islands, rivers, lakes (apply
  `ScaleModifier = (worldSize / 720)^AutoScaleExponent`).
- Terrain character: `TerracePoints` high + `Power` high → blocky,
  plateau-heavy terrain; `MaxElevationOceanDistance` small + steep
  `ElevationPower` → sharp peaks rising close to the coast.

**From the preview GIF + config:**

- Realized biome distribution: cluster pixels by palette color, map
  each cluster back to a block via the hex table above, then aggregate
  blocks → biome using the catalog + the config's enabled biomes.
- Continent count: binary-threshold land vs water (water hex
  `0x2B4696`), label connected components ≥ N pixels. Small blobs =
  islands.
- Water bodies: find blue components fully surrounded by land (lakes)
  vs. thin blue threads (rivers, width ≈ `RiverCellWidth` meters) vs.
  the one giant background body (ocean).
- Coast length: count land pixels adjacent to water pixels.
- Dominant biome: the largest land cluster by pixel count.
- Polar-cap presence: Ice-hex pixels near the top or bottom edge.

**From `HeightMap.gif` latest frame:**

- Mountain ranges: high-grayscale ridges.
- Crater presence: circular dark depressions (skip for Sirens until we
  turn `Crater.Frequency` back on).
- "Flat vs rugged" narrative: stddev of grayscale over land.

**From `Rainfall.gif` / `Temperature.gif`:**

- Global climate summary ("cold and wet", "hot and dry").
- Correlate high-rainfall + low-temp areas with snow/ice regions.

## Recommended Python parsing approach

- **Stack**: `Pillow` handles indexed-palette GIFs cleanly.
  `Image.open(path)` preserves the palette; `img.convert("P")` gives a
  byte array + 768-byte palette via `img.getpalette()`.
- **Fidelity check**: always log `img.size`, `len(img.getpalette()) // 3`,
  `img.n_frames`. If `n_frames != 1` for `WorldPreview.gif`, bail —
  something upstream changed.
- **Color matching**: SLG occasionally tweaks palette entries as new
  blocks register. Don't rely on exact hex equality; use nearest
  neighbor in RGB over the table in the Block-hex section above.
- **Connected components**: `scipy.ndimage.label` or
  `skimage.measure.label`. For a 100×100 image this is trivial; for
  720×720 it's still well under 100 ms.
- **Don't try to reconstruct biome boundaries** — the underlying
  Voronoi polygon graph isn't in the GIF. Stick to block-color + shape
  inference.

## Narrative design notes

- Keep it 1–3 short paragraphs; Discord truncates long walls.
- Lead with the *interesting* facts first: an ice cap, a single
  continent, a giant crater, a world that's 85% desert. Save "also has
  some grassland" for the end.
- Quote the seed once (`roll.py` already prints it in the Discord
  post); narrative copy shouldn't repeat it.
- Prefer observational phrasing ("Three continents ring a central
  ocean; the largest leans temperate, with a ribbon of rainforest
  along its southern coast") over stat dumps ("62% land, 38% ocean").
  Stats can go in a trailing parenthetical.
- Be explicit about uncertainty when the preview alone can't
  distinguish things (e.g. WarmForest vs ColdForest — lean on config
  weights, and `Temperature.gif` if we fetch it).

# Biome contents: plants, animals, minerals

Companion to [`worldgen.md`](worldgen.md). When `inv narrate` identifies a
biome on a generated map, this file is the reference for what that
biome actually *contains* — what species of plants grow there, what
animals spawn, what stone and ore lie under the soil. The narrative
generator draws on this to add player-facing color: what industries a
biome lends itself to (logging vs ranching vs mining), what food
sources are available, and what synergies a pairing of biomes
unlocks.

Scope is vanilla Eco as shipped. The Sirens server layers a handful of
mods on top (see `eco-mods` and `eco-mods-public`) but none of the
currently-installed ones alter biome species rosters — they add
crafting/processing tiers, not flora or fauna. If that changes, note
the additions in a trailing "Sirens additions" section per biome.

Sources (cross-referenced for accuracy):

- The game's own in-code biome definitions — canonical for which
  species spawn where.
- Our server's `eco-configs/Configs/WorldGenerator.eco` — canonical
  for the per-biome `BiomeTerrainModule` block stacks (mineral
  column).
- The Eco wiki at <https://wiki.play.eco/en/> and the in-game
  Ecopedia — canonical for human-readable species names and
  distinguishing traits.

The biome catalog (elevation / temperature / moisture bands, bad-neighbor
exclusions, prevailing rock type) lives in the [biome catalog table](worldgen.md#the-biome-catalog)
in `worldgen.md`. This file skips those and goes straight to what
matters for narrative color.

## How to use this doc

For any biome called out by `inv narrate`, skim the relevant section
and lift 1–3 of the most distinguishing items from each category:

- **Plants** — lean on the canopy tree (oak / redwood / palm) plus
  one or two edibles or ornamentals. Canopy species are the most
  visible signal of biome character to a player.
- **Animals** — the "headline" species is usually a grazer or
  predator that players interact with for food or hunting (bison,
  elk, jaguar, bighorn). Small game and unique fauna (prairie dog,
  agouti, tarantula) are good flavor when space permits.
- **Minerals** — list the rocks first, then the ore(s). A biome's
  ore makeup maps directly to which industries can bootstrap there:
  iron → early smelting, copper → electronics mid-game, coal →
  everything, gold → endgame.

Within each biome section, items are ordered roughly by player
salience (most visible / most useful first).

---

## Temperate and grassland biomes

### Grassland

Open, rolling plains. Moderate temperature (0.4–0.8 normalized) and
drier moisture (0.3–0.5). The biome the Ecopedia uses as its baseline
— most tutorial content assumes a grassland start.

**Plants**
- Trees: Oak (sparse; the only grassland tree)
- Grasses and grains: Big Bluestem, Bunchgrass, Common Grass, Wheat, Rice, Corn
- Wild edibles: Beans, Beets, Camas, Flax
- Flowers: Daisy, Sunflower
- Mushrooms: Boletus, Crimini

**Animals**
- Large grazers: Bison
- Small mammals: Hare, Prairie Dog
- Birds: Turkey
- Predators: Coyote, Fox

**Minerals**
- Surface stone: Limestone, Sandstone, Granite, Gneiss, Dirt, Rocky Soil
- Shallow deposits (1–6m): Clay, Peat, Sulfur
- Mid-depth (12–15m, 25–27m): Coal seams
- Deep (~53m): Iron Ore
- Narrative read: a good all-rounder starting biome — limestone for
  mortar, coal at mining depth, wheat for bread, bison for
  protein. Most civilizations on Sirens have bootstrapped out of a
  grassland.

### Steppe

A high-elevation grassland (0.325–0.4 elevation band). Same
temperature/moisture range as Grassland but perched above it, so
coastlines read as inland plateau when both biomes sit on one
continent.

**Plants** — same roster as Grassland.

**Animals** — same roster as Grassland.

**Minerals** — same block stack as Grassland.

Narrative read: treat it as "grassland with a view." Mostly matters
for visual variety on the preview; gameplay is indistinguishable from
a low-elevation grassland patch.

### Warm Forest

Temperate deciduous and mixed-broadleaf forests. Warm
(0.5–0.8 temp), moderate moisture (0.5–0.6). Granite-rich, which
makes it the standard early-game stone source for forest-start
civilizations.

**Plants**
- Trees: Oak, Cedar, Birch
- Wild edibles: Huckleberries, Beets, Pumpkin
- Flowers: Rose Bush, Trillium, Tulip, Ocean Spray
- Ferns: Fern
- Mushrooms: Amanita, Boletus, Crimini

**Animals**
- Large herbivores: Elk, Deer, Bison
- Predators: Wolf, Fox, Coyote
- Arthropods: Tarantula

**Minerals**
- Surface stone: Granite, Basalt
- Shallow (0–1m): Crushed Granite / Basalt
- Mid-depth (15–30m, 25–55m): Copper Ore
- Pocket (20–24m): Sulfur
- Narrative read: the canonical logging + copper-mining biome. Granite
  cliffs carry the skyline; wolves and elk drive the hunting economy.

### Cold Forest

Coniferous forest — spruce, fir, redwood canopy with occasional old
growth. Cool (0.2–0.5 temp), same moisture as Warm Forest
(0.5–0.6). Genre-defining Pacific-Northwest aesthetic.

**Plants**
- Trees: Fir, Spruce, Redwood (+ Old Growth Redwood), Cedar, Birch
- Wild edibles: Huckleberries, Pumpkin, Salal
- Flowers: Rose Bush, Trillium, Tulip
- Ferns: Fern
- Mushrooms: Amanita, Boletus, Crimini

**Animals**
- Large herbivores: Elk, Deer, Bison
- Predators: Wolf, Fox

**Minerals**
- Surface stone: Granite
- Shallow–mid (1–20m): Copper Ore
- Deep (35–45m): Gold Ore
- Narrative read: the gold-mining biome. Redwoods are the single
  highest-tier wood tier in vanilla Eco, so a cold forest on the
  preview means a logging empire is on the table. Pair with a cold
  forest for both metal tiers (copper shallow + gold deep).

---

## Wet and tropical biomes

### Rainforest

Dense tropical canopy, ceiba and palm as headline trees, very wet
(0.7–1.0 moisture) and warm (0.6–0.8 temp). Repels cold forest per
the world generator's bad-neighbor rules, so expect visible
separation on the preview when both spawn.

**Plants**
- Trees: Ceiba, Palm
- Wild edibles: Papaya, Pineapple, Taro, Heliconia
- Flowers: Orchid, Heliconia
- Ferns: Filmy Fern, King Fern
- Mushrooms: Cookeina, Lattice
- Unique: Pitcher Plant, Peat Moss

**Animals**
- Mammals: Agouti
- Predators: Jaguar

**Minerals**
- Surface stone: Shale, Granite, Clay
- Shallow (up to 20m) and mid (40–55m): Gold Ore
- Pocket (25–30m, 40–45m): Coal
- Narrative read: the gold-heavy biome with the fewest big grazers
  — food comes from tropical fruit (papaya / pineapple / taro) and
  the occasional agouti rather than deer or bison. Jaguars are
  dangerous enough that a rainforest start often pushes players
  toward farming over hunting.

### Wetland

Marshes, fens, peat bogs. Cool to cool-warm (0.4–0.6 temp), very wet
(0.6–0.8). Repels rainforest (bad-neighbor rule), so wetlands usually
appear as small distinct patches rather than as an extension of a
rainforest belt.

**Plants**
- Wild edibles: Beans, Bullrush, Buttonbush, Rice, Cotton, Pumpkin
- Aquatic: Waterweed, Bullrush, Filmy Fern, King Fern
- Flowers: Buttonbush, Rose Bush
- Mushrooms: Peat Moss, Amanita, Boletus, Cookeina, Crimini

**Animals**
- Reptiles: Snapping Turtle
- Mammals: Otter (semi-aquatic)

**Minerals**
- Surface stone: Shale, Clay, Dirt, Gneiss, Peat, Wetlands Soil
- Mid-shallow (~8–11m, 18–21m): Coal
- Deep (45–60m): Granite (scarce)
- Narrative read: the cotton-and-peat biome. Wetlands are the only
  biome that spawns cotton reliably, so a wetland on the preview
  unlocks textiles tech without importing it. Low on large game but
  rich in fish at the edges.

---

## Cold and boreal biomes

### Taiga

Sparse subarctic forest over permafrost-adjacent soil. Very cool
(0.2–0.3 temp), dry to moderate moisture (0.2–0.5). High elevation
(0.3–1.0) — taiga occupies ridges and highlands.

**Plants**
- Trees: Arctic Willow, Spruce
- Wild edibles: Camas, Lupine
- Flowers: Fireweed, Lupine, Saxifrage
- Mushrooms / lichen: Boletus, Deer Lichen

**Animals**
- Large herbivores: Elk, Mountain Goat
- Predators: Wolf, Coyote

**Minerals**
- Surface stone: Granite, Rocky Soil
- Ground layer: Frozen Soil (persistent; slows mining and farming)
- Mid (25–40m, 40–60m): Copper Ore
- Deep (50–60m): Gold Ore
- Narrative read: the mountain-goat biome. Taiga + cold forest
  adjacency is the richest bootstrap for both copper and gold
  without heat-intolerant crops. Frozen soil means you bring your
  own dirt if you want a farm.

### Tundra

No tree canopy — dwarf willows and ground-hugging flora only. Cold
(0.1–0.2 temp), variable moisture (0–0.6). High elevation (0.4–1.0).

**Plants**
- Trees: Arctic Willow, Dwarf Willow (stunted, knee-high)
- Flowers: Fireweed, Saxifrage
- Lichen: Deer Lichen

**Animals**
- Large herbivores: Mountain Goat
- Predators: Wolf

**Minerals**
- Surface stone: Gneiss
- Ground layer: Frozen Soil, Snow (persistent)
- Pocket (30–35m): Basalt
- Deposits (30–100m): Sulfur (long column), Copper Ore (60–100m)
- Shallow: Crushed Gold Ore
- Narrative read: the sulfur-and-gold biome. Tundra pulls up content
  from deeper than any other biome on Sirens, making it the
  late-game extraction zone. Minimal food — settlers starve here
  unless they import calories from a warmer neighbor.

### Ice

Glacial. Temperature 0–0.1, high elevation (0.6–1.0). Wherever ice
caps appear, expect a narrow ring of tundra between them and the
first tree-bearing biome.

**Plants** — essentially none. Specialized lichen and moss survive
at the margins only.

**Animals** — essentially none on the main ice sheet. Any species
present come from the adjacent tundra / cold-forest border.

**Minerals**
- Surface: Ice blocks only
- Shallow (−1 to 15m): Crushed Copper Ore
- Mid (10–60m): Copper Ore
- Narrative read: a biome you travel *across*, not *on*. The only
  reason to settle an ice patch is the copper column underneath.

---

## Arid biomes

### Desert

Hot (0.7–1.0 temp), bone-dry (0.0–0.3 moisture). Low elevation
(0.02–0.2). Bad neighbors with cold forest, warm forest, rainforest,
and wetland — so a desert biome on the preview almost always sits
far from anything lush.

**Plants**
- Trees: Joshua Tree (the only proper desert tree)
- Cacti: Saguaro, Barrel Cactus, Prickly Pear
- Wild edibles: Agave, Creosote Bush, White Bursage
- Moss: Desert Moss

**Animals**
- Large herbivores: Bighorn Sheep
- Reptiles: Tortoise
- Predators: Coyote
- Arthropods: Tarantula

**Minerals**
- Surface stone: Desert Sand, Sand, Sandstone, Gneiss
- Shallow to mid-column (0–50m, many bands): Iron Ore — unusually
  concentrated compared to any other biome
- Pocket (30–35m): Limestone
- Narrative read: *the* iron biome. If a civilization wants rails,
  steel, or heavy machinery early, they need a desert bordering
  their start. Bighorn + tortoise are the food anchor; grain imports
  are mandatory.

### High Desert

Desert at elevation (0.225–0.3). Same contents as low Desert —
treat identically in narrative unless the elevation specifically
matters.

---

## Coastal and marine biomes

### Coast / Warm Coast / Cold Coast

Transition zones where land meets ocean. Any coastline on the preview
is a coast biome; `WarmCoast` vs `ColdCoast` is determined by
temperature and decides whether you see sand (warm) or limestone-
rock (cold) at the waterline.

**Plants**
- Coastal edibles: adjacent-biome species bleed in (huckleberries
  near cold-forest coasts, etc.)
- Marine plants: Kelp, Seagrass (in the shallows beyond the
  waterline)

**Animals**
- Aquatic: Bass, Salmon, Trout, Crab, Clam, Urchin
- Predators at depth: Blue Shark (at the edge of open water)
- Transitional fauna from adjacent land biomes

**Minerals**
- Cold Coast: Gneiss, Sandstone (+ Iron at 34–37m)
- Warm Coast: Limestone (+ Iron at 16–18m)
- Narrative read: coasts mean a working fishing economy from day
  one. Coast depth also dictates whether a player can trade by boat
  between continents — the archipelagos on Sirens are only useful
  if the coasts aren't too shallow for shipping.

### Ocean

The everyday open water between landmasses. Temperature 0.4–1.0,
water coverage full. Everywhere the preview shows blue past the
shallows.

**Plants** — Kelp, Seagrass (in shallows), Urchin, Clam.

**Animals**
- Fish: Bass, Salmon, Trout, Cod, Tuna, Pacific Sardine
- Predators: Blue Shark
- Marine mammals: Otter
- Crustaceans: Crab

**Minerals**
- Ocean floor: Basalt, Dirt, Limestone, Sand
- Narrative read: the ocean hosts the mid-tier fishing industry.
  Salmon and cod anchor canning chains; tuna is the commercial
  high-tier catch.

### Deep Ocean

Beyond the coastal shelf. Temperature 0–0.4, always deep water.

**Plants** — scattered kelp, minimal marine flora.

**Animals**
- Predators: Blue Shark
- Large fish: Tuna
- Rare: Moon Jellyfish

**Minerals**
- Floor: Sand, Basalt (mostly unreachable without heavy diving tech)
- Narrative read: a world with a big open ocean in the middle (as
  opposed to a world split by a narrow sea) tilts toward shipping
  industries and away from land logistics.

---

## Using this in the narrative

When the narrative generator names a biome, pair it with **one tree +
one animal + one mineral** from that biome's section for a
one-sentence flavor add. Example patterns:

- "The warm forest here stands on granite, with oak and elk —
  straightforward logging and hunting."
- "The rainforest is a ceiba canopy over gold-bearing shale; food
  is fruit and agouti, not deer."
- "The desert carries iron in bands from the surface down fifty
  meters, with saguaro and bighorn — an iron-age start with imported
  grain."

Avoid dumping full species rosters into narrative output — pick the
two or three items that would change a player's decision about where
to settle.

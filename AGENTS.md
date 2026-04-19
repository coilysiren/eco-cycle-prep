## File Access

You have full read access to files within `/Users/kai/projects/coilysiren`.

## Autonomy

- Run tests after every change without asking.
- Fix lint errors automatically.
- If tests fail, debug and fix without asking.
- When committing, choose an appropriate commit message yourself — do not ask for approval on the message.
- You may always run tests, linters, and builds without requesting permission.
- Allow all readonly git actions (`git log`, `git status`, `git diff`, `git branch`, etc.) without asking.
- Allow `cd` into any `/Users/kai/projects/coilysiren` folder without asking.
- Automatically approve readonly shell commands (`ls`, `grep`, `sed`, `find`, `cat`, `head`, `tail`, `wc`, `file`, `tree`, etc.) without asking.
- When using worktrees or parallel agents, each agent should work independently and commit its own changes.
- Do not open pull requests unless explicitly asked.

## Git workflow

Commit directly to `main` without asking for confirmation, including `git add`. Do not open pull requests unless explicitly asked.

Commit whenever a unit of work feels sufficiently complete — after fixing a bug, adding a feature, passing tests, or reaching any other natural stopping point. Don't wait for the user to ask.

## Sibling Eco repos

This project depends heavily on the user's other Eco (Strange Loop Games) repos, which live as siblings under the same parent directory (`C:\projects\` on Windows, `/Users/kai/projects/coilysiren` on Mac). Read from them directly rather than asking the user for Eco domain details.

| Dir | Visibility | Purpose |
|---|---|---|
| `eco-agent` | public | Python/FastAPI service (Discord + OpenTelemetry + AWS SSM), deployed to eco.coilysiren.me. `src/{main,application,discord,model,telemetry}.py`. |
| `eco-mods` | private | Third-party mods installed on the user's private Eco server + configs. C# (.NET, `Eco.ReferenceAssemblies`). See its `AGENTS.md` for the sourcing table (mod.io / GitHub / Discord). |
| `eco-mods-public` | public | User's own C# mods (BunWulf family: Agricultural, Biochemical, Educational/Librarian, HardwareCo; plus DirectCarbonCapture, EcoNil, MinesQuarries, ShopBoat, WorldCounter). Code generation via `main.cs` + `tasks.py` + `templates/`. |
| `eco-configs` | private | Server config diffs: `Configs/*.eco` (live), `*.original.json`, `*.diff.json`. Includes `WorldGenerator.eco` — the canonical world-gen JSON shape (Voronoi modules, biomes, rivers, lakes, crater). Most relevant to this project. |
| `eco-mods-assets` | private | Unity project (AssetBundles, Assets, Builds, Packages, ProjectSettings). Produces asset bundles consumed by mods. |
| `eco-mods-assets-embeded` | private | Embedded Unity assets (Icons, Prefabs, Scenes). |
| `eco-GlobalPlanetaryDefense` | public | Standalone mod (Deepflame's GPD) overhauling laser/computer-lab endgame. |

Eco server install paths referenced across these repos:
- Windows: `C:\Program Files (x86)\Steam\steamapps\common\Eco\Eco_Data\Server\`
- Linux: `/home/kai/Steam/steamapps/common/EcoServer/` (also `.local/share/Steam/...`)
- Mac: `/Users/kai/Library/Application Support/Steam/steamapps/common/Eco/Eco.app/Contents/Server/`

Mod sourcing for `eco-mods`: `MODIO_API_KEY` env var; mod.io game ID is 6.

## Eco official docs and API

Reach for these before guessing at Eco types, config shapes, or modding conventions.

- **Wiki** — https://wiki.play.eco/en/ (start pages: `/en/Modding`, `/en/Mod_Development`, `/en/Ecopedia_Modding`).
- **ModKit docs (auto-generated, tracks latest Eco)** — https://docs.play.eco/. Split into:
  - Client API (Unity3D ModKit package)
  - Server API (server-side ModKit DLLs)
  - Remote API (web server, REST-style) — e.g. https://docs.play.eco/api/remote/web/ecogameapi.html
- **EcoModKit reference repo** — https://github.com/StrangeLoopGames/EcoModKit (example mods + the ModKit Unity package).
- **SLG blog on modding** — https://strangeloopgames.com/how-mods-work-in-eco/.
- **mod.io** — game ID `6`. REST API: `GET https://api.mod.io/v1/games/6/mods?api_key=$MODIO_API_KEY&_q=<search>`.

### DiscordLink

Bridges Eco server chat/state with Discord. Used by this project.

- Source: https://github.com/Eco-DiscordLink/EcoDiscordPlugin (org: https://github.com/Eco-DiscordLink)
- Releases: https://github.com/Eco-DiscordLink/EcoDiscordPlugin/releases
- mod.io: https://mod.io/g/eco/m/discordlink

## World generation reference

Two companion reference docs under `docs/`:

- [`docs/worldgen.md`](docs/worldgen.md) — the map-generation
  reference: `WorldGenerator.eco` config schema, the biome catalog
  with colors and block palettes, `WorldPreview.gif` format
  (single-frame 8-bit indexed; pixel size is `WorldWidth × 10`, so
  720×720 at Sirens' current 72-chunk sizing), sibling `/Layers/`
  GIFs, and what's inferable from config-only vs config+GIF.
- [`docs/biomes.md`](docs/biomes.md) — per-biome plants, animals,
  and minerals. Feeds `inv narrate` with the flavor color that lets
  a map description say "oak and elk on granite" instead of just
  "warm forest." Scope is vanilla Eco plus the Sirens mod stack.

Consult both before writing anything that reads world config, parses
the preview image, or attempts to narrate a map in prose.

## Patch notes on server deploys

Whenever a task from this repo lands a change on the live Sirens Eco server, post a patch note to the `#general-public` Discord channel in the Sirens server. Players there play multiple cycles and read patch notes carefully. This repo is the orchestrator, so most cross-repo deploys flow through here.

### When to post

Triggers specific to eco-cycle-prep:

- `inv go-live` / `inv go-private` (Network.eco flip, public/private + password state).
- `inv roll` / `inv post-roll` (new world seed, preview GIF, server restart).
- `inv mods-sync` (copies eco-mods and eco-mods-public onto the Eco install).
- `inv mods-disable --names=...` (removes mods from the server's UserCode).
- `inv ingame --sync` (writes in-game Name / DetailedDescription into Network.eco).
- Any direct ssh edit on kai-server to `/home/kai/Steam/steamapps/common/EcoServer/`.

A plain commit to `main` in this repo is not a deploy trigger by itself (tasks / helpers / wording tweaks that never run against prod don't need a post). Post when the invoked task actually reaches the server. Post in real time, in the same turn as the deploy. Do not describe the post as a backfill, delayed notice, or after-the-fact summary. Write as if the change just landed.

### Audience and tone

Adult gamers on a small private Eco server. Highly engaged. They play multiple cycles and read patch notes carefully.

- Assume they know the game. Use skill names, tier numbers, recipe names, and mechanics directly. Do not re-explain what a "specialty" is.
- Patch-notes voice: mechanical and specific. Numbers over adjectives. "Carpentry now costs 2 stars (tier 2) + 1 per prior specialty" beats "specialty costs are more realistic now."
- No marketing hype ("we're excited to", "enjoy!", "huge update!"). No condescension ("don't worry if this sounds complicated.").
- Describe the before / after when it's a fix. Describe the new capability when it's a feature.
- No em-dashes. Use periods, commas, parens, or " - " for mid-sentence sidebars. Same rule Kai applies elsewhere.
- Under ~1500 characters so it fits in a single Discord message. Sign off with the repo + task or config touched in brackets, e.g. `[eco-cycle-prep / inv roll]`.

### Sending the message

Channel ID is at SSM `/discord/channel/general-public`. For the bot token, **always** use `/sirens-echo/discord-bot-token` (posts as the `sirens-echo` bot). Never use `/eco/discord-bot-token` for manual messages. That one belongs to the `eco-sirens` bot, which is DiscordLink's in-game bridge and already auto-posts things like `Server Started` / `Server Stopped` embeds plus in-game and Discord chat bridging. Mixing the two bots in one channel creates confusion about which posts are automated vs. manual. Pull both values from SSM each time. Do not hardcode.

```sh
# On Windows / Git Bash, prefix each aws call with MSYS_NO_PATHCONV=1. On Mac, drop it.
BOT_TOKEN=$(MSYS_NO_PATHCONV=1 aws ssm get-parameter --name /sirens-echo/discord-bot-token --with-decryption --query Parameter.Value --output text)
CHANNEL=$(MSYS_NO_PATHCONV=1 aws ssm get-parameter --name /discord/channel/general-public --with-decryption --query Parameter.Value --output text)
BODY=$(python -c 'import json,sys; print(json.dumps({"content": sys.stdin.read()}))' <<< 'YOUR MESSAGE BODY HERE')
curl -sS -H "Authorization: Bot $BOT_TOKEN" -H "Content-Type: application/json" -d "$BODY" "https://discord.com/api/v10/channels/$CHANNEL/messages"
```

## Server restart notice (#eco-status)

Before you restart the Eco server on kai-server, post a heads-up embed to `#eco-status`. DiscordLink already auto-posts `Server Stopped :x:` and `Server Started :white_check_mark:` embeds around the restart event itself, but those are retroactive. This one is the forward-looking "restart incoming" signal for players who are in-game or watching the channel.

- Channel ID: SSM `/discord/channel/server-status-feed` (which already points at #eco-status; do not create a new param).
- Bot token: SSM `/sirens-echo/discord-bot-token`.

Match the DiscordLink format exactly: title-only embed, color `7506394`, two spaces between the title text and the emoji shortcode.

```sh
BOT_TOKEN=$(MSYS_NO_PATHCONV=1 aws ssm get-parameter --name /sirens-echo/discord-bot-token --with-decryption --query Parameter.Value --output text)
CHANNEL=$(MSYS_NO_PATHCONV=1 aws ssm get-parameter --name /discord/channel/server-status-feed --with-decryption --query Parameter.Value --output text)
curl -sS -H "Authorization: Bot $BOT_TOKEN" -H "Content-Type: application/json" \
  -d '{"embeds":[{"title":"Server Restarting  :arrows_counterclockwise:","color":7506394}]}' \
  "https://discord.com/api/v10/channels/$CHANNEL/messages"
```

If the restart has a specific reason worth surfacing (e.g. applying a mod fix, new cycle roll), add a one-line `description` field to the embed. Otherwise title-only, matching the spartan existing format. Post immediately before the restart command runs, not after.

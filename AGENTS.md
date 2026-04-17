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

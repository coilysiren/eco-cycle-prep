# Agent instructions

See `../AGENTS.md` for workspace conventions. This file covers what's specific.

---

## Local server config mutations are expected

`server_local.prep_for_local` (via `coily server-run`) intentionally rewrites `Configs/{Network,DiscordLink,Difficulty}.eco` and creates `Configs/Sleep.eco` in the Steam-installed Eco server dir. That's the point - private-local-dev shape. Don't flag these as cleanup candidates. Resync from `eco-configs` only when Kai explicitly asks.

## Sibling Eco repos

Read as siblings rather than asking. `eco-agent` (public, FastAPI Discord/OTel/SSM). `eco-mods` (private, third-party C# mods). `eco-mods-public` (public, BunWulf family + DirectCarbonCapture / EcoNil / MinesQuarries / ShopBoat / WorldCounter). `eco-configs` (private, config diffs + canonical `WorldGenerator.eco`). `eco-mods-assets` (+`-embeded`, private, Unity). `eco-GlobalPlanetaryDefense` (public, Deepflame's GPD).

Eco install paths: Windows `C:\...\Steam\...\Eco_Data\Server\`, Linux `/home/kai/Steam/steamapps/common/EcoServer/`, Mac `~/Library/Application Support/Steam/.../Eco.app/Contents/Server/`. Mod sourcing: `MODIO_API_KEY` env, game ID `6`.

## Eco docs + API

Wiki: https://wiki.play.eco/en/. ModKit docs: https://docs.play.eco/. EcoModKit: https://github.com/StrangeLoopGames/EcoModKit. mod.io API: `GET https://api.mod.io/v1/games/6/mods?api_key=$MODIO_API_KEY&_q=...`. DiscordLink: https://github.com/Eco-DiscordLink/EcoDiscordPlugin.

## World generation reference

Two companion docs under `docs/`:

- `docs/worldgen.md` - `WorldGenerator.eco` schema, biome catalog (colors + blocks), `WorldPreview.gif` format (single-frame 8-bit indexed; `WorldWidth × 10` pixel size = 720×720 at Sirens' 72-chunk).
- `docs/biomes.md` - per-biome plants/animals/minerals. Feeds `coily narrate`.

## Vendor source + dev entry

`../Eco/` is vendor game source, read-only background. Don't paste/quote/link snippets externally; describe behavior in your own words.

`coily` (`../coily`) is the canonical dev entry. Declared in `.coily/coily.yaml`, backed by Make targets, delegating to `eco_cycle_prep/cli.py`. Type `coily <verb>`. `coily --list` shows verbs. Direct `make` / `uv run python -m` only when coily is unavailable.

## Server communications

This repo owns all manual Discord messaging. Siblings point here. Python helpers in `eco_cycle_prep/discord_post.py`, surfaced as coily verbs.

```
coily discord-post --channel=<alias> --from-file=<path>     # plain content
coily discord-post --channel=<alias> --body="<body>"
coily restart-notice [--reason="..."]                       # pre-restart embed -> #eco-status
```

Channel aliases in `discord_post.CHANNEL_ALIASES`: `general-public`, `eco-status`. Both verbs post through the `sirens-echo` bot (SSM `/sirens-echo/discord-bot-token`). The `eco-sirens` bot belongs to DiscordLink for auto Started/Stopped + chat bridge; never used here, so bot author signals automated vs manual.

### When to post

Triggers: `coily go-live` / `go-private`, `coily roll` / `post-roll`, `coily mods-sync`, `coily mods-disable --names=...`, `coily ingame --sync`, any direct ssh edit to `EcoServer/`. A plain commit isn't a trigger. Post when the task actually reaches the server, same turn, not as a backfill.

### Voice, footer, links, ops-trace

- **Voice** - read [`../eco-voice/VOICE.md`](../eco-voice/VOICE.md) first. Mechanical, specific. Numbers over adjectives. Name skills/tiers/recipes. No hype, no exclamation, no em-dashes. Under ~1500 chars. Sign off `[eco-cycle-prep / coily <verb>]`.
- **Restart-schedule footer** - server restarts at 08:00 America/Los_Angeles. Patch notes that need a restart end with the next 08:00 PT via `restart_schedule_footer()` (DST-aware). Hot-reloaded changes don't need it.
- **Public-repo commit links** - when source is in a public repo (only `eco-mods-public` today), include `https://github.com/coilysiren/eco-mods-public/commit/<sha>` (or `.../compare/<a>...<b>`) above the sign-off. Private repos don't get links.
- **Restart-notice embed** - `coily restart-notice [--reason=...]` posts a title-only embed matching DiscordLink's Started/Stopped format (color `7506394`, two-space emoji spacing). Post immediately before the restart, not after.
- **Ops-command trace** - any task mutating real server state posts the literal invoke command to `#eco-status` **before** side-effects. Use `discord_post.ops_notice(command_text)` as the first concrete step. Title-only embed, format the command naturally, redact secrets at the call site. Any new ops verb ships with `ops_notice(...)` + Make target + `.coily/coily.yaml` entry as hard requirements.

## See also

- [README.md](README.md) - human-facing intro.
- [docs/FEATURES.md](docs/FEATURES.md) - inventory of what ships today.
- [.coily/coily.yaml](.coily/coily.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/agentic-os#59](https://github.com/coilysiren/agentic-os/issues/59).

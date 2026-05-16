# Features

Baseline inventory of what `eco-cycle-prep` does today. Yardstick for scope changes. Flat, headline-only. Detail in module docstrings or `README.md`.

Entry points are `coily <verb>`, argparse subcommands in `eco_cycle_prep/cli.py`, wired through Makefile + `.coily/coily.yaml`.

## Cycle prep and intel

- **Weekly prep** - `coily prep --cycle=N`. steamcmd update, pull sibling `eco-configs` + `infrastructure`, Discord digest of recent input.
- **Cycle brief** - `coily brief --cycle=N --days=D`. Long-form brief: full cycle-N channel history + last D days of `#suggestions` + forum.
- **Forum dump** - `coily forum-dump --days=D`. Standalone export of suggestions forum.

## Worldgen rolls

- **Roll a seed** - `coily roll --cycle=N [--seed=S]`. End-to-end: set + push to `eco-configs`, sync + reset storage on kai-server, restart, stream `journalctl` until preview stabilizes, post GIF.
- **Replay a roll** - `coily post-roll --cycle=N [--roll=R]`. Re-posts captured preview without re-rolling. Recovers from failed Discord/SSM hops.
- **Narrate a map** - `coily narrate [--gif=...] [--config=...] [--features]`. Reads `WorldPreview.gif` + `WorldGenerator.eco`, extracts biome/land features, prints prose.

## Mod management on kai-server

- **Sync mods** - `coily mods-sync`. Clones `eco-mods` + `eco-mods-public`, copies into Eco install. Lockdown-gated.
- **Disable mods** - `coily mods-disable --names=A,B,C`. Removes folders from `Mods/UserCode/`, sweeps orphaned AutoGen overrides. Ephemeral.
- **Sweep AutoGen** - `coily mods-sweep`. Idempotent prune of orphaned `Mods/UserCode/AutoGen/*.override.cs`.

## Announcements

- **Cross-server ad** - `coily ad --cycle=N --start-ts=UNIX`. Renders structured markdown ad for main Eco Discord + Reddit. Saves under `rolls/_prep/`.
- **Sirens kickoff** - `coily sirens-post --cycle=N --start-ts=UNIX`. Verbose cycle-kickoff post for `#eco-configs`. 2000-char budget.
- **In-game card** - `coily ingame --cycle=N [--sync]`. Renders master-browser Name (250-char) + DetailedDescription (500-char) with Unity rich-text. `--sync` writes into `eco-configs/Configs/Network.eco`.

## Public / private flips

- **Go live** - `coily go-live`. Launch flip: `eco.copy-configs --with-world-gen`, edits `Network.eco` on disk to public + empty password, optional restart. Git-tracked `Network.eco` stays locked private.
- **Go private** - `coily go-private`. Inverse: syncs locked `Network.eco` onto server, re-asserts private + locked password, restarts.

## Direct Discord posting

- **Plain post** - `coily discord-post --channel=<alias> (--body=... | --from-file=...)`. Posts via `sirens-echo` to `general-public` / `eco-status`.
- **Restart heads-up** - `coily restart-notice [--reason=...]`. Pre-restart embed to `#eco-status`, mirrors DiscordLink format.
- **Ops trace** - `coily ops-notice --command=...`. Posts literal ops command to `#eco-status` before side effects. First step of every ops task.

## Local-dev Eco server (Windows / Mac)

- **Prep + launch** - `coily server-run [--offline]`. Rewrites `Network.eco`, `DiscordLink.eco`, `Difficulty.eco`, creates `Sleep.eco`, launches server.
- **Launch as-is** - `coily server-launch [--offline]`.
- **Copy configs** - `coily server-copy-configs`. Pulls `Configs/` from sibling `eco-configs`.
- **Copy mods** - `coily server-copy-public-mods` + `coily server-copy-private-mods`. Pull `Mods/` from siblings.
- **Deploy mod DLL** - `coily server-deploy-mod --dll=PATH [--name=NAME]`. Drops pre-built DLL into `Server/Mods/<name>/`.
- **Regen new seed** - `coily server-regen-new [--seed=N]`. Wipes `Storage` + `Logs`, fresh world.
- **Regen same seed** - `coily server-regen-same`. Wipes `Storage` + `Logs`, keeps current seed.

## Cross-cutting infrastructure

- **SSM-backed config** - Discord channel IDs, bot tokens, mod.io API key, Eco server ID resolve from AWS SSM at runtime.
- **Two-bot discipline** - `sirens-echo` for manual messaging, `eco-sirens` for DiscordLink auto-embeds + chat bridge. Bot author = automated vs hand-authored.
- **Restart-schedule footer** - `restart_schedule_footer()` renders next 08:00 PT restart in Discord timestamp syntax.
- **Lockdown gate** - `safety.assert_network_locked_down()` blocks ops when git's `Network.eco` is not locked.
- **Worldgen refs** - `docs/worldgen.md` + `docs/biomes.md`. Schema, biome catalog, GIF format, per-biome flora/fauna.
- **Templates** - `string.Template` markdown stubs under `eco_cycle_prep/templates/` for ad + kickoff. Per-cycle bullets under `rolls/_prep/` (gitignored).

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - agent-facing operating rules.
- [.coily/coily.yaml](../.coily/coily.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/agentic-os#59](https://github.com/coilysiren/agentic-os/issues/59).

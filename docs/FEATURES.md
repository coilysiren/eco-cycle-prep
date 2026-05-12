# Features

Baseline inventory of what `eco-cycle-prep` does today. Use this as the
yardstick for scope changes. If a future PR adds a feature not in this
list, that's a scope increase. If it removes one, scope decrease. Keep
the list flat and headline-only. Detail belongs in module docstrings or
`README.md`.

All operator entry points are `coily <verb>`. Implementations live as
pyinvoke tasks in `tasks.py` and modules under `eco_cycle_prep/`.

## Cycle prep and intel

- **Weekly prep** - `coily prep --cycle=N`. Runs steamcmd update, pulls
  sibling `eco-configs` and `infrastructure` repos, generates a Discord
  digest of recent community input.
- **Cycle brief** - `coily brief --cycle=N --days=D`. Cycle-13-style
  long-form brief. Full cycle-N channel history plus last D days of
  `#suggestions` and the suggestions forum.
- **Forum dump** - `coily forum-dump --days=D`. Standalone export of
  the suggestions forum.

## Worldgen rolls

- **Roll a seed** - `coily roll --cycle=N [--seed=S]`. End-to-end:
  set + push to `eco-configs`, sync configs and reset storage on
  kai-server, restart, stream `journalctl -u eco-server` until the
  preview stabilizes, post the preview GIF to the cycle channel. One
  seed per invocation.
- **Replay a roll post** - `coily post-roll --cycle=N [--roll=R]`.
  Re-posts a previously captured preview without re-rolling the world.
  Recovers from failed Discord or SSM hops.
- **Narrate a map** - `coily narrate [--gif=...] [--config=...]
  [--features]`. Reads `WorldPreview.gif` plus `WorldGenerator.eco`,
  extracts biome and land-shape features, prints prose suitable for
  Discord. Standalone, not yet wired into `roll`.

## Mod management on kai-server

- **Sync mods** - `coily mods-sync`. Clones `eco-mods` and
  `eco-mods-public` on kai-server and copies them into the Eco install.
  Lockdown-gated: `Network.eco` in git must carry the private,
  password-protected values.
- **Disable mods** - `coily mods-disable --names=A,B,C`. Removes mod
  folders from `Mods/UserCode/` on the server and sweeps orphaned
  AutoGen overrides. Ephemeral. Permanent removals belong in the
  `eco-mods` source repo.
- **Sweep AutoGen overrides** - `coily mods-sweep`. Idempotent prune of
  orphaned `Mods/UserCode/AutoGen/*.override.cs` whose source mod is
  gone. Replaces the static workaround that lived in
  `infrastructure/scripts/install-eco-mod.sh`.

## Announcements

- **Cross-server ad** - `coily ad --cycle=N --start-ts=UNIX`. Renders
  the structured markdown ad for the main Eco Discord and Reddit.
  Prints to stdout and saves a copy under `rolls/_prep/`.
- **Sirens kickoff post** - `coily sirens-post --cycle=N
  --start-ts=UNIX`. Verbose cycle-kickoff post for Sirens'
  `#eco-configs`. Budgeted to Discord's 2000-char cap.
- **In-game server card** - `coily ingame --cycle=N [--sync]`. Renders
  the master-server-browser Name (250-char cap) and DetailedDescription
  (500-char cap) with Unity rich-text color tags. `--sync` writes the
  rendered values into `eco-configs/Configs/Network.eco`.

## Public / private flips

- **Go live** - `coily go-live`. Cycle launch flip on kai-server. Runs
  `eco.copy-configs --with-world-gen`, edits `Network.eco` on disk to
  set `PublicServer=true` and `Password=""`, optionally restarts. The
  git-tracked `Network.eco` stays locked private at all times.
- **Go private** - `coily go-private`. Inverse mid-cycle flip. Syncs
  git's locked `Network.eco` onto the server, re-asserts
  `PublicServer=false` plus the locked password, restarts.

## Direct Discord posting

- **Plain content post** - `coily discord-post --channel=<alias>
  (--body=... | --from-file=...)`. Posts via the `sirens-echo` bot to a
  named channel alias (`general-public`, `eco-status`). Used for patch
  notes and other manual announcements.
- **Restart heads-up** - `coily restart-notice [--reason=...]`.
  Pre-restart embed to `#eco-status`. Mirrors DiscordLink's Server
  Started / Server Stopped embed format.
- **Ops command trace** - `coily ops-notice --command=...`. Posts the
  literal text of an ops command to `#eco-status` before side effects
  hit the server. Audit-trail backbone. Called as the first step of
  every ops task in this repo, also exposed for manual use.

## Local-dev Eco server (Windows / Mac)

Migrated from `coilysiren/infrastructure/src/eco.py` so this repo is
the single source of truth for Eco ops.

- **Prep and launch** - `coily server-run [--offline]`. Rewrites local
  `Configs/Network.eco`, `DiscordLink.eco`, `Difficulty.eco`, and
  creates `Sleep.eco` to put the local box into private-dev shape, then
  launches the EcoServer.
- **Launch as-is** - `coily server-launch [--offline]`.
- **Copy configs from sibling** - `coily server-copy-configs`. Pulls
  `Configs/` from the sibling `eco-configs` repo.
- **Copy mods from siblings** - `coily server-copy-public-mods` and
  `coily server-copy-private-mods`. Pull `Mods/` from
  `eco-mods-public` and `eco-mods` respectively.
- **Deploy a single mod DLL** - `coily server-deploy-mod --dll=PATH
  [--name=NAME]`. Drops a pre-built mod DLL into
  `Server/Mods/<name>/`.
- **Regen world (new seed)** - `coily server-regen-new [--seed=N]`.
  Wipes `Storage` and `Logs`, forces a fresh world at the given seed.
- **Regen world (same seed)** - `coily server-regen-same`. Wipes
  `Storage` and `Logs`, keeps the current `WorldGenerator.eco` seed.

## Cross-cutting infrastructure

- **AWS SSM-backed config** - All Discord channel IDs, bot tokens, the
  mod.io API key, and the Eco server ID resolve from AWS SSM at
  runtime. No secrets in repo.
- **Two-bot discipline** - `sirens-echo` for manual messaging,
  `eco-sirens` reserved for DiscordLink's auto Server Started /
  Stopped embeds and the in-game chat bridge. Bot author identifies
  whether a message was automated or hand-authored.
- **Restart-schedule footer** - `restart_schedule_footer()` helper
  renders the next 08:00 PT restart in Discord native timestamp syntax.
  Used in patch notes whose changes need a restart to take effect.
- **Lockdown safety gate** - `safety.assert_network_locked_down()`
  blocks ops that assume private state when git's `Network.eco` is
  not in the locked private form.
- **Worldgen reference docs** - `docs/worldgen.md` and
  `docs/biomes.md`. `WorldGenerator.eco` schema, biome catalog and
  block palettes, `WorldPreview.gif` format, per-biome flora/fauna for
  narration. Consulted by `narrate` and by anyone touching world
  config.
- **Templates** - `string.Template` markdown stubs under
  `eco_cycle_prep/templates/` for the cross-server ad and the Sirens
  kickoff post. Per-cycle bullets live under `rolls/_prep/`
  (gitignored).

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - agent-facing operating rules.
- [.coily/coily.yaml](../.coily/coily.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/coilyco-ai#313](https://github.com/coilysiren/coilyco-ai/issues/313).

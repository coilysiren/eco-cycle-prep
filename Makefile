DEFAULT_GOAL := help

help:
	@awk '/^## / \
		{ if (c) {print c}; c=substr($$0, 4); next } \
			c && /(^[[:alpha:]][[:alnum:]_-]+:)/ \
		{printf "%-30s %s\n", $$1, c; c=0} \
			END { print c }' $(MAKEFILE_LIST)

# Each verb delegates to `python -m eco_cycle_prep.cli <verb>`. coily.yaml
# wraps these as `coily <verb>`. Pass arguments as variables, e.g.
# `make prep cycle=13` or `coily prep --cycle=13`.

## install runtime + dev deps
sync:
	uv sync

# --- cycle prep ---

## weekly cycle prep digest
#  vars: cycle (required)
prep:
	uv run python -m eco_cycle_prep.cli prep --cycle=$(cycle)

## standalone dump of the suggestions forum
#  vars: days (default 60)
forum-dump:
	uv run python -m eco_cycle_prep.cli forum-dump --days=$(or $(days),60)

## full cycle channel pull plus suggestions/forum lookback
#  vars: cycle (required), days (default 60)
brief:
	uv run python -m eco_cycle_prep.cli brief --cycle=$(cycle) --days=$(or $(days),60)

# --- map rolls ---

## roll one worldgen seed end-to-end and post the preview
#  vars: cycle (required), seed (optional)
roll:
	uv run python -m eco_cycle_prep.cli roll --cycle=$(cycle) $(if $(seed),--seed=$(seed))

## replay the Discord post for an already-captured roll preview
#  vars: cycle (required), roll (optional)
post-roll:
	uv run python -m eco_cycle_prep.cli post-roll --cycle=$(cycle) $(if $(roll),--roll=$(roll))

## describe a generated map in prose
#  vars: gif (optional), config (optional), features (set to 1 to enable)
narrate:
	uv run python -m eco_cycle_prep.cli narrate \
		$(if $(gif),--gif=$(gif)) \
		$(if $(config),--config=$(config)) \
		$(if $(features),--features)

# --- mod management ---

## clone eco-mods + eco-mods-public on kai-server and copy to the Eco install
#  vars: check (set to 1 for lockdown-only check)
mods-sync:
	uv run python -m eco_cycle_prep.cli mods-sync $(if $(check),--check)

## remove mod folders from the live server (ephemeral)
#  vars: names (required, comma-separated)
mods-disable:
	uv run python -m eco_cycle_prep.cli mods-disable --names=$(names)

## prune orphaned AutoGen overrides on the live server
mods-sweep:
	uv run python -m eco_cycle_prep.cli mods-sweep

# --- announcements ---

## emit the cross-server ad markdown
#  vars: cycle (required), start_ts (required, unix)
ad:
	uv run python -m eco_cycle_prep.cli ad --cycle=$(cycle) --start-ts=$(start_ts)

## emit the Sirens #eco-configs cycle-kickoff post
#  vars: cycle (required), start_ts (required, unix)
sirens-post:
	uv run python -m eco_cycle_prep.cli sirens-post --cycle=$(cycle) --start-ts=$(start_ts)

## render in-game Name + DetailedDescription
#  vars: cycle (required), sync (set to 1 to write back)
ingame:
	uv run python -m eco_cycle_prep.cli ingame --cycle=$(cycle) $(if $(sync),--sync)

# --- discord plumbing ---

## post a one-off content message via the sirens-echo bot
#  vars: channel (required), body OR from_file (one of)
discord-post:
	uv run python -m eco_cycle_prep.cli discord-post --channel=$(channel) \
		$(if $(body),--body="$(body)") \
		$(if $(from_file),--from-file=$(from_file))

## pre-restart heads-up embed to #eco-status
#  vars: reason (optional)
restart-notice:
	uv run python -m eco_cycle_prep.cli restart-notice $(if $(reason),--reason="$(reason)")

## post the literal text of an ops command to #eco-status
#  vars: command (required)
ops-notice:
	uv run python -m eco_cycle_prep.cli ops-notice --command="$(command)"

# --- go-live / go-private ---

## flip the running server to public + no-password on kai-server
#  vars: restart (default true)
go-live:
	uv run python -m eco_cycle_prep.cli go-live --restart=$(or $(restart),true)

## inverse of go-live - re-privatize the running server
#  vars: restart (default true)
go-private:
	uv run python -m eco_cycle_prep.cli go-private --restart=$(or $(restart),true)

# --- local Eco server (Windows / Mac) ---

## rewrite Configs for private-local dev then launch the local EcoServer
#  vars: offline (set to 1 to skip SSM)
server-run:
	uv run python -m eco_cycle_prep.cli server-run $(if $(offline),--offline)

## launch the local EcoServer as-is with no config rewrite
#  vars: offline (set to 1 to skip SSM)
server-launch:
	uv run python -m eco_cycle_prep.cli server-launch $(if $(offline),--offline)

## copy Configs/ from sibling eco-configs into the local Eco server
server-copy-configs:
	uv run python -m eco_cycle_prep.cli server-copy-configs

## copy Mods/ from sibling eco-mods-public into the local Eco server
server-copy-public-mods:
	uv run python -m eco_cycle_prep.cli server-copy-public-mods

## copy Mods/ from sibling eco-mods into the local Eco server
server-copy-private-mods:
	uv run python -m eco_cycle_prep.cli server-copy-private-mods

## drop a pre-built mod DLL into the local Server/Mods/<name>/
#  vars: dll (required), name (optional, defaults to DLL stem)
server-deploy-mod:
	uv run python -m eco_cycle_prep.cli server-deploy-mod --dll=$(dll) $(if $(name),--name=$(name))

## wipe Storage + Logs and force a fresh random world on the local server
#  vars: seed (default 0)
server-regen-new:
	uv run python -m eco_cycle_prep.cli server-regen-new --seed=$(or $(seed),0)

## wipe Storage + Logs but keep the current WorldGenerator.eco seed
server-regen-same:
	uv run python -m eco_cycle_prep.cli server-regen-same

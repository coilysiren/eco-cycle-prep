DEFAULT_GOAL := help

help: ## Print this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "%-30s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Each verb delegates to `python -m eco_cycle_prep.cli <verb>`. coily.yaml
# wraps these as `coily <verb>`. Pass arguments as variables, e.g.
# `make prep cycle=13` or `coily prep --cycle=13`.

sync: ## Install runtime + dev deps via uv.
	uv sync

# --- cycle prep ---

prep: ## Weekly cycle prep - steamcmd update, sibling git pulls, Discord digest. Args - cycle=N.
	uv run python -m eco_cycle_prep.cli prep --cycle=$(cycle)

forum-dump: ## Standalone dump of the suggestions forum. Args - days=D.
	uv run python -m eco_cycle_prep.cli forum-dump --days=$(or $(days),60)

brief: ## Full cycle channel pull plus suggestions/forum lookback. Args - cycle=N days=D.
	uv run python -m eco_cycle_prep.cli brief --cycle=$(cycle) --days=$(or $(days),60)

# --- map rolls ---

roll: ## Roll one worldgen seed end-to-end and post the preview. Args - cycle=N seed=S.
	uv run python -m eco_cycle_prep.cli roll --cycle=$(cycle) $(if $(seed),--seed=$(seed))

post-roll: ## Replay the Discord post for an already-captured roll preview. Args - cycle=N roll=R.
	uv run python -m eco_cycle_prep.cli post-roll --cycle=$(cycle) $(if $(roll),--roll=$(roll))

narrate: ## Describe a generated map in prose. Args - gif=PATH config=PATH features=1.
	uv run python -m eco_cycle_prep.cli narrate \
		$(if $(gif),--gif=$(gif)) \
		$(if $(config),--config=$(config)) \
		$(if $(features),--features)

# --- mod management ---

mods-sync: ## Clone eco-mods + eco-mods-public on kai-server and copy to the Eco install. Lockdown-gated. Args - check=1.
	uv run python -m eco_cycle_prep.cli mods-sync $(if $(check),--check)

mods-disable: ## Remove mod folders from the live server (ephemeral). Args - names=A,B,C.
	uv run python -m eco_cycle_prep.cli mods-disable --names=$(names)

mods-sweep: ## Prune orphaned AutoGen overrides on the live server whose source mod is gone. Idempotent.
	uv run python -m eco_cycle_prep.cli mods-sweep

# --- announcements ---

ad: ## Emit the cross-server ad markdown. Args - cycle=N start_ts=UNIX.
	uv run python -m eco_cycle_prep.cli ad --cycle=$(cycle) --start-ts=$(start_ts)

sirens-post: ## Emit the Sirens #eco-configs channel kickoff post. Args - cycle=N start_ts=UNIX.
	uv run python -m eco_cycle_prep.cli sirens-post --cycle=$(cycle) --start-ts=$(start_ts)

ingame: ## Render in-game Name + DetailedDescription. Args - cycle=N sync=1.
	uv run python -m eco_cycle_prep.cli ingame --cycle=$(cycle) $(if $(sync),--sync)

# --- discord plumbing ---

discord-post: ## Post a one-off content message via the sirens-echo bot. Args - channel=ALIAS body=STR or from_file=PATH.
	uv run python -m eco_cycle_prep.cli discord-post --channel=$(channel) \
		$(if $(body),--body="$(body)") \
		$(if $(from_file),--from-file=$(from_file))

restart-notice: ## Pre-restart heads-up embed to #eco-status. Args - reason=STR.
	uv run python -m eco_cycle_prep.cli restart-notice $(if $(reason),--reason="$(reason)")

ops-notice: ## Post the literal text of an ops command to #eco-status before running. Args - command=STR.
	uv run python -m eco_cycle_prep.cli ops-notice --command="$(command)"

# --- go-live / go-private ---

go-live: ## Flip the running server to public + no-password on kai-server. Args - restart=true|false.
	uv run python -m eco_cycle_prep.cli go-live --restart=$(or $(restart),true)

go-private: ## Inverse of go-live - re-privatize the running server. Args - restart=true|false.
	uv run python -m eco_cycle_prep.cli go-private --restart=$(or $(restart),true)

# --- local Eco server (Windows / Mac) ---

server-run: ## Rewrite Configs for private-local dev then launch the local EcoServer. Args - offline=1.
	uv run python -m eco_cycle_prep.cli server-run $(if $(offline),--offline)

server-launch: ## Launch the local EcoServer as-is with no config rewrite. Args - offline=1.
	uv run python -m eco_cycle_prep.cli server-launch $(if $(offline),--offline)

server-copy-configs: ## Copy Configs/ from sibling eco-configs into the local Eco server.
	uv run python -m eco_cycle_prep.cli server-copy-configs

server-copy-public-mods: ## Copy Mods/ from sibling eco-mods-public into the local Eco server.
	uv run python -m eco_cycle_prep.cli server-copy-public-mods

server-copy-private-mods: ## Copy Mods/ from sibling eco-mods into the local Eco server.
	uv run python -m eco_cycle_prep.cli server-copy-private-mods

server-deploy-mod: ## Drop a pre-built mod DLL into the local Server/Mods/<name>/. Args - dll=PATH name=STR.
	uv run python -m eco_cycle_prep.cli server-deploy-mod --dll=$(dll) $(if $(name),--name=$(name))

server-regen-new: ## Wipe Storage + Logs and force a fresh random world on the local server. Args - seed=N.
	uv run python -m eco_cycle_prep.cli server-regen-new --seed=$(or $(seed),0)

server-regen-same: ## Wipe Storage + Logs but keep the current WorldGenerator.eco seed.
	uv run python -m eco_cycle_prep.cli server-regen-same

"""argparse CLI for eco-cycle-prep dev verbs.

Replaces tasks.py. The Makefile + .coily/coily.yaml route every verb
through `python -m eco_cycle_prep.cli <verb> ...`. Operators (human or
agent) type `coily <verb>`, not `python -m`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 on stdout/stderr so unicode in Discord content and Eco logs
# doesn't blow up on Windows (default cp1252).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _add_prep(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("prep", help="Weekly cycle prep digest.")
    p.add_argument("--cycle", type=int, required=True)
    p.set_defaults(func=lambda a: _prep(a))


def _prep(a: argparse.Namespace) -> None:
    from eco_cycle_prep import prep as prep_module

    prep_module.run(None, cycle=a.cycle)


def _add_forum_dump(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("forum-dump", help="Dump suggestions-forum history.")
    p.add_argument("--days", type=int, default=60)
    p.set_defaults(func=lambda a: _forum_dump(a))


def _forum_dump(a: argparse.Namespace) -> None:
    from eco_cycle_prep import prep as prep_module

    prep_module.run_forum_dump(None, since_days=a.days)


def _add_brief(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("brief", help="Cycle channel pull plus suggestions/forum lookback.")
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--days", type=int, default=60)
    p.set_defaults(func=lambda a: _brief(a))


def _brief(a: argparse.Namespace) -> None:
    from eco_cycle_prep import prep as prep_module

    prep_module.run_brief(None, cycle=a.cycle, days=a.days)


def _add_mods_sync(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("mods-sync", help="Clone eco-mods on kai-server and sync to Eco install.")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=lambda a: _mods_sync(a))


def _mods_sync(a: argparse.Namespace) -> None:
    from eco_cycle_prep import mods, safety

    safety.assert_network_locked_down()
    if a.check:
        print("lockdown ok - would call eco.copy-private-mods + eco.copy-public-mods")
        return
    mods.sync(None)


def _add_ad(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("ad", help="Emit cross-server ad markdown for the cycle.")
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--start-ts", type=int, required=True)
    p.set_defaults(func=lambda a: _ad(a))


def _ad(a: argparse.Namespace) -> None:
    from eco_cycle_prep import announce

    announce.run(cycle=a.cycle, start_ts=a.start_ts)


def _add_sirens_post(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("sirens-post", help="Emit the Sirens #eco-configs cycle-kickoff post.")
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--start-ts", type=int, required=True)
    p.set_defaults(func=lambda a: _sirens_post(a))


def _sirens_post(a: argparse.Namespace) -> None:
    from eco_cycle_prep import announce

    announce.run_sirens_configs(cycle=a.cycle, start_ts=a.start_ts)


def _add_ingame(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("ingame", help="Render in-game Name + DetailedDescription strings.")
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--sync", action="store_true")
    p.set_defaults(func=lambda a: _ingame(a))


def _ingame(a: argparse.Namespace) -> None:
    from eco_cycle_prep import announce

    announce.run_ingame(cycle=a.cycle)
    if a.sync:
        announce.sync_ingame_to_network(cycle=a.cycle)


def _add_mods_disable(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("mods-disable", help="Remove mod folders from the live server.")
    p.add_argument("--names", required=True)
    p.set_defaults(func=lambda a: _mods_disable(a))


def _mods_disable(a: argparse.Namespace) -> None:
    from eco_cycle_prep import discord_post as dp
    from eco_cycle_prep import mods

    arr = [n.strip() for n in a.names.split(",") if n.strip()]
    if not arr:
        raise ValueError("--names is required; pass e.g. --names=DFBargeIndustries")
    dp.ops_notice(f"coily mods-disable --names={','.join(arr)}")
    mods.disable_on_server(None, arr)


def _add_mods_sweep(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("mods-sweep", help="Prune orphaned AutoGen overrides on the live server.")
    p.set_defaults(func=lambda a: _mods_sweep(a))


def _mods_sweep(a: argparse.Namespace) -> None:
    from eco_cycle_prep import discord_post as dp
    from eco_cycle_prep import mods

    dp.ops_notice("coily mods-sweep")
    mods.sweep_autogen_on_server(None)


def _add_roll(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("roll", help="Roll one worldgen seed end-to-end and post preview.")
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=lambda a: _roll(a))


def _roll(a: argparse.Namespace) -> None:
    from eco_cycle_prep import roll as roll_module

    roll_module.run(None, cycle=a.cycle, seed=a.seed)


def _add_post_roll(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("post-roll", help="Replay the Discord post for an existing roll preview.")
    p.add_argument("--cycle", type=int, required=True)
    p.add_argument("--roll", type=int, default=None)
    p.set_defaults(func=lambda a: _post_roll(a))


def _post_roll(a: argparse.Namespace) -> None:
    from eco_cycle_prep import roll as roll_module

    roll_module.post_existing(cycle=a.cycle, roll=a.roll)


def _add_narrate(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("narrate", help="Describe a generated map in prose.")
    p.add_argument("--gif", default=None)
    p.add_argument("--config", default=None)
    p.add_argument("--features", action="store_true")
    p.set_defaults(func=lambda a: _narrate(a))


def _narrate(a: argparse.Namespace) -> None:
    from eco_cycle_prep import narrative as narrative_module

    narrative_module.run(
        gif_path=Path(a.gif) if a.gif else None,
        config_path=Path(a.config) if a.config else None,
        show_features=bool(a.features),
    )


def _add_discord_post(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("discord-post", help="Post a one-off content message via sirens-echo bot.")
    p.add_argument("--channel", required=True)
    p.add_argument("--body", default=None)
    p.add_argument("--from-file", default=None, dest="from_file")
    p.set_defaults(func=lambda a: _discord_post(a))


def _discord_post(a: argparse.Namespace) -> None:
    from eco_cycle_prep import discord_post as dp

    if bool(a.body) == bool(a.from_file):
        raise ValueError("pass exactly one of --body=... or --from-file=...")
    content = a.body if a.body else open(a.from_file, encoding="utf-8").read()
    r = dp.post_content(a.channel, content)
    print(f"posted id={r['id']} channel_id={r['channel_id']} len={len(r.get('content', ''))}")


def _add_restart_notice(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("restart-notice", help="Pre-restart heads-up embed to #eco-status.")
    p.add_argument("--reason", default=None)
    p.set_defaults(func=lambda a: _restart_notice(a))


def _restart_notice(a: argparse.Namespace) -> None:
    from eco_cycle_prep import discord_post as dp

    r = dp.restart_notice(reason=a.reason)
    print(f"posted id={r['id']} channel_id={r['channel_id']}")


def _add_ops_notice(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("ops-notice", help="Post the literal text of an ops command to #eco-status.")
    p.add_argument("--command", required=True)
    p.set_defaults(func=lambda a: _ops_notice(a))


def _ops_notice(a: argparse.Namespace) -> None:
    from eco_cycle_prep import discord_post as dp

    r = dp.ops_notice(a.command)
    print(f"posted id={r['id']} channel_id={r['channel_id']}")


def _add_go_live(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("go-live", help="Flip the Eco server to public + no-password.")
    p.add_argument("--restart", default="true")
    p.set_defaults(func=lambda a: _go_live(a))


def _go_live(a: argparse.Namespace) -> None:
    from eco_cycle_prep import golive

    golive.run(None, restart=_truthy(a.restart))


def _add_go_private(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("go-private", help="Re-privatize the running Eco server.")
    p.add_argument("--restart", default="true")
    p.set_defaults(func=lambda a: _go_private(a))


def _go_private(a: argparse.Namespace) -> None:
    from eco_cycle_prep import goprivate

    goprivate.run(None, restart=_truthy(a.restart))


def _truthy(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _add_server_run(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-run", help="Rewrite Configs for private-local dev and launch.")
    p.add_argument("--offline", action="store_true")
    p.set_defaults(func=lambda a: _server_run(a))


def _server_run(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.prep_for_local(offline=a.offline)
    server_local.launch(offline=a.offline)


def _add_server_launch(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-launch", help="Launch the local EcoServer as-is.")
    p.add_argument("--offline", action="store_true")
    p.set_defaults(func=lambda a: _server_launch(a))


def _server_launch(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.launch(offline=a.offline)


def _add_server_copy_configs(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-copy-configs", help="Copy Configs/ from sibling eco-configs.")
    p.set_defaults(func=lambda a: _server_copy_configs(a))


def _server_copy_configs(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.copy_configs_from_sibling()


def _add_server_copy_public_mods(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "server-copy-public-mods", help="Copy Mods/ from sibling eco-mods-public."
    )
    p.set_defaults(func=lambda a: _server_copy_public_mods(a))


def _server_copy_public_mods(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.copy_mods_from_sibling(server_local.PUBLIC_MODS_SIBLING)


def _add_server_copy_private_mods(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-copy-private-mods", help="Copy Mods/ from sibling eco-mods.")
    p.set_defaults(func=lambda a: _server_copy_private_mods(a))


def _server_copy_private_mods(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.copy_mods_from_sibling(server_local.PRIVATE_MODS_SIBLING)


def _add_server_deploy_mod(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-deploy-mod", help="Drop a pre-built mod DLL into Server/Mods/.")
    p.add_argument("--dll", required=True)
    p.add_argument("--name", default=None)
    p.set_defaults(func=lambda a: _server_deploy_mod(a))


def _server_deploy_mod(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.deploy_mod_dll(Path(a.dll), mod_name=a.name)


def _add_server_regen_new(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-regen-new", help="Wipe Storage + Logs and force a fresh world.")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=lambda a: _server_regen_new(a))


def _server_regen_new(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.regen_new_world(seed=a.seed)


def _add_server_regen_same(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("server-regen-same", help="Wipe Storage + Logs but keep the seed.")
    p.set_defaults(func=lambda a: _server_regen_same(a))


def _server_regen_same(a: argparse.Namespace) -> None:
    from eco_cycle_prep import server_local

    server_local.regen_same_world()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eco-cycle-prep")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for adder in [
        _add_prep,
        _add_forum_dump,
        _add_brief,
        _add_mods_sync,
        _add_ad,
        _add_sirens_post,
        _add_ingame,
        _add_mods_disable,
        _add_mods_sweep,
        _add_roll,
        _add_post_roll,
        _add_narrate,
        _add_discord_post,
        _add_restart_notice,
        _add_ops_notice,
        _add_go_live,
        _add_go_private,
        _add_server_run,
        _add_server_launch,
        _add_server_copy_configs,
        _add_server_copy_public_mods,
        _add_server_copy_private_mods,
        _add_server_deploy_mod,
        _add_server_regen_new,
        _add_server_regen_same,
    ]:
        adder(sub)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

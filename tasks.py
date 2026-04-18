"""Entry points for the Eco map evaluation workflow.

Phase 1 (weekly):   inv prep --cycle 13
Phase 2 (repeated): inv roll --cycle 13 [--count N] [--seed N]
"""

from invoke import task


@task(help={"cycle": "Current Eco cycle number (e.g. 13)"})
def prep(ctx, cycle):
    from eco_map_generator import prep as prep_module

    prep_module.run(ctx, cycle=int(cycle))


@task(
    help={
        "cycle": "Current Eco cycle number",
        "count": "How many rolls to generate (default 1)",
        "seed": "Specific seed to use. If set, overrides random and forces count=1.",
    }
)
def roll(ctx, cycle, count=1, seed=None):
    from eco_map_generator import roll as roll_module

    roll_module.run(
        ctx,
        cycle=int(cycle),
        count=int(count),
        seed=int(seed) if seed is not None else None,
    )

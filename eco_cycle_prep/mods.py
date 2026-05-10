"""Mod workflow helpers for cycle prep:

- sync: clone eco-mods + eco-mods-public on kai-server and copy into
  the Eco install (via existing `inv eco.copy-*-mods` tasks in
  infrastructure/src/eco.py).
- check: query mod.io for each third-party mod listed in eco-mods/README.md
  and report latest version vs. what's installed.
- disable: list of mod folder names to remove from the install post-sync
  (used for cycle-by-cycle disables like Deepflame 2026-04 request).
- sweep_autogen: prune orphaned `*.override.cs` files under the server's
  `Mods/UserCode/AutoGen/` whose source no longer exists in eco-mods or
  eco-mods-public. Replaces the per-deploy workaround that lived in
  infrastructure/scripts/install-eco-mod.sh (eco-cycle-prep#5).
"""

import json
import re
from pathlib import Path

from typing import Any as Context

from . import remote, safety

def _find_sibling(name: str) -> Path:
    """Locate a sibling repo clone. The Windows host has them flat under
    `~/projects/<name>`; Mac nests them under `~/projects/coilysiren/<name>`.
    Try both, return whichever exists. Falls back to the flat path so callers
    that probe `.exists()` get a deterministic answer."""
    flat = Path.home() / "projects" / name
    nested = Path.home() / "projects" / "coilysiren" / name
    if nested.is_dir():
        return nested
    return flat


ECO_MODS = _find_sibling("eco-mods")
ECO_MODS_PUBLIC = _find_sibling("eco-mods-public")
MODS_README = ECO_MODS / "README.md"

# Both source repos co-own this tree on the server. Expected contents are
# the union of `Mods/UserCode/AutoGen/` from both clones.
AUTOGEN_REL = Path("Mods/UserCode/AutoGen")

MODIO_RE = re.compile(r"mod\.io/g/eco/m/([\w\-]+)")


def list_modio_slugs() -> list[tuple[str, str]]:
    """Return (display_name, mod.io slug) pairs parsed from eco-mods/README.md."""
    out: list[tuple[str, str]] = []
    for line in MODS_README.read_text(encoding="utf-8").splitlines():
        m = MODIO_RE.search(line)
        if not m:
            continue
        # Bullet lines look like: `- [DisplayName](mod.io/g/eco/m/slug)`
        name_match = re.search(r"\[([^\]]+)\]", line)
        display = name_match.group(1) if name_match else m.group(1)
        out.append((display, m.group(1)))
    return out


def sync(ctx: Context) -> None:
    """Re-clone eco-mods + eco-mods-public on kai-server and copy them into
    the Eco install. Guarded by Network.eco lockdown (we will not sync mods
    into a public server)."""
    safety.assert_network_locked_down()
    print("-- syncing private mods (eco-mods) on kai-server")
    remote.ssh(ctx, f"cd {remote.INFRA_DIR} && {remote.REMOTE_INV} eco.copy-private-mods")
    print("-- syncing public mods (eco-mods-public) on kai-server")
    remote.ssh(ctx, f"cd {remote.INFRA_DIR} && {remote.REMOTE_INV} eco.copy-public-mods")
    sweep_autogen_on_server(ctx)


def disable_on_server(ctx: Context, names: list[str]) -> None:
    """Delete the given mod folder names from the server's UserCode dir,
    then sweep orphaned AutoGen overrides whose source mod is no longer
    present. Idempotent; missing names are a no-op. Guarded by lockdown."""
    safety.assert_network_locked_down()
    if not names:
        return
    paths = [
        f"{remote.ECO_SERVER_DIR}/Mods/UserCode/{n}" for n in names
    ]
    print(f"-- disabling {len(names)} mods on kai-server: {', '.join(names)}")
    remote.ssh(ctx, "rm -rfv " + " ".join(paths))
    sweep_autogen_on_server(ctx)


def _expected_autogen_files() -> set[str]:
    """Union of file paths under `Mods/UserCode/AutoGen/` across the local
    eco-mods and eco-mods-public clones, as POSIX strings relative to the
    AutoGen root. The local clones are the source of truth; kai-server
    reclones from these same git repos during `mods.sync`."""
    expected: set[str] = set()
    for repo in (ECO_MODS, ECO_MODS_PUBLIC):
        root = repo / AUTOGEN_REL
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.is_file():
                expected.add(p.relative_to(root).as_posix())
    return expected


_SWEEP_SCRIPT_TEMPLATE = '''
import json, os

ROOT = {root!r}
EXPECTED = set(json.loads({expected_json!r}))

removed_files = []
if os.path.isdir(ROOT):
    for dirpath, _, filenames in os.walk(ROOT):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            if rel not in EXPECTED:
                os.remove(full)
                removed_files.append(rel)

    # Walk bottom-up; rmdir empties only. Leave ROOT in place.
    for dirpath, _, _ in os.walk(ROOT, topdown=False):
        if dirpath == ROOT:
            continue
        try:
            os.rmdir(dirpath)
        except OSError:
            pass

if removed_files:
    print(f"removed {{len(removed_files)}} orphan(s):")
    for r in sorted(removed_files):
        print(f"  {{r}}")
else:
    print("no AutoGen orphans found")
'''


def sweep_autogen_on_server(ctx: Context) -> None:
    """Remove `Mods/UserCode/AutoGen/` files on kai-server whose source no
    longer exists in eco-mods or eco-mods-public. Idempotent. Guarded by
    lockdown.

    Replaces the static ORPHANED_PATHS sweep that lived in
    infrastructure/scripts/install-eco-mod.sh. The expected file set is
    computed from the local clones (kai-server reclones the same repos
    during `mods.sync`, so the local view matches what got copied).
    """
    safety.assert_network_locked_down()
    # Refuse to sweep if neither source clone is on disk. Computing an empty
    # expected set against a populated server tree would delete everything
    # under AutoGen, which is exactly the foot-gun this task is meant to
    # avoid. Both repos must be locally present to authorize the sweep.
    missing = [str(p) for p in (ECO_MODS, ECO_MODS_PUBLIC) if not p.is_dir()]
    if missing:
        raise FileNotFoundError(
            "mods.sweep_autogen_on_server: source clones missing "
            f"({', '.join(missing)}). Refusing to sweep with an empty "
            "expected set. Clone the repos and retry."
        )
    expected = _expected_autogen_files()
    script = _SWEEP_SCRIPT_TEMPLATE.format(
        root=f"{remote.ECO_SERVER_DIR}/{AUTOGEN_REL.as_posix()}",
        expected_json=json.dumps(sorted(expected)),
    )
    print(
        f"-- sweeping AutoGen orphans on kai-server "
        f"(expected={len(expected)} files from local eco-mods + eco-mods-public)"
    )
    remote.run_python(ctx, script)


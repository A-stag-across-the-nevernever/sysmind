"""Test bootstrap. Imported first by every test file.

Does two things, both of which the suite previously got wrong:

1. Puts the project root on sys.path *relative to this file*, rather than a
   hardcoded absolute path that only resolved on the original author's machine.

2. Redirects every config and data path at a throwaway directory. Without this,
   `save_config()` writes to ~/.config/sysmind/config.json, so simply running
   the tests destroys real settings — approvals, block list, level, model.
   That is not hypothetical: it happened during development of this file.

Import it before importing anything from the project:

    import _bootstrap  # noqa: F401
"""
import pathlib
import sys
import tempfile

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import sysmind_common as _sc  # noqa: E402  (must follow the sys.path insert)

TMP = pathlib.Path(tempfile.mkdtemp(prefix="sysmind-tests-"))

_sc.CONFIG_DIR = TMP / "config"
_sc.DATA_DIR = TMP / "data"
_sc.BACKUP_DIR = _sc.DATA_DIR / "backups"
_sc.CONFIG_FILE = _sc.CONFIG_DIR / "config.json"
_sc.ATLAS_FILE = _sc.DATA_DIR / "atlas.json"


def real_config_untouched() -> bool:
    """True if the live user config is not what these tests write to."""
    real = pathlib.Path.home() / ".config" / "sysmind" / "config.json"
    return _sc.CONFIG_FILE != real

import enum
import importlib
import logging
import os
import site
import sys
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class Checkpoint(enum.IntEnum):
    BLANK = 0
    PACKAGES = 1
    MAIN = 2
    TESTLIB = 3


SITE_PACKAGES = site.getsitepackages() + [
    site.getuserbase(),
    site.getusersitepackages(),
    "/usr/lib/python",
]

CACHEDIR = Path(".pytest_cache/forkserver")
CACHEDIR.mkdir(parents=True, exist_ok=True)


def write_modules_to_checkpoints() -> None:
    d = defaultdict(list)
    for module in sys.modules:
        cp = get_checkpoint(module)
        d[cp].append(module)

    for cp in d:
        get_file(cp).write_text("\n".join(d[cp]))


def load_modules_in_checkpoint(cp: Checkpoint) -> None:
    logger.info(f"loading modules at {cp}")

    if not get_file(cp).exists():
        return
    modules = get_file(cp).read_text().splitlines()
    to_remove = set()
    try:
        for module in modules:
            importlib.import_module(module)
    except ModuleNotFoundError:
        to_remove.add(module)

    if to_remove:
        logger.info(f"removing modules: {to_remove}")
        modules = [m for m in modules if m not in to_remove]
        get_file(cp).write_text("\n".join(modules))


def get_file(cp: Checkpoint) -> Path:
    return CACHEDIR.joinpath(f"{cp}.txt")


def get_checkpoint(module: str) -> Checkpoint:
    if _is_package(module):
        return Checkpoint.PACKAGES
    elif _is_test_package(module):
        return Checkpoint.TESTLIB
    else:
        return Checkpoint.MAIN


checkpoints = [
    get_file(c).read_text().splitlines() if get_file(c).exists() else []
    for c in Checkpoint
]


def _is_package(module: str) -> bool:
    module = importlib.import_module(module)

    # builtins dont have file?
    f = getattr(module, "__file__", None)
    if not f:
        return True

    f: str = os.path.abspath(module.__file__)
    return any(f.startswith(sp) for sp in SITE_PACKAGES)


def _is_test_package(module: str) -> bool:
    return True if "test" in module else False

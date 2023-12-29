import enum
import functools
import importlib
import importlib.util
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
]

CACHEDIR = Path(".forkserver_cache")
CACHEDIR.mkdir(parents=True, exist_ok=True)


def write_modules_to_checkpoints() -> None:
    d = defaultdict(list)
    # imported_modules.txt gets written as the 'command' executes.
    f = CACHEDIR / "imported_modules.txt"
    if not f.exists():
        return

    for module in f.read_text().splitlines():
        cp = get_checkpoint(module)
        d[cp].append(module)

    for cp in d:
        get_file(cp).write_text("\n".join(d[cp]))

    f.unlink(missing_ok=True)


def load_modules_in_checkpoint(cp: Checkpoint) -> None:
    logger.debug(f"loading modules at {cp}")

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
        logger.debug(f"removing modules: {to_remove}")
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
    prefix = module.split(".", 1)[0]
    return _is_package_by_prefix(prefix)


@functools.cache
def _is_package_by_prefix(prefix: str) -> bool:
    if prefix in sys.stdlib_module_names:
        return True
    spec = importlib.util.find_spec(prefix)
    if spec is None:
        return True
    if spec.origin is None:
        return True
    origin = os.path.abspath(spec.origin)
    return any(origin.startswith(sp) for sp in SITE_PACKAGES)


def _is_test_package(module: str) -> bool:
    return True if _is_main(module) and "test" in module else False


def _is_main(module: str) -> bool:
    return not _is_package(module)

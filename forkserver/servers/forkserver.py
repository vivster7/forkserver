import logging
import sys
from multiprocessing.connection import Connection
from typing import Optional

import pytest

from forkserver.lib.checkpoint import (
    Checkpoint,
    checkpoints,
    load_modules_in_checkpoint,
    write_modules_to_checkpoints,
)
from forkserver.lib.context import ctx
from forkserver.lib.events import FilesModifiedEvent, ShutdownEvent
from forkserver.lib.filename_to_module import filename_to_module

logger = logging.getLogger(__name__)


def forkserver(receiver: Connection, level: int) -> None:
    sender = None
    logger.info(f"starting checkpoint server: {level}")
    while True:
        logger.info(f"{level} waiting...")
        event = receiver.recv()
        logger.info(f"{level} received: {type(event).__name__}")

        t = event.get_type()
        if t == "shutdown":
            _shutdown(sender, level)
        elif t == "files_modified" and level == len(Checkpoint):
            _run_test()
        elif t == "files_modified" and _should_forward(sender, event, level):
            _forward(sender, event)
        elif t == "files_modified":
            sender = _respawn(sender, event, level)
        else:
            raise ValueError(f"unknown event: {t}")


def _run_test() -> None:
    def execute_test() -> None:
        # os.execvp(sys.argv[0], sys.argv)
        exit_code = pytest.main(
            ["-s", "-v", "-Wignore::pytest.PytestAssertRewriteWarning", "tests/slow.py"]
        )
        write_modules_to_checkpoints()
        return exit_code

    ctx.Process(target=execute_test, daemon=True).start()


def _shutdown(sender: Optional[Connection], level: int) -> None:
    logger.info(f"shutting down checkpoint server: {level}")
    if sender:
        sender.send((ShutdownEvent()))
        sender.close()
    sys.exit(0)


def _forward(sender: Connection, event: FilesModifiedEvent) -> None:
    logger.info(f"forwarding {type(event).__name__}")
    sender.send(event)


def _should_forward(
    sender: Optional[Connection], event: FilesModifiedEvent, level: int
) -> bool:
    modules = [filename_to_module(f) for f in event.files]
    return (
        sender is not None
        and level + 1 < len(checkpoints)
        and all(m not in checkpoints[level + 1] for m in modules)
    )


def _respawn(
    old_sender: Optional[Connection], event: FilesModifiedEvent, level: int
) -> Connection:
    if old_sender:
        logger.info(f"shutting down next level {level} -> {level+ 1}")
        old_sender.send((ShutdownEvent()))
        old_sender.close()

    load_modules_in_checkpoint(level)

    logger.info(f"starting next {level} -> {level + 1}")
    receiver, sender = ctx.Pipe(duplex=False)
    child = ctx.Process(target=forkserver, args=(receiver, level + 1))
    child.start()
    sender.send(event)
    return sender

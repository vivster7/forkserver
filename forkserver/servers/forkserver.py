import logging
import shlex
import sys
from multiprocessing.connection import Connection
from typing import Optional, Union

from forkserver.lib.checkpoint import (
    Checkpoint,
    checkpoints,
    load_modules_in_checkpoint,
    write_modules_to_checkpoints,
)
from forkserver.lib.context import ctx
from forkserver.lib.events import CommandEvent, FilesModifiedEvent, ShutdownEvent
from forkserver.lib.filename_to_module import filename_to_module

logger = logging.getLogger(__name__)


def forkserver(receiver: Connection, level: int) -> None:
    sender = None
    logger.info(f"starting checkpoint server: {level}")
    while True:
        logger.info(f"{level} waiting...")
        event = receiver.recv()
        logger.info(f"{level} received: {type(event).__name__}")

        t = event.type
        if t == "shutdown":
            _forward_shutdown(sender, level)
            _exit(level)
        elif level == len(Checkpoint):
            _run_command(event)
        elif _should_forward(sender, event, level):
            _forward(sender, event)
        else:
            sender = _respawn(sender, event, level)
        # else:
        #     raise ValueError(f"unknown event: {t}")


def _run_command(event: Union[CommandEvent, FilesModifiedEvent]) -> None:
    def execute_test() -> None:
        import os
        import runpy
        import sys

        if getattr(event, "command", None) is not None:
            # Possiblilites:
            # 1. app.py
            # 2. app
            # 3. -m app
            # 3. -- app.py
            command = shlex.split(event.command)
            if not command:
                return
            if command[0] == "--":
                command = command[1:]
            if os.path.exists(command[0]):
                canon = os.path.normcase(os.path.abspath(command[0]))
                sys.argv[:] = [canon] + command[1:]
                runpy.run_path(canon, run_name="__main__")
            else:
                if command[0] == "-m":
                    command = command[1:]
                sys.argv[:] = command
                runpy._run_module_as_main(command[0], alter_argv=False)
            write_modules_to_checkpoints()

    ctx.Process(target=execute_test, daemon=True).start()


def _forward_shutdown(sender: Optional[Connection], level: int) -> None:
    if sender:
        logger.info(f"forwarding shutdown {level} -> {level+ 1}")
        sender.send((ShutdownEvent()))
        sender.close()


def _exit(level: int) -> None:
    logger.info(f"shutting down checkpoint server: {level}")
    sys.exit(0)


def _forward(sender: Connection, event: FilesModifiedEvent) -> None:
    logger.info(f"forwarding {type(event).__name__}")
    sender.send(event)


def _should_forward(
    sender: Optional[Connection], event: FilesModifiedEvent, level: int
) -> bool:
    if sender is None:
        return False
    if event.type == "command":
        return True
    elif event.type == "files_modified":
        modules = [filename_to_module(f) for f in event.files]
        return level + 1 < len(checkpoints) and all(
            m not in checkpoints[level + 1] for m in modules
        )


def _respawn(
    old_sender: Optional[Connection], event: FilesModifiedEvent, level: int
) -> Connection:
    _forward_shutdown(old_sender, level)

    load_modules_in_checkpoint(level)

    logger.info(f"starting next {level} -> {level + 1}")
    receiver, sender = ctx.Pipe(duplex=False)
    child = ctx.Process(target=forkserver, args=(receiver, level + 1))
    child.start()
    sender.send(event)
    return sender

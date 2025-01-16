import logging
import sys
from multiprocessing.connection import Connection
from typing import Optional, Union

from forkserver.lib.checkpoint import (
    Checkpoint,
    checkpoints,
    load_modules_in_checkpoint,
)
from forkserver.lib.context import ctx
from forkserver.lib.events import CommandEvent, FilesModifiedEvent, ShutdownEvent
from forkserver.lib.filename_to_module import filename_to_module

logger = logging.getLogger(__name__)


def forkserver(receiver: Connection, level: int) -> None:
    logger.info(f"starting forkserver: {level}")
    sender = None
    while True:
        logger.debug(f"{level} waiting...")
        event = receiver.recv()
        logger.debug(f"{level} received: {type(event).__name__}")

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
        import pathlib
        import runpy
        import sys

        # TODO: This probably needs to be optimized.
        class CustomFinder:
            def __init__(self):
                self.f = pathlib.Path(".forkserver_cache/imported_modules.txt")
                self.f.parent.mkdir(parents=True, exist_ok=True)

            def find_spec(self, fullname, path, target=None):
                # Importing flask.__main__ causes the import process to be swapped out?
                if fullname.endswith("__main__"):
                    return None
                with self.f.open("a") as f:
                    f.write(f"{fullname}\n")
                # Return None to continue with the normal import process
                return None

        custom_finder = CustomFinder()
        sys.meta_path.insert(0, custom_finder)

        if getattr(event, "command", None) is not None:
            # Possiblilites:
            # 1. pytest tests/fast.py
            # 2. python -m pytest tests/fast.py
            # 3. python tests/fast.py
            # 4. (unsupported) python -0 tests/fast.py
            command = event.command
            if not command:
                return

            logger.debug(f"running command: {command}")

            if command[:2] == ["python", "-m"]:
                sys.argv[:] = command[2:]
                runpy._run_module_as_main(command[2], alter_argv=False)
            elif command[0] != "python":
                sys.argv[:] = command
                runpy._run_module_as_main(command[0], alter_argv=False)
            elif command[0] == "python":
                # TODO: Handle other args to python like -0.
                canon = os.path.normcase(os.path.abspath(command[1]))
                sys.argv[:] = [canon] + command[2:]
                runpy.run_path(canon, run_name="__main__")

    ctx.Process(target=execute_test, daemon=True).start()


def _forward_shutdown(sender: Optional[Connection], level: int) -> None:
    if sender:
        logger.debug(f"forwarding shutdown {level} -> {level + 1}")
        sender.send((ShutdownEvent()))
        sender.close()


def _exit(level: int) -> None:
    logger.debug(f"shutting down checkpoint server: {level}")
    sys.exit(0)


def _forward(sender: Connection, event: FilesModifiedEvent) -> None:
    logger.debug(f"forwarding {type(event).__name__}")
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

    logger.debug(f"starting next {level} -> {level + 1}")
    receiver, sender = ctx.Pipe(duplex=False)
    child = ctx.Process(target=forkserver, args=(receiver, level + 1))
    child.start()
    sender.send(event)
    return sender

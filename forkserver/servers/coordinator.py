import logging
import multiprocessing
import os
import signal
import sys
import time
from typing import Optional

from forkserver.lib.checkpoint import write_modules_to_checkpoints
from forkserver.lib.context import ctx
from forkserver.lib.events import CommandEvent
from forkserver.servers.forkserver import forkserver
from forkserver.servers.http import http
from forkserver.servers.watcher import watcher

logger = logging.getLogger(__name__)


def coordinator(command: list[str], timeout: Optional[int] = None) -> None:
    # Set a process group id so that we can kill all processes in the group on exit.
    pgid = os.getpid()
    os.setpgid(os.getpid(), pgid)

    queue = ctx.SimpleQueue()

    fs = ctx.Process(target=forwarder, args=(queue,))
    hs = ctx.Process(target=http, args=(queue,))
    ws = ctx.Process(target=watcher, args=(queue,))

    ws.start()
    fs.start()
    hs.start()

    if len(sys.argv) > 1:
        queue.put(CommandEvent(command))

    elapsed = 0

    try:
        while True:
            time.sleep(1)
            elapsed += 1
            if timeout and elapsed >= timeout:
                raise KeyboardInterrupt("Timeout expired")
    except KeyboardInterrupt:
        # Catch the first ctrl+c and try and kill the entire process group
        os.killpg(pgid, signal.SIGTERM)
    finally:
        # Everythings probably dead, but just in case...
        ws.stop()
        fs.stop()
        hs.stop()
        ws.join()
        fs.join()
        hs.join()


def forwarder(queue: multiprocessing.SimpleQueue) -> None:
    """Fowards events from queue to forkserver."""
    receiver, sender = ctx.Pipe(duplex=False)
    cs = ctx.Process(target=forkserver, args=(receiver, 0))
    cs.start()
    last_command: list[str] = []
    while True:
        event = queue.get()
        write_modules_to_checkpoints()
        # Attach 'last_command' to files_modified events.
        if event.type == "command":
            last_command = event.command
        elif event.type == "files_modified":
            if last_command:
                event.command = last_command
        logger.debug(f"got event: {type(event).__name__}")
        sender.send(event)

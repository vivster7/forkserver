import logging
import multiprocessing
import os
import signal
import time

from forkserver.lib.context import ctx
from forkserver.servers.forkserver import forkserver
from forkserver.servers.watcher import watcher

logger = logging.getLogger(__name__)


def coordinator() -> None:
    # Set a process group id so that we can kill all processes in the group on exit.
    pgid = os.getpid()
    os.setpgid(os.getpid(), pgid)

    queue = ctx.SimpleQueue()

    wd = ctx.Process(target=watcher, args=(queue,))
    ff = ctx.Process(target=forwarder, args=(queue,))

    wd.start()
    ff.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Catch the first ctrl+c and try and kill the entire process group
        os.killpg(pgid, signal.SIGTERM)
    finally:
        # Everythings probably dead, but just in case...
        wd.stop()
        ff.stop()
        wd.join()
        ff.join()


def forwarder(queue: multiprocessing.SimpleQueue) -> None:
    """Fowards events from watcher to forkserver."""
    receiver, sender = ctx.Pipe(duplex=False)
    cs = ctx.Process(target=forkserver, args=(receiver, 0))
    cs.start()
    while True:
        event = queue.get()
        logger.info(f"got event: {type(event).__name__}")
        sender.send(event)

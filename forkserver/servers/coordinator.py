import logging
import os
import signal

from forkserver.lib.context import ctx
from forkserver.servers.forkserver import forkserver
from forkserver.servers.watcher import watchdog_server

logger = logging.getLogger(__name__)


def coordinator():
    # Set a process group id so that we can kill all processes in the group on exit.
    pgid = os.getpid()
    os.setpgid(os.getpid(), pgid)

    queue = ctx.SimpleQueue()
    receiver, sender = ctx.Pipe(duplex=False)

    wd = ctx.Process(target=watchdog_server, args=(queue,))
    cs = ctx.Process(target=forkserver, args=(receiver, 0))

    wd.start()
    cs.start()

    try:
        while True:
            event = queue.get()
            logger.info(f"got event: {type(event).__name__}")
            sender.send(event)
    except KeyboardInterrupt:
        # Catch the first ctrl+c and try and kill the entire process group
        os.killpg(pgid, signal.SIGTERM)
    finally:
        # Everythings probably dead, but just in case...
        wd.stop()
        cs.stop()
        wd.join()
        cs.join()

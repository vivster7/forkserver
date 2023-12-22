import logging

from forkserver.servers.coordinator import coordinator

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s [%(name)s]:: %(message)s",
    datefmt="%H:%M:%S",
)


coordinator()

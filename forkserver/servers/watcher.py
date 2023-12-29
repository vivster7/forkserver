import logging
from functools import partial
from multiprocessing import SimpleQueue

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.utils.event_debouncer import EventDebouncer

from forkserver.lib.events import FilesModifiedEvent

logger = logging.getLogger(__name__)


class NotifyEventHandler(PatternMatchingEventHandler):
    def __init__(self, event_debouncer: EventDebouncer):
        self.event_debouncer = event_debouncer
        super().__init__(patterns=["*.py"], ignore_directories=True)

    def on_modified(self, event: FileSystemEvent) -> None:
        self.event_debouncer.handle_event(event)


def on_events_callback(
    events: list[FileSystemEvent],
    *,
    queue: SimpleQueue,
) -> None:
    event = FilesModifiedEvent({event.src_path for event in events}, command=[])
    logger.debug(f"put event: {event}")
    queue.put(event)


def watcher(queue: SimpleQueue) -> None:
    path = "."
    event_debouncer = EventDebouncer(
        debounce_interval_seconds=0.3,
        events_callback=partial(on_events_callback, queue=queue),
    )

    event_handler = NotifyEventHandler(event_debouncer)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)

    observer.start()
    event_debouncer.start()

    observer.join()
    event_debouncer.join()

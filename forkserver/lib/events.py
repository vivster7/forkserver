from dataclasses import dataclass
from typing import ClassVar


@dataclass
class ShutdownEvent:
    type: ClassVar[str] = "shutdown"


@dataclass
class FilesModifiedEvent:
    type: ClassVar[str] = "files_modified"
    files: list[str]


@dataclass
class CommandEvent:
    type: ClassVar[str] = "command"
    command: str

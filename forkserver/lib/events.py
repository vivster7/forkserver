from dataclasses import dataclass


@dataclass
class ShutdownEvent:
    @classmethod
    def get_type(cls):
        return "shutdown"


@dataclass
class FilesModifiedEvent:
    @classmethod
    def get_type(cls):
        return "files_modified"

    files: list[str]


@dataclass
class CommandEvent:
    command: str

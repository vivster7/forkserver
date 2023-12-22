import os


def filename_to_module(filename: str) -> str:
    filename = os.path.splitext(filename)[0]  # Remove the .py extension
    module = filename.replace(os.sep, ".")  # Replace directory separators with dots
    return module.lstrip(".")

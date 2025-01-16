from pathlib import Path


def filename_to_module(filename: Path) -> str:
    # Convert to Path if string is passed
    filename = Path(filename).resolve()

    # Remove .py extension
    filename = filename.with_suffix("")

    # Start from the file's parent directory and work up
    path = filename.parent
    module_root = filename

    while path != path.parent:  # Stop at root
        if not (path / "__init__.py").exists():
            # Found the top of the package
            # Get the relative part of the path from here
            module_root = filename.relative_to(path) if path != Path("/") else filename
            break
        path = path.parent

    # Convert path parts to module notation
    module = str(module_root).replace(str(Path("/")), ".")
    return module

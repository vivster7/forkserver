"""Compoose Python modules.

Code mostly taken from pdb.py.

Usage:
  python -m forkserver.compose -m forkserver.compose -m http.server
"""

#! /usr/bin/env python3

# NOTE: the actual command documentation is collected from docstrings of the
# commands and is appended to __doc__ after the class has been defined.


# Main program for testing


def _runmodule(module_name):
    import builtins
    import os
    import runpy

    import __main__

    def canonic(filename):
        """Return canonical form of filename.

        For real filenames, the canonical form is a case-normalized (on
        case insensitive filesystems) absolute path.  'Filenames' with
        angle brackets, such as "<stdin>", generated in interactive
        mode, are returned unchanged.
        """
        if filename == "<" + filename[1:-1] + ">":
            return filename

        canonic = os.path.abspath(filename)
        canonic = os.path.normcase(canonic)
        return canonic

    def run(cmd, globals=None, locals=None):
        """Debug a statement executed via the exec() function.

        globals defaults to __main__.dict; locals defaults to globals.
        """
        if globals is None:
            import __main__

            globals = __main__.__dict__
        if locals is None:
            locals = globals
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")

        exec(cmd, globals, locals)

    mod_name, mod_spec, code = runpy._get_module_details(module_name)
    mainpyfile = canonic(code.co_filename)

    __main__.__dict__.clear()
    __main__.__dict__.update(
        {
            "__name__": "__main__",
            "__file__": mainpyfile,
            "__package__": mod_spec.parent,
            "__loader__": mod_spec.loader,
            "__spec__": mod_spec,
            "__builtins__": builtins,
        }
    )
    run(code)


def _runscript(filename):
    import builtins
    import io
    import os

    import __main__

    def canonic(filename):
        """Return canonical form of filename.

        For real filenames, the canonical form is a case-normalized (on
        case insensitive filesystems) absolute path.  'Filenames' with
        angle brackets, such as "<stdin>", generated in interactive
        mode, are returned unchanged.
        """
        if filename == "<" + filename[1:-1] + ">":
            return filename

        canonic = os.path.abspath(filename)
        canonic = os.path.normcase(canonic)
        return canonic

    def run(cmd, globals=None, locals=None):
        """Debug a statement executed via the exec() function.

        globals defaults to __main__.dict; locals defaults to globals.
        """
        if globals is None:
            import __main__

            globals = __main__.__dict__
        if locals is None:
            locals = globals
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")

        exec(cmd, globals, locals)

    # The script has to run in __main__ namespace (or imports from
    # __main__ will break).
    #
    # So we clear up the __main__ and set several special variables
    # (this gets rid of pdb's globals and cleans old variables on restarts).

    __main__.__dict__.clear()
    __main__.__dict__.update(
        {
            "__name__": "__main__",
            "__file__": filename,
            "__builtins__": builtins,
        }
    )

    # When bdb sets tracing, a number of call and line events happens
    # BEFORE debugger even reaches user's code (and the exact sequence of
    # events depends on python version). So we take special measures to
    # avoid stopping before we reach the main script (see user_line and
    # user_call for details).
    mainpyfile = canonic(filename)
    with io.open_code(filename) as fp:
        statement = "exec(compile(%r, %r, 'exec'))" % (fp.read(), mainpyfile)
    run(statement)


_usage = """\
usage: pdb.py [-c command] ... [-m module | pyfile] [arg] ...

Debug the Python program given by pyfile. Alternatively,
an executable module or package to debug can be specified using
the -m switch.

Initial commands are read from .pdbrc files in your home directory
and in the current directory, if they exist.  Commands supplied with
-c are executed after commands from .pdbrc files.

To let the script run until an exception occurs, use "-c continue".
To let the script run up to a given line X in the debugged file, use
"-c 'until X'"."""


def main():
    import getopt
    import os
    import sys

    opts, args = getopt.getopt(sys.argv[1:], "mh:", ["help"])

    if not args:
        print(_usage)
        sys.exit(2)

    commands = []
    run_as_module = False
    for opt, optarg in opts:
        if opt in ["-h", "--help"]:
            print(_usage)
            sys.exit()
        elif opt in ["-c", "--command"]:
            commands.append(optarg)
        elif opt in ["-m"]:
            run_as_module = True

    mainpyfile = args[0]  # Get script filename
    if not run_as_module and not os.path.exists(mainpyfile):
        print("Error:", mainpyfile, "does not exist")
        sys.exit(1)

    sys.argv[:] = args  # Hide "pdb.py" and pdb options from argument list

    if not run_as_module:
        mainpyfile = os.path.realpath(mainpyfile)
        # Replace pdb's dir with script's dir in front of module search path.
        sys.path[0] = os.path.dirname(mainpyfile)

    if run_as_module:
        _runmodule(mainpyfile)
    else:
        _runscript(mainpyfile)


# When invoked as main program, invoke the debugger on a script
if __name__ == "__main__":
    print("Composing..")
    main()

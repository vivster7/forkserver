import argparse
import logging

from forkserver.servers.coordinator import coordinator

_usage = """\
python -m forkserver [--timeout <seconds>] -- <command> [<args>]

Examples:
  python -m forkserver -- pytest tests/fast.py
  python -m forkserver -- flask run
"""


# Create the parser and add arguments
parser = argparse.ArgumentParser(prog="forkserver", usage=_usage)
parser.add_argument(
    "--timeout",
    type=int,
    help="Timeout until forkserver exits.",
)
parser.add_argument(
    "--loglevel",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Set the logging level",
)
parser.add_argument(
    "command", nargs=argparse.REMAINDER, help="Command to eexecute after --"
)

# Parse the arguments
args = parser.parse_args()

if not args.command:
    parser.print_help()
    exit(1)

numeric_level = logging.INFO
if args.loglevel:
    numeric_level = getattr(logging, args.loglevel.upper(), None)

logging.basicConfig(
    level=numeric_level,
    format="[%(levelname)s] %(asctime)s [%(name)s]:: %(message)s",
    datefmt="%H:%M:%S",
)

coordinator(args.command[1:], args.timeout)

import sys


def pytest_addoption(parser):
    parser.addoption(
        "--forkserver", action="store_true", help="Enable the forkserver"
    )


def pytest_configure(config):
    if config.getoption("--forkserver"):
        args = sys.argv[:]
        args.remove("--forkserver")
        from forkserver.servers.forkserver import start_server

        start_server(args)

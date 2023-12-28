import linecache
import signal
import subprocess
import sys
import time
import unittest
import asyncio
import subprocess


class IntegrationTest(unittest.TestCase):
    async def run_integration_test():
        try:
            server_process = await asyncio.create_subprocess_exec(
                "python", "-m", "forkserver", "--", "pytest", "tests/fast.py",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await server_process.communicate()
            print(stdout)
            print(stderr)
        except asyncio.TimeoutError:
            print("Timeout expired")

    asyncio.run(run_integration_test())

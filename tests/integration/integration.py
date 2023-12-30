import subprocess
import time
import unittest


class IntegrationTest(unittest.TestCase):
    def test_watches_files(self):
        process1 = subprocess.Popen(
            [
                "python",
                "-m",
                "forkserver",
                "--timeout",
                "1",
                "--loglevel",
                "DEBUG",
                "--",
                "pytest",
                "tests/unit/fast.py",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.1)
        subprocess.Popen(["touch", "tests/unit/fast.py"])
        stdout, stderr = process1.communicate()

        # Use this to inspect the output
        # print(stderr)

        # Listens to fie changes
        assert b"put event: FilesModifiedEvent(files={'./tests/unit/fast.py'}" in stderr
        # Uses the right checkpoint
        assert b"forwarding shutdown 2 -> 3" not in stderr
        assert b"forwarding shutdown 3 -> 4" in stderr
        assert b"loading modules at 3" in stderr
        # Reruns command
        assert b"running command: ['pytest', 'tests/unit/fast.py']" in stderr

    def test_listens_for_new_commands(self):
        process1 = subprocess.Popen(
            [
                "python",
                "-m",
                "forkserver",
                "--timeout",
                "1",
                "--loglevel",
                "DEBUG",
                "--",
                "pytest",
                "tests/unit/fast.py",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.1)

        # Make an POST HTTP request to HTTP server at localhost:7384/command with the payload 'pytest tests/unit/slow.py'
        import http.client

        conn = http.client.HTTPConnection("localhost", 7384)
        headers = {"Content-type": "plain/text"}
        payload = "pytest tests/unit/slow.py"
        conn.request("POST", "/command", payload, headers)
        response = conn.getresponse()
        conn.close()
        assert response.status == 200, "POST request failed"

        stdout, stderr = process1.communicate()

        # Use this to inspect the output
        # print(stderr)

        assert b" got event: CommandEvent" in stderr
        assert b" running command: pytest tests/unit/slow.py" in stderr

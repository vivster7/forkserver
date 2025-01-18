Example Flask server to test the forkserver functionality with.

To test forkserver, run:

```bash
uv run forkserver -- pytest -s  # first run
# wait for tests to finish, then ctrl+c to exit

uv run forkserver -- pytest -s  # second run
```

Now, you can edit the test file and see near instantaneous reloads. If you edit the application files, you'll notice the lag is longer due to the application being reloaded (and the artificial `time.sleep(3)` delay).

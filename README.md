# forkserver

A Python tool that dramatically speeds up repeated test execution through application preloading and intelligent process forking.

## Quickstart

```
pip install forkserver
forkserver -- pytest tests/unit
```

This sets up a server to re-run `pytest tests/unit` on file changes. It's better than using a typical file watcher because the re-run operation is able to leverage a copy of the application that has been preloaded into memory. There's a lot of caveats to this approach, so read on to learn more.

Check out the examples/ directory for a hands-on example.

## What is application preloading?

This is easiest to explain with a concrete example. The command `python server.py` starts a Python interpreter in a new process. For large programs, it can take 10+ seconds to evaluate all the code before the server is ready to accept connections.

So if our test code looks like this:

```py
import server  # slow, takes 10+ seconds to import
def test_add():
    assert 1+1==2
```

Then a simple `test_add()` which should take a few milliseconds to execute will take 10+ seconds to run. And we'll have to wait 10+ seconds every time we edit the test file and want to re-run the test. That's pretty frustrating.

What if we could cache the `import server` step? Then we'd only have to load it once, and we'd be able to iterate on the test code much more quickly. That's the core idea behind preloading. In practice, we can achieve this cache effect by loading `import server` in a parent process and then forking a child process to run the test. The Unix process model uses a copy-on-write strategy, so the child process will have read-access to a portion of memory that has already evaluated the code `import server`. Now, the child process can re-run the test without having to pay the 10 second penalty to run `import server`. Specifically in Python, when the child process evaluates the line `import server`, it'll immediately find an existing entry in the module cache (the module cache is why running `import server` twice doesn't take 20 seconds, the second invocation is a cache lookup).

Pictorially, this kind of looks like:
![Diagram of a process forking and sharing read-only memory](image.png)

## How forkserver works

Forkserver adds three capabilities on top of basic application preloading:

1. File watching (for rerunning commands on file changes)
2. HTTP server (for accepting new commands to run)
3. Multiple checkpoints (for partial reloading)

These capabilities communicate through a top-level coordination server.

The process tree looks like:
![Tree diagram showing process hierarchy.](image.png)

The file watcher and HTTP server are fairly straightforward. The multiple checkpoints feature is a bit more novel. In the example above describing preloading, we have a single checkpoint after preloading the line `import server`. The checkpoint is created by loading some code, forking a child process, and keeping the parent process alive as a saved checkpoint. Well, we can just apply this same idea multiple times when loading a single application. The default configuration for `forkserver` is to use 3 checkpoints:

1. Load the 3rd party packages and fork (checkpoint #1)
2. Load the application code and fork (checkpoint #2)
3. Load the test code and fork (checkpoint #3)

If you only change a test file, you can resume at checkpoint #3. If you change some application code, you can resume at checkpoint #2. If you change the 3rd party packages, you can resume at checkpoint #1.

Currently, this configuration only lives in code, but a good future project would be to make this configuration declarative and read from a config file.

## Known caveats

- Only works on unix-like systems (Linux, macOS, BSD, etc.) that uses a copy-on-write strategy for forked processes.
- Threading is not fork-safe, so make sure to only start threads after the last checkpoint is loaded.
- The file watcher currently listens to too many files (doesn't respect .gitignore)
- Currently does not leverage `gc.freeze()`. This [instagram blog post](https://instagram-engineering.com/copy-on-write-friendly-python-garbage-collection-ad6ed5233ddf) does a great job explaining why it's important to `gc.freeze` when trying to leverage shared copy-on-write memory.
- Attaching to stdin to support `ipdb`-style breakpoints does not work.

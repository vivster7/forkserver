import multiprocessing
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from forkserver.lib.events import CommandEvent

queue: Optional[multiprocessing.SimpleQueue] = None


class CommandHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/command":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            command = post_data.decode("utf-8")

            # Do something with the command
            print(f"Received command: {command}")
            queue.put(CommandEvent(command))
            
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Success")
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")


def http(q: multiprocessing.SimpleQueue) -> None:
    global queue
    queue = q
    server_address = ("", 7384)
    httpd = HTTPServer(server_address, CommandHandler)
    httpd.serve_forever()

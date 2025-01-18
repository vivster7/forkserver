import time
import flask

print("Loading app.py (slow)")
time.sleep(3)
print("Done loading app.py")


def create_app():
    app = flask.Flask(__name__)

    @app.route("/")
    def index():
        return "Hello, World!"

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()

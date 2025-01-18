from src.app import create_app


def test_index():
    """Test the index page returns 200"""
    app = create_app()
    with app.test_client() as client:
        rv = client.get("/")
        assert rv.status_code == 200
        assert b"Hello, World!" in rv.data

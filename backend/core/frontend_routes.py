"""Serve the exisiting frontend files to thru Flask"""

from pathlib import Path
from flask import redirect, send_from_directory, url_for

# Get frontend/ path
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

def register_frontend_routes(app):

    # Register home page
    @app.get("/")
    def frontend_home():
        return redirect(url_for("serve_frontend_file", filename="html/index.html"))

    # Serve resources
    @app.get("/frontend/<path:filename>")
    def serve_frontend_file(filename):
        return send_from_directory(FRONTEND_DIR, filename)
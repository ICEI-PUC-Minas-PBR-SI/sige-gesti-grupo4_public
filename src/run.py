"""Inicia o GesTI em modo de desenvolvimento: python run.py  →  http://127.0.0.1:5000"""
import os

from gesti import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("GESTI_HOST", "127.0.0.1"),
            port=int(os.environ.get("GESTI_PORT", "5000")),
            debug=os.environ.get("GESTI_DEBUG", "1") == "1")

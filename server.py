import os
import logging

from waitress import serve

from engine.wsgi import application

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve(application, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8765")), threads=6)

import sys
import os

# Path ke folder project
path = '/home/jazaniest07/absensi'
if path not in sys.path:
    sys.path.append(path)

from main import app  # app = FastAPI instance

# Gunakan WSGI adaptor
from fastapi.middleware.wsgi import WSGIMiddleware
application = WSGIMiddleware(app)

import importlib.metadata

try:
    __version__ = importlib.metadata.version(__name__)
except:
    __version__ = 'unknown'

import os

# Qt widget tests run headless. Must be set before any PySide6 import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sys import exit  # Just in case Nuitka throws another tantrum
import czeditor.util.installhelper
if __name__ == "__main__":
    # Checks for missing runtime dependencies and installs them
    # if possible or prompts the user to install them manually
    if czeditor.util.installhelper.checkAndInstall():
        exit(0)

import os
import sys

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QApplication

from czeditor.czeditor import *

# Set up resource paths for Qt internals like stylesheets
# Use importlib.resources when it's possible to do so
root = os.path.dirname(os.path.abspath(__file__))
QDir.addSearchPath("res", os.path.join(root, "res"))
for path in os.listdir(os.path.join(root, "res")):
    if os.path.isdir(os.path.join(root, "res", path)):
        QDir.addSearchPath(path, os.path.join(root, "res", path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec())

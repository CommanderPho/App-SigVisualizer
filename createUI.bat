@echo off
REM Generate PyQt5 UI python from Qt Designer .ui using current Python environment
REM Avoid hard-coded user paths to prevent "Failed to canonicalize script path"

python -m PyQt5.uic.pyuic -x ui_sigvisualizer.ui -o ui_sigvisualizer.py



# Project Structure

## Root Files
- `main.py` - Application entry point and main window initialization
- `sigvisualizer.py` - Main application class with UI logic and event handling
- `pyproject.toml` - Project configuration and dependencies
- `uv.lock` - Dependency lock file

## Core Components
- `ui_sigvisualizer.py` - Generated PyQt5 UI code (auto-generated, do not edit manually)
- `ui_sigvisualizer.ui` - Qt Designer UI definition file
- `datathread.py` - Background thread for LSL data streaming and processing
- `paintwidget.py` - Custom widget for real-time signal painting/visualization
- `pyqtgraph_paintwidget.py` - Alternative PyQtGraph-based visualization widget
- `consolewidget.py` - Console/logging widget component
- `LSL_sender.py` - Utility for sending test LSL streams

## Build & Distribution
- `main.spec` - PyInstaller specification for executable creation
- `createUI.bat` - Windows batch script to regenerate UI from .ui files
- `build/` - PyInstaller build artifacts
- `dist/` - Distribution files and executables

## Assets
- `icons/` - UI icons (chevron navigation)
- `sigvisualizer.ico` - Application icon
- `sigvisualizer.png` - Application logo
- `SigVisualizer_demo.gif` - Demo animation

## Development
- `.venv/` - Python virtual environment
- `__pycache__/` - Python bytecode cache
- `.python-version` - Python version specification
- `sigvisualizer.log` - Application log file

## Conventions
- UI files are generated from Qt Designer - edit `.ui` files, not `.py` UI files
- Main application logic in `sigvisualizer.py`, data handling in `datathread.py`
- Custom widgets follow PyQt5 patterns with signal/slot communication
- Logging configured with both console and file output
- Thread-safe data handling for real-time streaming
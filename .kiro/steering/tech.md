# Technology Stack

## Core Technologies
- **Python 3.11.9** - Primary language
- **PyQt5** - GUI framework for desktop application
- **PyLSL** - Lab Streaming Layer integration for real-time data streaming
- **PyQtGraph** - High-performance plotting library for signal visualization

## Build System & Packaging
- **uv** - Modern Python package manager (uv.lock present)
- **PyInstaller** - Application packaging for distribution
- **pyproject.toml** - Modern Python project configuration

## Key Dependencies
```toml
pylsl>=1.17.6          # LSL streaming protocol
pyqt5>=5.15.7,<6       # GUI framework
pyqtgraph>=0.13.7      # Real-time plotting
pyinstaller>=6.16.0    # Executable packaging
```

## Common Commands

### Development
```bash
# Install dependencies
uv sync

# Generate UI from Qt Designer files
python -m PyQt5.uic.pyuic -x ui_sigvisualizer.ui -o ui_sigvisualizer.py

# Run application
python main.py
```

### Building
```bash
# Create executable
pyinstaller main.spec

# Build UI (Windows batch)
createUI.bat
```

## Architecture Notes
- Qt Designer (.ui) files are converted to Python using PyQt5 UIC
- Multi-threaded architecture with QThread for data handling
- Signal/slot pattern for inter-component communication
- Custom painting widgets for high-performance real-time visualization
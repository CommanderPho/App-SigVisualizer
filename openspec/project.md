# Project Context

## Purpose
SigVisualizer is a desktop GUI for visualizing multi‑channel biosignals (primarily EEG) streamed via LabStreamingLayer (LSL) in real time. The app discovers available LSL streams, presents channel metadata, and renders time‑series plots with optional marker overlays. It is intended for quick inspection, debugging, and demonstration of LSL data streams.

## Tech Stack
- Python ≥ 3.9.13
- PyQt5 5.15.x for the desktop UI (Qt Designer `.ui` compiled to Python)
- pyqtgraph ≥ 0.13.7 for high‑performance plotting
- pylsl ≥ 1.17.6 for LSL discovery and data ingestion
- Packaging metadata via `pyproject.toml`; `uv.lock` present (Astral uv). Installation works with `pip` or `uv`.

## Project Conventions

### Code Style
- Pythonic naming: `snake_case` for modules, functions, and variables; `CamelCase` for classes.
- Qt signals/slots and UI object names may follow Qt's camelCase conventions (e.g., `updateStreamNames`).
- Prefer standard logging over `print`; module loggers use namespaces like `phohale.sigvisualizer`.
- Indentation: use 4 spaces in new code. Some legacy files may contain tabs; do not mix indentation within a file when modifying.

### Architecture Patterns
- Entry point: `main.py` creates the `QApplication`, instantiates `sigvisualizer.SigVisualizer` (a `QMainWindow`), and starts the event loop.
- UI: `ui_sigvisualizer.ui` is compiled to `ui_sigvisualizer.py` (see `createUI.bat`). The generated UI embeds a custom `PaintWidget` imported from `pyqtgraph_paintwidget`.
- Window wiring: `sigvisualizer.SigVisualizer`
  - Sets up icons, status bar, and left‑side stream tree (`QTreeWidget`).
  - Manages manual stream refresh and an auto‑refresh `QTimer` (default ~2s cadence).
  - Uses a `QThreadPool` to run `UpdateStreamsTask`, which calls `DataThread.update_streams` off the GUI thread.
  - Emits `stream_expanded` when a stream node expands; connected to data thread to switch active stream.
- Data ingestion: `datathread.DataThread` (`QThread`)
  - Resolves streams via `pylsl.resolve_streams()` and creates `pylsl.StreamInlet` per stream.
  - Extracts extended metadata (channel labels, sample rate, formats) and emits `updateStreamNames(metadata, default_idx)`.
  - Pulls chunks continuously in `run()`. For high sample rates (>1000Hz), computes downsampled chunks to keep UI performant.
  - Separately detects marker streams (String type with irregular rate) and emits marker data alongside signal data: `sendData(sig_ts, sig_buffer, marker_ts, marker_buffer)`.
- Rendering: `pyqtgraph_paintwidget.PaintWidget` (`pg.PlotWidget`)
  - Subscribes to `sendData` and `changedStream` signals from `DataThread`.
  - Computes per‑channel robust scaling (median/IQR), stacks channels vertically, and renders with pyqtgraph `PlotCurveItem`s.
  - Optionally overlays markers as a scatter series; pg UI controls are hidden for a simplified view.
- Utilities and legacy:
  - `LSL_sender.py` publishes an example 8‑channel 100Hz LSL stream for local testing.
  - `paintwidget.py` and `consolewidget.py` contain older QPainter‑based plotting; current UI uses pyqtgraph.

### Testing Strategy
- Manual end‑to‑end test
  1. Start a local LSL stream (e.g., `python LSL_sender.py`).
  2. Run the app (`python main.py`).
  3. Verify streams appear in the tree; channels populate with labels; plots update continuously; toggle auto‑refresh and manual refresh.
- No automated tests are defined yet. Future work: mock `pylsl` for data source tests and use `pytest-qt` for basic UI smoke tests.

### Git Workflow
- Branching: `feature/<name>` for new work (example: `feature/pyqtgraph-based-plots`).
- Commits: imperative present‑tense subjects; reference OpenSpec change IDs where applicable.
- Proposals/spec changes live under `openspec/changes/`; keep `openspec/specs/` aligned with deployed behavior.

## Domain Context
- Signals follow LSL conventions: multi‑channel numeric arrays plus optional marker streams.
- Channel labels are read from LSL metadata at `desc/channels/channel/label` and shown in the stream tree and y‑axis ticks.
- Marker streams are identified by String channel format and irregular sample rate, and are displayed as overlaid markers.

## Important Constraints
- UI responsiveness: all blocking I/O stays off the GUI thread. Data resolution and pulling occur in `QThread`/`QThreadPool`.
- Real‑time cadence: default auto‑refresh interval ~2000 ms; data processing per interval must complete within budget.
- High‑rate inputs: downsampling is applied for sample rates > 1000 Hz to avoid excessive rendering workload.
- Platform: primary development on Windows; PyQt5 is required (Qt6 is not targeted).
- Runtime: Python ≥ 3.9.13.

## External Dependencies
- LabStreamingLayer (runtime and stream producers).
- Python packages (declared in `pyproject.toml`):
  - `pylsl>=1.17.6`
  - `pyqt5>=5.15.7,<6` and `pyqt5-qt5==5.15.2`
  - `pyqtgraph>=0.13.7`
- Assets: `icons/` (SVG chevrons), `sigvisualizer.ico`, demo GIF.

### UI Code Generation
- Regenerate the UI module after editing `ui_sigvisualizer.ui`:
  - Recommended: `pyuic5 -x ui_sigvisualizer.ui -o ui_sigvisualizer.py`
  - The provided `createUI.bat` runs `pyuic5` with a machine‑specific path; update it locally as needed.

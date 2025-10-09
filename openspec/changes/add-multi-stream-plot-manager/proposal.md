## Why
The app originally displayed one selected LSL stream (multi‑channel) on the right, with traces rendered by a legacy `App-SigVisualizer.paintwidget.PaintWidget` (now unused). To support multiple active streams simultaneously and improve performance, a new pyqtgraph‑based `App-SigVisualizer.pyqtgraph_paintwidget.PaintWidget` was introduced but not fully wired. For greater flexibility than the current architecture allows, we need a container widget, `App-SigVisualizer.pyqtgraph_paintwidget.MultiStreamPlotManagingWidget`, to manage and render multiple streams at once. This proposal formalizes that widget and its signal wiring to enable multi‑stream preview while maintaining stability and responsiveness.

## What Changes
- Add a multi-stream plotting container `MultiStreamPlotManagingWidget` managing a grid of per-stream plots.
- Wire data ingestion (`DataThread.updateStreamNames`, `sendData`, `changedStream`) to support multi-stream metadata and updates.
- Define behaviors for per-stream channel enabling, y-offset stacking, and marker overlays.
- Keep current single-stream selection compatible while enabling parallel stream display scaffolding.
- Make the resultant app both performant and stable/robust to changing streams.
 - Expose a clear container API: `reset()`, `on_streams_updated(metadata, default_idx)`, and `get_data(sig_ts, sig_buffer, marker_ts, marker_buffer)`.
 - Ensure GUI-thread–only rendering; keep data ingestion off the GUI thread.
 - No breaking changes are expected.

## Impact
- Affected specs: `plotting`
- Affected code: `pyqtgraph_paintwidget.py` (new container widget), `sigvisualizer.py` (wiring), `datathread.py` (multi-stream semantics), `ui_sigvisualizer.py` (uses custom widget)
 - Risks: `DataThread` currently drives a single active stream index; true concurrent updates may require a follow‑up refactor to emit per‑stream chunks.
 - Test plan: use `LSL_sender.py`, run the app, verify multi‑stream rendering, channel labels, and marker overlays; confirm auto‑refresh and manual refresh behaviors.


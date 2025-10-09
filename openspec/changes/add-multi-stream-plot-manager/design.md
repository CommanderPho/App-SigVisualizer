## Context
Current UI uses a single `App-SigVisualizer.pyqtgraph_paintwidget.PaintWidget` to show one signal stream with multiple channels. We are introducing `MultiStreamPlotManagingWidget` (pyqtgraph `GraphicsLayoutWidget`) to manage multiple per-stream plots, leveraging existing `DataThread` signals.

## Goals / Non-Goals
- Goals: multi-stream plotting container, robust scaling, marker overlays, metadata-driven rebuilds.
- Non-Goals: persistent settings, recording/export, advanced analysis.

## Decisions
- Use `pg.GraphicsLayoutWidget` to host per-stream `PlotItem`s in rows.
- Keep `DataThread` as single worker emitting combined signals; reuse `updateStreamNames`, `sendData`, `changedStream` for now.
- Compute per-channel median/IQR on recent chunk for stable display.
- Track channel enable flags from tree UI via a simple mapping on the container.

## Risks / Trade-offs
- Single `sendData` currently tied to one active stream index; extending to true multi-stream updates may require refactor. Initial step keeps compatibility and focuses on container lifecycle and wiring.

## Migration Plan
1) Land container widget and wiring without breaking single-stream path.
2) Incrementally extend `DataThread` to emit per-stream chunks, updating the container logic accordingly.

## Open Questions
- Do we need per-stream time bases if sample rates differ? Initial version assumes independent x-ranges per plot.
- Should channel toggles apply per-stream or globally? Assume per-stream.



## Context
Current plots use pyqtgraph `PlotWidget`/`PlotItem` with the UI controls mostly hidden for a simplified look. Users have requested quick y-range manipulation for inspection without adding custom toolbars.

## Goals / Non-Goals
- Goals: enable built-in context menus; support double-click auto-range; provide a reset y-scale action integrated with existing robust scaling.
- Non-Goals: persistence of settings; cross-plot y-linking; toolbar UX redesign.

## Decisions
- Use pyqtgraph built-in context menu (right-click) by not suppressing it on the `PlotItem`/`ViewBox`.
- Add a custom "Reset Y-Scale" menu action that calls the existing robust-scaling function used after new data arrives.
- Keep mouse interactions default for vertical zoom; avoid overriding `ViewBox` behaviors unless necessary.

## Risks / Trade-offs
- Users might unintentionally change view; mitigated with obvious reset and double-click auto-range.
- Multi-stream: ensure each plot retains independent view state; do not link y across plots.

## Migration Plan
1) Enable context menus on plot items; verify default actions present.
2) Add reset action into the same menu; wire to robust scaling recalculation.
3) Validate double-click auto-range remains active.
4) Manual test with live LSL data; confirm stacked offsets preserved.

## Open Questions
- Should reset target only the active plot or all visible plots? Initial: active plot only.



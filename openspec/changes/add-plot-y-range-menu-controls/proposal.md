## Why
Users need quick, intuitive control over y-range and scaling while inspecting live signals. Today, robust per-channel scaling is applied automatically and most pyqtgraph UI controls are hidden. Enabling the typical built-in pyqtgraph menus (and a simple reset action) provides a familiar, low-effort way to adjust and recover y-range during analysis without introducing heavy custom UI.

## What Changes
- Enable pyqtgraph built-in context menus on signal plots to expose standard y-range controls (zoom, auto-range, view reset).
- Add a lightweight "Reset Y-Scale" action to restore the default robust scaling state for the active plot.
- Ensure double-click on the plot area triggers y auto-range (pyqtgraph default) and that mouse interactions for vertical zoom are available.
- Keep stacked-channel offsets intact while allowing y-zoom of the overall plot; no cross-plot y-linking.
- No persistence in this change; settings reset on app restart.
- No breaking changes expected.

## Impact
- Affected specs: `plotting`
- Affected code: `pyqtgraph_paintwidget.py` (enable menus, add reset action), `sigvisualizer.py` (wiring if needed), `ui_sigvisualizer.py` (no structural changes expected)
- Risks: Users may accidentally zoom; mitigation via menu-driven reset and double-click auto-range.
- Out of scope: toolbar buttons, persistence, cross-plot y-linking.



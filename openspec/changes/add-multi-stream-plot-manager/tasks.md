## 1. Implementation
- [ ] 1.1 Finalize `MultiStreamPlotManagingWidget` layout and lifecycle (reset, build from metadata)
- [ ] 1.2 Connect `updateStreamNames` to container `on_streams_updated(metadata, default_idx)`
- [ ] 1.3 Wire `sendData(sig_ts, sig_buffer, marker_ts, marker_buffer)` to update plots per active streams
- [ ] 1.4 Track per-channel enable state from tree UI (toggle on render)
- [ ] 1.5 Preserve single-stream selection compatibility (`changedStream`) while rendering multiple
- [ ] 1.6 Robust scaling (median/IQR) per channel and y-axis labels
- [ ] 1.7 Marker overlay rendering aligned to time base
- [ ] 1.8 Manual validation: run demo stream and verify multi-stream rendering

## 2. Tooling & Validation
- [ ] 2.1 `openspec validate add-multi-stream-plot-manager --strict`
- [ ] 2.2 Update proposal/tasks if validation raises issues



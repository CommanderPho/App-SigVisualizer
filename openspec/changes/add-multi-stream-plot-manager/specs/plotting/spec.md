## ADDED Requirements

### Requirement: Multi-Stream Plot Management
The system SHALL provide a `MultiStreamPlotManagingWidget` that manages multiple LSL streams, each with multiple channels, and renders them concurrently using pyqtgraph.

#### Scenario: Display multiple signal streams concurrently
- **WHEN** multiple non-marker LSL streams are resolved
- **THEN** a dedicated plot area SHALL be created per stream with stacked channel traces
- **AND** each plot SHALL display channel labels as y-axis ticks
- **AND** the x-axis SHALL represent time aligned to incoming timestamps (or sample index fallback)

#### Scenario: Handle marker streams overlay
- **WHEN** marker streams are present alongside signal streams
- **THEN** marker events SHALL be overlaid as symbols on the relevant stream plot using the same time base

#### Scenario: Metadata updates rebuild plots
- **WHEN** `updateStreamNames(metadata, default_idx)` is emitted
- **THEN** the widget SHALL rebuild its child plots to reflect the current streams and channels, removing stale ones

#### Scenario: Channel enable/disable state tracked
- **WHEN** channels are toggled in the UI tree
- **THEN** the widget SHALL track per-channel enable state and only render enabled channels

#### Scenario: Robust scaling per channel
- **WHEN** rendering channel traces
- **THEN** the widget SHALL compute robust scaling (median/IQR) per channel to normalize display



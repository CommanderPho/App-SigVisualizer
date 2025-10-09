## ADDED Requirements

### Requirement: Plot Y-Range Controls via Pyqtgraph Menus
The system SHALL expose standard pyqtgraph context menu controls on signal plots to allow quick y-range adjustments and reset without custom heavy UI.

#### Scenario: Right-click shows pyqtgraph view menu
- **WHEN** the user right-clicks within a signal plot area
- **THEN** the built-in pyqtgraph context menu SHALL appear
- **AND** it SHALL include actions for ViewBox auto-range and view reset

#### Scenario: Double-click auto-ranges y-axis
- **WHEN** the user double-clicks within a signal plot area
- **THEN** the plot y-range SHALL auto-range to fit currently visible data

#### Scenario: Mouse drag zoom vertically
- **WHEN** the user drags the mouse with standard pyqtgraph modifiers
- **THEN** the plot SHALL allow vertical zooming using built-in interactions

#### Scenario: Reset Y-Scale action restores default scaling
- **WHEN** the user selects "Reset Y-Scale" from the context menu
- **THEN** the plot SHALL restore its default robust scaling state as defined by the rendering pipeline

#### Scenario: Preserve stacked-channel offsets
- **WHEN** the user adjusts y-range via menu or interactions
- **THEN** channel stacking offsets SHALL remain intact, affecting only the overall view range and not relative channel offsets



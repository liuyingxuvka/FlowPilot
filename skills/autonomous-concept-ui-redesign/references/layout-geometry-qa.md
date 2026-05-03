# Layout Geometry QA

Use this reference when verifying rendered UI. The goal is to prove the layout
does not depend only on human or model interpretation of screenshots.

## Evidence Priority

1. Rendered geometry data from the browser or UI runtime.
2. Screenshot dimensions and viewport/window dimensions.
3. Visual screenshot review by the model.

Screenshots can reveal visual quality problems, but they are not enough to prove
that text is not clipped or controls are not overlapped.

## Required Matrix

Use project-appropriate sizes, but prefer at least:

- desktop: `1440x900`;
- normal laptop/window: `1280x720`;
- compact: `1024x768` or the product's minimum supported size;
- wide/large: `1920x1080`;
- high-DPI Windows evidence when available: record logical window size, physical
  screenshot dimensions, and scale factor if known.

For mobile-capable web surfaces, add the project's normal mobile breakpoint.

## Geometry Checks

For each material screen or state:

- no text bounding box exceeds its visible parent unless intentional truncation
  has a discoverable full-text path;
- no important element has zero width, zero height, or is outside the viewport;
- no interactive target is visually covered by another element;
- no visible control is unreachable by pointer or keyboard;
- no unexpected horizontal page scrolling;
- sticky or fixed headers/footers do not cover scrollable content;
- dialogs, menus, tooltips, drawers, dropdowns, and popovers remain inside the
  visible area or provide a usable overflow strategy;
- loading, empty, error, hover, focus, active, disabled, and selected states do
  not introduce overlap or clipping when they are relevant.

## Failure Handling

- Fix geometry failures before visual polish.
- If the failure is caused by wrong information architecture, return to the
  design contract instead of repeatedly changing spacing values.
- If a product intentionally uses two-dimensional layouts, record the exception
  and verify each cell/item still has a usable access path.

## Report Fields

Record:

- viewport/window size;
- screenshot pixel size;
- checked states;
- geometry failures found;
- fixes made;
- unresolved risks.

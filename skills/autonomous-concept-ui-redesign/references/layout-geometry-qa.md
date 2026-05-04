# Layout Geometry QA

Use this reference when verifying rendered UI. The goal is to prove the layout
does not depend only on human or model interpretation of screenshots.

## Evidence Priority

1. Rendered geometry data from the browser or UI runtime.
2. Real platform screenshots and viewport/window dimensions.
3. Offscreen/headless screenshots, only after renderer trust is checked.
4. Visual screenshot review by the model.

Screenshots can reveal visual quality problems, but they are not enough to prove
that text is not clipped or controls are not overlapped.

## Native Desktop Screenshot Trust

For native desktop apps, including Qt/PySide, Electron, Tk, WinUI, SwiftUI,
Compose, and Flutter desktop, offscreen or headless renderers are probes rather
than proof by default. Before accepting them as final visual evidence, inspect
whether text is readable, glyphs are present, fonts look plausible, icons render,
window chrome is represented correctly, transparency is not corrupt, and the
captured state matches a real launched app.

If an offscreen/headless capture shows missing glyph boxes, blank widgets,
wrong font fallback, clipped platform chrome, incorrect scale, or other renderer
artifacts, recapture from the real desktop platform. When real platform capture
is unavailable, mark screenshot QA `partial` or `blocked` and state exactly what
could not be trusted. Do not use a broken offscreen screenshot to pass a visual,
localization, or geometry gate.

## Required Matrix

Use project-appropriate sizes, but prefer at least:

- desktop: `1440x900`;
- normal laptop/window: `1280x720`;
- compact: `1024x768` or the product's minimum supported size;
- wide/large: `1920x1080`;
- high-DPI Windows evidence when available: record logical window size, physical
  screenshot dimensions, and scale factor if known.
- desktop/native/app-shell identity evidence when applicable: record whether the
  same selected app icon appears in the window, taskbar/dock, tray/menu-bar, and
  package/shortcut metadata.
- native desktop capture provenance when applicable: record real platform,
  offscreen/headless, remote desktop, or package/runtime capture, and whether it
  was accepted, recaptured, partial, or blocked.

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
- app/software icon is not only rendered inside the app content; for applicable
  software artifacts it is bound to the real platform identity surface or the
  gap is recorded as partial/blocked.
- native desktop screenshot text and icon rendering is trustworthy, or the
  evidence is recaptured from the real platform before final acceptance.

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
- screenshot capture provenance and trust verdict for native desktop surfaces;
- checked states;
- app icon identity surfaces checked when applicable;
- geometry failures found;
- fixes made;
- unresolved risks.

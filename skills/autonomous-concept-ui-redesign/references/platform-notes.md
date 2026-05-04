# Platform Notes

Use these notes only when the rendering surface makes normal web screenshot assumptions weak.

## Web Apps

- Prefer browser screenshots at desktop and mobile widths.
- Check responsive collapse, sticky regions, dialogs, dropdowns, and table overflow.
- Use existing component libraries and route patterns before adding primitives.
- Do not leave a generated concept image as the only source of truth; implement semantic HTML, accessible names, focus states, and real copy.

## Desktop Apps

- Screenshot the actual window at realistic user size.
- On high-DPI Windows systems, read both logical and physical display size when possible. Logical APIs can return scaled values such as 1280x720 on a 3840x2160 panel.
- For full-desktop proof, use a DPI-aware capture path, capture the physical screen dimensions, and verify the saved image dimensions match those physical dimensions.
- Bring the target app to the foreground or temporarily topmost before capture; reject screenshots that capture the agent host, a browser preview, or another app instead.
- When using full-screen proof, include the Windows taskbar or another clear desktop boundary unless there is recorded evidence that it is hidden.
- When using window-only proof, confirm the title bar/top edge, left/right edges, and bottom/status area are visible. A cropped corner or missing bottom edge is not valid evidence.
- On high-DPI systems, confirm the capture is not cropped, scaled to one quadrant, wrong-window, or blurry.
- Click changed navigation, footer controls, popups, and settings windows.
- For embedded widgets, test through the host window, not only isolated child widgets.

## Canvas Or Custom Drawing UI

- Measure rendered text when possible; layout math alone can miss clipping.
- Reserve explicit regions for title, body, footer, badges, and actions.
- Validate sparse data, dense data, empty states, and long labels.
- Avoid patchy optional rendering paths unless they protect a real supported runtime boundary.

## Slide Decks And Presentations

- Treat rendered slide images as screenshots.
- Check text fit, alignment, hierarchy, and whether the slide matches the visual target.
- Prefer revising the slide layout over shrinking text until it becomes unreadable.
- Keep concept images as direction; exact slide copy and charts must come from the deck data.

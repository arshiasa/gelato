# Rule: Bypassing Android Forced Dark Mode via Direct Canvas Vector Drawing

## 1. Problem
When mobile browsers enforce dark mode, they intercept CSS rules and invert light colors, including loaded `<img>` tags, SVG assets, and backgrounds. Standard properties like `color-scheme: light only` or `forced-color-adjust: none` are frequently overridden.

## 2. Root Cause
The browser's layout engine applies forced inversion filters to parsed DOM elements and image rasterizers. However, the browser treats the raw 2D pixel buffer of an HTML5 `<canvas>` as a dynamic script-drawn bitmap, leaving it immune to inversion.

## 3. The Canvas Vector Solution (Strict Pattern)
To ensure light-mode fidelity for vector assets or custom graphics in any environment:

1. **Element Swap**: Replace the `<img>` or `<svg>` tag with a `<canvas>` element.
2. **Device Pixel Scaling**: Match display dimensions while scaling the internal resolution to prevent blurriness:
   ```javascript
   const dpr = window.devicePixelRatio || 1;
   const rect = canvas.getBoundingClientRect();
   canvas.width = rect.width * dpr;
   canvas.height = rect.height * dpr;
   ctx.scale(rect.width * dpr / originalWidth, rect.height * dpr / originalHeight);
   ```
3. **Pure JS Vector Drawing**: Instead of drawing a loaded SVG file with `drawImage()` (which can still trigger raster-level inversion), draw the shapes directly onto the canvas using 2D rendering instructions:
   - `ctx.arc()`
   - `ctx.ellipse()`
   - `ctx.quadraticCurveTo()`
   - `ctx.fillStyle` and `ctx.strokeStyle`
   - Emojis / Text with `ctx.fillText()`
4. **Fidelity**: This guarantees absolute control over color values, completely bypassing browser-side color-scheme overrides.

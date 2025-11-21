# Logo Size Requirements

## Frontend/Web
- `favicon.ico`: 16x16, 32x32 (embedded)
- PWA icons: 72x72, 96x96, 128x128, 144x144, 152x152, 192x192, 384x384, 512x512

## macOS App
- AppIcon: 16, 32, 64, 128, 256, 512, 1024 (@1x and @2x)
- Menu bar: 16x16@2x (template, black on transparent)

## Documentation
- Social preview: 1280x640 (GitHub OG image)
- README header: 800x200 (suggested)

## Source Assets
- Preferred: `SVG` vector artwork (single-file single-source)
- Raster (PNG) recommended at least `1024x1024` for icon source

## Notes
- Use lossless PNG for raster exports. Keep original SVG for vector builds.
- macOS `.icns` generation requires `iconutil` (macOS). The script will create the `.iconset` folder and call `iconutil` when available.
- The provided `scripts/update-logos.sh` automates generation and copying to `frontend/`, `server/static/`, and `logo/` appicon sets.

# Branding

Original logo and banner files. They are not served by the app and do not enter the Docker image.

## Versions

| File | Look | Used for |
|---|---|---|
| `mk_logo_clair.png` | Dark grey disk, 5400 × 5400 | Every logo and icon in the app (its dark theme) |
| `mk_banner_clair.png` | Dark grey band, 6950 × 1124 | Sign-in page, README on GitHub's dark theme |
| `mk_logo_sombre.png` | White disk, 5400 × 5400 | Notification badge shape; kept for a future light theme |
| `mk_banner_sombre.png` | White band, 6964 × 1181 | README on GitHub's light theme |

The dark-looking versions (« clair » files) were picked for the app's dark theme.

`mk_banner_sombre-1280.png` and `mk_banner_clair-1280.png` are the reduced copies the README shows.

## Derived files

The app only loads reduced copies. This script rebuilds them all:

```
powershell -ExecutionPolicy Bypass -File scripts/generate_brand_assets.ps1
```

It needs Windows (System.Drawing). It writes to `frontend/public/assets/icons/`:

- `mk-favicon-32.png` and `mk-favicon-48.png`: browser tab.
- `mk-apple-touch-icon-180.png`: iPhone home screen, on an opaque background.
- `mk-icon-192.png`, `mk-icon-512.png` and `mk-icon-maskable-512.png`: installed app (manifest) and notification icon.
- `mk-badge-96.png`: notification badge, a white owl shape.
- `mk-logo-128.png`: logo in the portal bar, the admin menu, sign-in and setup.
- `mk-banner-700.png`: sign-in page banner.

It also writes `frontend/src/assets/icons/mk-logo-96.png`, built into the app for the reconnect screen, and the two README copies above.

## Changing the artwork

1. Replace the originals here.
2. Give the derived files new names in the script, so browsers and phones do not keep the old image.
3. Update the references: `frontend/index.html`, `frontend/public/manifest.json`, `frontend/public/sw.js`, the components that show the logo or banner, and the README files.

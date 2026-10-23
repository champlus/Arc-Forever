# Arc Forever — Use Arc Browser Offline & After Shutdown (macOS)

**Keep using Arc Browser on macOS forever — offline, without cloud login, and with all your Spaces, pinned tabs, extensions, and profile intact.**

[简体中文](README.zh-CN.md) · [Compatibility](docs/compatibility.md) · [Architecture](docs/architecture.md)

## Features

- **Bypass Account Shutdown**: Handles authentication locally and disables forced sign-out so Arc continues to launch and work after official cloud services end.
- **Keep Your Entire Workflow**: Works directly on your installed `Arc.app` — your Spaces, pinned tabs, favorites, history, and extensions stay right where they are.
- **One-Click & Reversible**: Automatically backs up original files and lets you restore your installation to its untouched state at any time.
- **Sidebar Bookmark Exporter**: Includes a standalone utility to export all your Arc Spaces and pinned tabs into standard HTML bookmarks and JSON.

## Quick Start

Requires macOS with Python 3 and Xcode Command Line Tools (`xcode-select --install`). Quit Arc before running.

### Option 1: Double-Click Menu (Recommended)
Download this repository and double-click [`Arc Forever.command`](Arc%20Forever.command) in Finder to apply, check status, or restore from an interactive Terminal menu.

### Option 2: Command Line
```sh
git clone https://github.com/ChambersXDU/Arc-Forever.git
cd Arc-Forever

# Enable local authentication patch
python3 arc_forever.py apply
```

Then open Arc as usual.

### Common Commands
```sh
# Check current patch status
python3 arc_forever.py status

# Restore untouched original Arc files
python3 arc_forever.py restore

# Export Arc Spaces & pinned tabs to HTML bookmarks + JSON
python3 tools/export_sidebar.py --output ./arc-bookmarks
```

## License

Released under the [MIT License](LICENSE).

# Arc Forever — Make Arc Great Again

Keep using Arc Browser on macOS after the official shutdown — offline, account-free, with all your Spaces, pinned tabs, extensions, and profile intact.

[简体中文](README.zh-CN.md) · [Compatibility](docs/compatibility.md) · [Architecture](docs/architecture.md)

## Features

- **Bypass Account Shutdown**: Handles authentication locally and disables forced sign-out so Arc continues to launch and work after official cloud services end.
- **Keep Your Entire Workflow**: Works directly on your installed `Arc.app` — your Spaces, pinned tabs, favorites, history, and extensions stay right where they are.
- **One-Click & Reversible**: Automatically backs up original files and lets you restore your installation to its untouched state at any time.

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
```

## License

Released under the [MIT License](LICENSE).

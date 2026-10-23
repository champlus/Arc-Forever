# Arc Forever

**Keep using Arc Browser on macOS with local authentication after account shutdown.**

Arc Forever is a lightweight, reversible in-place patch tool. It preserves your existing Arc profile and local authentication state, allowing you to launch and browse normally without depending on official cloud account servers.

[简体中文](README.zh-CN.md) · [Compatibility](docs/compatibility.md) · [Architecture](docs/architecture.md) · [Arc Official Notice](https://arc.net/)

## Highlights

- **In-place & Reversible**: Modifies your installed Arc.app directly, automatically backs up original files, and restores cleanly at any time.
- **Preserves Your Setup**: Retains your existing Spaces, pinned tabs, favorites, extensions, and profile without creating duplicate apps.
- **Local Session Preservation**: Prevents remote sign-out when cloud accounts are disabled, keeping browsing functional offline.
- **SIP Friendly**: Works on standard macOS security configurations without needing to disable System Integrity Protection.

## Quick Start

### Prerequisites
- macOS
- Python 3 & Command Line Tools (`xcode-select --install`)
- Arc installed with an existing logged-in profile (please quit Arc before running the tool)

### Usage

**Option 1: Interactive Menu**  
Double-click [Arc Forever.command](Arc%20Forever.command) in Finder to run the bilingual menu.

**Option 2: Command Line**  
```sh
git clone https://github.com/ChambersXDU/Arc-Forever.git
cd Arc-Forever

# Check installation status
python3 arc_forever.py status

# Apply the patch
python3 arc_forever.py apply

# Restore original files whenever needed
python3 arc_forever.py restore
```

After applying, launch Arc as you normally would.

## Backup & Restore

Original binaries and configuration snapshots are saved to:  
`~/Library/Application Support/Arc Forever/Backups`

Running `python3 arc_forever.py restore` verifies hashes and restores your Arc installation to its untouched state.

## Notes

- **Cloud Services**: Features relying on official backends (such as Arc Sync) are unavailable once cloud servers go offline.
- **Keychain Prompts**: Because the app is re-signed, macOS may prompt for Keychain permissions upon first launch; click "Always Allow".
- **Browser Engine**: This project preserves local usability; it does not track or update the underlying Chromium engine.

## License

This project is licensed under the [MIT License](LICENSE). Arc and its trademarks belong to The Browser Company.

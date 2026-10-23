import argparse
import json
from pathlib import Path
import subprocess
import sys
from .patcher import apply, restore, status, DEFAULT_BACKUPS


def _short_path(path_str):
    try:
        home = str(Path.home())
        if path_str.startswith(home + '/'):
            return '~' + path_str[len(home):]
    except Exception:
        pass
    return path_str


def format_status(result):
    lines = [
        f"App:       {result['app']}",
        f"Version:   {result['version']} ({result['build']})",
    ]
    if result.get('patched'):
        intact = result.get('guard_intact') and result.get('carrier_intact')
        health = 'Healthy' if intact else 'Modified / Needs Restore'
        lines.append(f"Status:    Patched & Active ({health})")
        lines.append(f"Mode:      {result.get('strategy', 'unknown')}")
        if result.get('backup'):
            lines.append(f"Backup:    {_short_path(result['backup'])}")
    else:
        supported = 'Supported (Ready to patch)' if result.get('supported') else 'Unsupported Arc build'
        lines.append(f"Status:    Unpatched — {supported}")
    return '\n'.join(lines)


def format_apply(result):
    lines = [
        "✓ Arc Forever patch applied successfully!",
        "",
        format_status(result),
        "",
        "You can now launch Arc as usual.",
    ]
    return '\n'.join(lines)


def format_restore(result):
    lines = [
        "✓ Original Arc restored successfully!",
        "",
        f"App:       {result['app']}",
        f"Restored:  {_short_path(result['backup'])}",
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Arc Forever — Keep using Arc Browser offline and after shutdown on macOS.')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('status', 'apply', 'restore'):
        p = sub.add_parser(name)
        p.add_argument('--app', type=Path, default=Path('/Applications/Arc.app'))
        p.add_argument('--json', action='store_true', help='Output raw JSON')
        if name == 'apply':
            p.add_argument('--backup-dir', type=Path, default=DEFAULT_BACKUPS)
            p.add_argument('--strategy', choices=('auto', 'framework', 'main'), default='auto')
        if name == 'restore':
            p.add_argument('--backup', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'status':
            result = status(args.app)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_status(result))
        elif args.command == 'apply':
            result = apply(args.app, args.backup_dir, args.strategy)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_apply(result))
        else:
            result = restore(args.app, args.backup)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_restore(result))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr, file=sys.stderr)
        return 1

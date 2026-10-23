import argparse
import json
from pathlib import Path
import subprocess
import sys
from .patcher import apply, restore, status, DEFAULT_BACKUPS


def main():
    parser = argparse.ArgumentParser(description='Arc Forever — reversible in-place local account patch for Arc Browser on macOS.')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('status', 'apply', 'restore'):
        p = sub.add_parser(name)
        p.add_argument('--app', type=Path, default=Path('/Applications/Arc.app'))
        if name == 'apply':
            p.add_argument('--backup-dir', type=Path, default=DEFAULT_BACKUPS)
            p.add_argument('--strategy', choices=('auto', 'framework', 'main'), default='auto')
        if name == 'restore':
            p.add_argument('--backup', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'status':
            result = status(args.app)
        elif args.command == 'apply':
            result = apply(args.app, args.backup_dir, args.strategy)
        else:
            result = restore(args.app, args.backup)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Arc Forever: ' + str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr, file=sys.stderr)
        return 1

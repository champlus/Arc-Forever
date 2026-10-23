#!/usr/bin/env python3
"""Read Arc's local sidebar, exporting links without an Arc account or running app."""
import argparse
import html
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def mapping(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, list) or len(value) % 2:
        raise ValueError('Expected a Swift dictionary encoded as alternating key/value entries')
    result = {}
    for key, item in zip(value[::2], value[1::2]):
        if not isinstance(key, str) or not isinstance(item, dict) or key in result:
            raise ValueError('Unsupported or duplicate dictionary entry')
        result[key] = item
    return result


def extract(document):
    containers = document.get('sidebar', {}).get('containers')
    if not isinstance(containers, list):
        raise ValueError('Unsupported sidebar format: missing containers')
    links, seen = [], set()
    for container in containers:
        if 'items' not in container:
            continue
        items = mapping(container['items'])
        spaces = mapping(container.get('spaces', []))
        roots = {}
        for space_id, space in spaces.items():
            for root in space.get('containerIDs', []):
                if isinstance(root, str):
                    roots[root] = (space_id, space.get('title') or 'Untitled Space')
        for item_id, item in items.items():
            tab = item.get('data', {}).get('tab')
            if not isinstance(tab, dict) or not tab.get('savedURL'):
                continue
            url = tab['savedURL']
            if not isinstance(url, str):
                raise ValueError('Unsupported tab URL value')
            path, ancestor, visited = [], item_id, set()
            space_id, space_title = None, 'Unassigned / Favorites'
            while ancestor:
                if ancestor in visited:
                    raise ValueError('Sidebar parent cycle detected')
                visited.add(ancestor)
                if ancestor in roots:
                    space_id, space_title = roots[ancestor]
                    break
                parent = items.get(ancestor)
                if parent is None:
                    break
                if ancestor != item_id and parent.get('title'):
                    path.append(parent['title'])
                ancestor = parent.get('parentID')
            identity = (space_id, item_id)
            if identity in seen:
                continue
            seen.add(identity)
            links.append({'id': item_id, 'space_id': space_id, 'space': space_title,
                          'folders': list(reversed(path)), 'url': url,
                          'title': item.get('title') or tab.get('savedTitle') or url})
    return links


def bookmarks(links):
    tree = {}
    skipped = 0
    for link in links:
        if urlsplit(link['url']).scheme.lower() not in ('http', 'https', 'ftp', 'file'):
            skipped += 1
            continue
        node = tree
        for folder in [link['space'], *link['folders']]:
            node = node.setdefault(('folder', folder), {})
        node[('link', link['id'])] = link

    def render(node):
        lines = ['<DL><p>']
        for (kind, key), value in node.items():
            if kind == 'folder':
                lines.append('<DT><H3>' + html.escape(key) + '</H3>')
                lines.extend(render(value))
            else:
                lines.append('<DT><A HREF="' + html.escape(value['url'], quote=True)
                             + '">' + html.escape(value['title']) + '</A>')
        return lines + ['</DL><p>']

    header = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>', '<META HTTP-EQUIV="Content-Type" '
              'CONTENT="text/html; charset=UTF-8">', '<TITLE>Arc Sidebar</TITLE>', '<H1>Arc Sidebar</H1>']
    return '\n'.join(header + render(tree)) + '\n', skipped


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.home() /
                        'Library/Application Support/Arc/StorableSidebar.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    links = extract(json.loads(args.source.read_text()))
    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    (args.output / 'tabs.json').write_text(json.dumps(links, ensure_ascii=False, indent=2) + '\n')
    content, skipped = bookmarks(links)
    (args.output / 'bookmarks.html').write_text(content)
    print(json.dumps({'tabs': len(links), 'spaces': len({x['space_id'] for x in links}),
                      'html_omitted_internal_or_unsafe_urls': skipped, 'output': str(args.output.resolve())}))


if __name__ == '__main__':
    main()

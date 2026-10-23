import unittest

from tools.export_sidebar import bookmarks, extract, mapping


class SidebarTests(unittest.TestCase):
    def sample(self):
        return {'sidebar': {'containers': [{'global': {}}, {
            'spaces': ['space-a', {'title': 'Work', 'containerIDs': ['root']}],
            'items': ['root', {'parentID': None},
                      'folder', {'parentID': 'root', 'title': 'A&B'},
                      'tab', {'parentID': 'folder', 'title': '<Custom>', 'data': {
                          'tab': {'savedURL': 'https://example.com/?x="y"&z=1', 'savedTitle': 'Original'}}}]
        }]}}

    def test_real_swift_dictionary_shape_and_folder_chain(self):
        links = extract(self.sample())
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['space'], 'Work')
        self.assertEqual(links[0]['folders'], ['A&B'])
        self.assertEqual(links[0]['title'], '<Custom>')
        markup, skipped = bookmarks(links)
        self.assertIn('&lt;Custom&gt;', markup)
        self.assertIn('A&amp;B', markup)
        self.assertIn('&quot;y&quot;&amp;z=1', markup)
        self.assertEqual(skipped, 0)

    def test_parent_cycle_fails(self):
        doc = self.sample()
        doc['sidebar']['containers'][1]['items'][3]['parentID'] = 'tab'
        with self.assertRaises(ValueError):
            extract(doc)

    def test_rejects_corrupt_dictionary(self):
        with self.assertRaises(ValueError):
            mapping(['orphan'])
        with self.assertRaises(ValueError):
            mapping(['id', {}, 'id', {}])

    def test_javascript_is_retained_as_data_but_not_clickable(self):
        doc = self.sample()
        doc['sidebar']['containers'][1]['items'][-1]['data']['tab']['savedURL'] = 'javascript:alert(1)'
        links = extract(doc)
        markup, skipped = bookmarks(links)
        self.assertEqual(links[0]['url'], 'javascript:alert(1)')
        self.assertNotIn('javascript:', markup)
        self.assertEqual(skipped, 1)


if __name__ == '__main__':
    unittest.main()

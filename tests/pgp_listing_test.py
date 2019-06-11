import unittest

from pgp_listing import *


class TestSortingEntries(unittest.TestCase):
    def setUp(self) -> None:
        self.raw_fingerprint = """
        pub   4096R/85FBBD09 2019-03-11\n
        Key fingerprint = 6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09\n
        uid       [ unknown] Kate Whalen <Kate.Whalen@theguardian.com>\n
        sub 2048R/8FA007E8 2019-03-11"""

    def test_parse_fingerprint(self):
        expected = parse_fingerprint(self.raw_fingerprint)
        self.assertEqual('6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09', expected)

    def test_enhance_entry(self):
        result = enhance_entry(Entry('kate whalen', 'whalen pk', self.raw_fingerprint))

        self.assertEqual(result.name, 'Kate Whalen')
        self.assertEqual(result.fingerprint, '6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09')

    def test_sort_entries(self):
        result = sort_entries([
            Entry('Sam Cutler', 'cutler pk', 'cutler fp'),
            Entry('David Blishen', 'blishen pk', 'blishen fp'),
            Entry('Kate Whalen', 'whalen pk', 'whalen fp'),
            Entry('Michael Barton', 'barton pk', 'barton fp')
        ])
        expected = {
            'B': [
                Entry('David Blishen', 'blishen pk', 'blishen fp'),
                Entry('Michael Barton', 'barton pk', 'barton fp')
            ],
            'C': [
                Entry('Sam Cutler', 'cutler pk', 'cutler fp')
            ],
            'W': [
                Entry('Kate Whalen', 'whalen pk', 'whalen fp')
            ]
        }
        self.assertEqual(result, expected)

    def test_create_groups(self):
        result = list(create_groups({
            'B': [
                Entry('David Blishen', 'blishen pk', 'blishen fp'),
                Entry('Michael Barton', 'barton pk', 'barton fp')
            ],
            'C': [
                Entry('Sam Cutler', 'cutler pk', 'cutler fp')
            ],
            'W': [
                Entry('Kate Whalen', 'whalen pk', 'whalen fp')
            ]
        }))

        self.assertEqual(result[0], Group('B', [
                Entry('David Blishen', 'blishen pk', 'blishen fp'),
                Entry('Michael Barton', 'barton pk', 'barton fp')
            ]))

        self.assertEqual(result[1], Group('C', [
                Entry('Sam Cutler', 'cutler pk', 'cutler fp')
            ]))
        self.assertEqual(result[2], Group('W', [
                Entry('Kate Whalen', 'whalen pk', 'whalen fp')
            ]))


if __name__ == '__main__':
    unittest.main()

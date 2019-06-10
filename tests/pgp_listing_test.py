import unittest

from pgp_listing import *


class TestSortingEntries(unittest.TestCase):

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

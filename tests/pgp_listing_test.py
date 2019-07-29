import unittest

from pgp_listing import *


class TestSortingEntries(unittest.TestCase):
    def setUp(self) -> None:
        self.fingerprint = """
        pub   4096R/85FBBD09 2019-03-11\n
        Key fingerprint = 6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09\n
        uid       [ unknown] Kate Whalen <Kate.Whalen@theguardian.com>\n
        sub 2048R/8FA007E8 2019-03-11"""

        self.fingerprint_without_angle_brackets = """
        pub   4096R/85FBBD09 2019-03-11\n
        Key fingerprint = 6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09\n
        uid       [ unknown] Kate.Whalen@theguardian.com\n\n"""

    def test_parse_fingerprint(self):
        expected = parse_fingerprint(self.fingerprint)
        self.assertEqual('6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09', expected)

    def test_parse_email(self):
        expected = parse_email(self.fingerprint)
        self.assertEqual('Kate.Whalen@theguardian.com', expected)

    def test_parse_email_without_angle_brackets(self):
        expected = parse_email(self.fingerprint_without_angle_brackets)
        self.assertEqual('Kate.Whalen@theguardian.com', expected)

    def test_obscure_email(self):
        expected = obscure_email('Kate.Whalen@theguardian.com')
        self.assertEqual('Kate.Whalen<span class="leira">leira</span>[@]<span '
                         'class="leira">illusion</span>theguardian.com', expected)

    def test_enhance_entry(self):
        result = enhance_entry(Entry('Kate Whalen', 'whalen pk', self.fingerprint))

        self.assertEqual(result.other_names, 'Kate')
        self.assertEqual(result.last_name, 'Whalen')
        self.assertEqual(result.fingerprint, '6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09')

    def test_sort_entries(self):
        result = sort_entries([
            EnhancedEntry('Sam', 'Cutler', 'cutler pk', 'cutler fp', 'email@example'),
            EnhancedEntry('David', 'Blishen', 'blishen pk', 'blishen fp', 'email@example'),
            EnhancedEntry('Kate', 'Whalen', 'whalen pk', 'whalen fp', 'email@example'),
            EnhancedEntry('Michael', 'Barton', 'barton pk', 'barton fp', 'email@example')
        ])
        expected = {
            'B': [
                EnhancedEntry('David', 'Blishen', 'blishen pk', 'blishen fp', 'email@example'),
                EnhancedEntry('Michael', 'Barton', 'barton pk', 'barton fp', 'email@example')
            ],
            'C': [
                EnhancedEntry('Sam', 'Cutler', 'cutler pk', 'cutler fp', 'email@example'),
            ],
            'W': [
                EnhancedEntry('Kate', 'Whalen', 'whalen pk', 'whalen fp', 'email@example'),
            ]
        }
        self.assertEqual(result, expected)

    def test_create_ordered_groups(self):
        result = list(create_ordered_groups({
            'B': [
                EnhancedEntry('David', 'Blishen', 'blishen pk', 'blishen fp', 'email@example'),
                EnhancedEntry('Michael', 'Barton', 'barton pk', 'barton fp', 'email@example')
            ],
            'C': [
                EnhancedEntry('Sam', 'Cutler', 'cutler pk', 'cutler fp', 'email@example'),
            ],
            'W': [
                EnhancedEntry('Kate', 'Whalen', 'whalen pk', 'whalen fp', 'email@example'),
            ]
        }))

        self.assertEqual(result[0], Group('B', [
                EnhancedEntry('Michael', 'Barton', 'barton pk', 'barton fp', 'email@example'),
                EnhancedEntry('David', 'Blishen', 'blishen pk', 'blishen fp', 'email@example')
            ]))

        self.assertEqual(result[1], Group('C', [
                EnhancedEntry('Sam', 'Cutler', 'cutler pk', 'cutler fp', 'email@example'),
            ]))
        self.assertEqual(result[2], Group('W', [
                EnhancedEntry('Kate', 'Whalen', 'whalen pk', 'whalen fp', 'email@example'),
            ]))


if __name__ == '__main__':
    unittest.main()

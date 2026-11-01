"""
Tests for cpi.py
"""
# Built-ins
import datetime
import sqlite3
import unittest
# 3rd-party
# Internal
import cpi
from cpi import Observation
from temp_database import TempDatabaseMixin


class TestObservation(TempDatabaseMixin, unittest.TestCase):

    def test___init__(self):
        inputs = {'Date': datetime.date.today(), 'Item': 'Dozen eggs', 'Price': 3.99, 'Category': 'Food',
                  'State': 'Texas', 'City': 'Dallas'}
        obj = Observation(**inputs)
        self.assertEqual(obj.Date, datetime.date.today())
        self.assertEqual(obj.Category, 'Food')

    def test_write(self):
        # Quotes and SQL inside a value must be stored as plain text, never run as SQL
        item = "Eggs'); DROP TABLE Observation; --"
        rows_before = len(Observation.table_df().index)
        Observation(Date=datetime.date(2026, 10, 31), Item=item, Price=3.999, Category='Food', State='Texas',
                    City='Dallas').write()
        df = Observation.table_df()
        self.assertEqual(len(df.index), rows_before + 1)
        saved = df[df['Item'] == item].iloc[0]
        self.assertEqual(saved['Date'], '2026-10-31')  # YYYY-MM-DD, the same format as the sample data
        self.assertEqual(saved['Price'], 4.0)  # rounded to the cent

    def test_create_table(self):
        Observation.create_table()

    def test_get_test_data(self):
        df = Observation.get_test_data()
        self.assertGreater(len(df.index), 0)
        # Same formats as write(): YYYY-MM-DD dates and prices rounded to the cent
        self.assertTrue(df['Date'].str.fullmatch(r'\d{4}-\d{2}-\d{2}').all())
        self.assertTrue((df['Price'] == df['Price'].round(2)).all())

    # The delete_matching tests add rows for an item that isn't in the random sample data, so only those rows match
    test_item = 'Test item'

    def insert_test_rows(self, *rows):
        """Insert (Price, City, AddedOn) rows for test_item, in the order given."""
        with sqlite3.connect(cpi.db_file) as con:
            con.executemany('INSERT INTO Observation (Date, Item, Price, Category, State, City, AddedOn) '
                            "VALUES ('2026-10-31', ?, ?, 'Food', 'Texas', ?, ?)",
                            [(self.test_item, *row) for row in rows])

    def remaining_test_prices(self):
        with sqlite3.connect(cpi.db_file) as con:
            sql = 'SELECT Price FROM Observation WHERE Item = ? ORDER BY Price'
            return [price for (price,) in con.execute(sql, (self.test_item,))]

    def test_delete_matching_most_recent_first(self):
        # The first row added has the latest AddedOn, so AddedOn decides, not the order the rows were added
        self.insert_test_rows((1.11, 'Dallas', '2026-10-31 12:00:00'),
                              (2.22, 'Dallas', '2026-10-31 09:00:00'),
                              (3.33, 'Dallas', '2026-10-31 10:00:00'),
                              (4.44, 'Austin', '2026-10-31 13:00:00'))  # the newest, but a different city
        deleted = Observation().delete_matching(n_to_delete=2, order_to_delete_in={'AddedOn': False},
                                                Item=self.test_item, City='Dallas')
        self.assertEqual(deleted, 2)
        self.assertEqual(self.remaining_test_prices(), [2.22, 4.44])

    def test_delete_matching_oldest_first(self):
        self.insert_test_rows((1.11, 'Dallas', '2026-10-31 12:00:00'),
                              (2.22, 'Dallas', '2026-10-31 09:00:00'),
                              (3.33, 'Dallas', '2026-10-31 10:00:00'))
        Observation().delete_matching(n_to_delete=1, order_to_delete_in={'AddedOn': True}, Item=self.test_item)
        self.assertEqual(self.remaining_test_prices(), [1.11, 3.33])

    def test_delete_matching_breaks_ties_by_order_added(self):
        # Saved in the same second, so AddedOn ties and the order the rows were added decides
        same_second = '2026-10-31 09:00:00'
        self.insert_test_rows((1.11, 'Dallas', same_second), (2.22, 'Dallas', same_second),
                              (3.33, 'Dallas', same_second))
        Observation().delete_matching(order_to_delete_in={'AddedOn': False}, Item=self.test_item)  # the last added
        Observation().delete_matching(order_to_delete_in={'AddedOn': True}, Item=self.test_item)  # the first added
        self.assertEqual(self.remaining_test_prices(), [2.22])

    def test_delete_matching_without_order_deletes_in_order_added(self):
        same_second = '2026-10-31 09:00:00'
        self.insert_test_rows((1.11, 'Dallas', same_second), (2.22, 'Dallas', same_second),
                              (3.33, 'Dallas', same_second))
        Observation().delete_matching(n_to_delete=2, Item=self.test_item)
        self.assertEqual(self.remaining_test_prices(), [3.33])

    def test_delete_matching_deletes_at_most_the_matching_rows(self):
        self.insert_test_rows((1.11, 'Dallas', '2026-10-31 09:00:00'),
                              (2.22, 'Dallas', '2026-10-31 10:00:00'),
                              (3.33, 'Austin', '2026-10-31 11:00:00'))
        self.assertEqual(Observation().delete_matching(n_to_delete=10, Item=self.test_item, City='Dallas'), 2)
        self.assertEqual(Observation().delete_matching(n_to_delete=0, Item=self.test_item), 0)
        self.assertEqual(self.remaining_test_prices(), [3.33])

    def test_delete_matching_matches_dates_and_prices(self):
        self.insert_test_rows((1.11, 'Dallas', '2026-10-31 09:00:00'),
                              (2.22, 'Dallas', '2026-10-31 10:00:00'))
        deleted = Observation().delete_matching(Date=datetime.date(2026, 10, 31), Price=2.22, Item=self.test_item)
        self.assertEqual(deleted, 1)
        self.assertEqual(self.remaining_test_prices(), [1.11])

    def test_delete_matching_treats_values_as_data(self):
        rows_before = len(Observation.table_df().index)
        deleted = Observation().delete_matching(n_to_delete=1000, City="Dallas' OR '1'='1")
        self.assertEqual(deleted, 0)
        self.assertEqual(len(Observation.table_df().index), rows_before)

    def test_delete_matching_rejects_invalid_arguments(self):
        rows_before = len(Observation.table_df().index)
        invalid_calls = {
            'negative count (LIMIT -1 means no limit in SQLite)': dict(n_to_delete=-1, City='Dallas'),
            'count that is a bool': dict(n_to_delete=True, City='Dallas'),
            'count that is not a whole number': dict(n_to_delete=1.5, City='Dallas'),
            'no column to match on': dict(n_to_delete=1),
            'unknown column to match on': dict(Colour='red'),
            'SQL in a column name': {'City = City OR 1 = 1 --': 'x'},
            'unknown column to order by': dict(order_to_delete_in={'Nope': True}, City='Dallas'),
            'order direction that is not True or False': dict(order_to_delete_in={'AddedOn': 'desc'}, City='Dallas'),
        }
        for description, arguments in invalid_calls.items():
            with self.subTest(description):
                with self.assertRaises(ValueError):
                    Observation().delete_matching(**arguments)
        self.assertEqual(len(Observation.table_df().index), rows_before)  # nothing was deleted


if __name__ == '__main__':
    unittest.main()

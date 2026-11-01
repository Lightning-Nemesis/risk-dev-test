"""
Tests for cpi.py
"""
# Built-ins
import copy
import datetime
import json
import os
import sqlite3
import tempfile
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

    def test_init_ignores_unknown_fields_with_a_warning(self):
        with self.assertLogs('cpi', 'WARNING') as logs:
            obj = Observation(Prise=3.99)  # a typo of Price
        self.assertIn('Prise is not a valid attribute', logs.output[0])
        self.assertFalse(hasattr(obj, 'Prise'))
        self.assertIsNone(obj.Price)

    def test_added_on_comes_from_the_database(self):
        self.assertIsNone(Observation().AddedOn)  # not a fixed time from when the module was loaded
        Observation(Date=datetime.date(2026, 10, 31), Item=self.test_item, Price=1.0, Category='Food', State='Texas',
                    City='Dallas').write()
        df = Observation.table_df()
        added_on = datetime.datetime.fromisoformat(df.loc[df['Item'] == self.test_item, 'AddedOn'].iloc[0])
        utc_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.assertLess(abs(utc_now - added_on), datetime.timedelta(minutes=1))  # stamped in UTC as the row was saved

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


class TestLoadOptions(unittest.TestCase):

    # A small, valid options file: one category with one item, one state with one city
    valid = {'categories': [{'name': 'Dairy', 'items': [{'name': 'Whole Milk, Gallon', 'sample_base_price': 3.49}]}],
             'states': [{'name': 'Illinois', 'cities': ['Chicago'], 'sample_price_level': 1.2,
                         'sample_price_spread': 0.1}]}

    def tearDown(self):
        Observation.load_options(cpi.options_file)  # put the real options back

    def load(self, options):
        """Write options (a dict, or raw text) to a temporary file and load it."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'options.json')
            with open(path, 'w', encoding='utf-8') as file:
                file.write(options if isinstance(options, str) else json.dumps(options))
            Observation.load_options(path)

    def test_the_real_options_file_is_valid(self):
        Observation.load_options(cpi.options_file)
        self.assertTrue(Observation.available_categories())
        self.assertTrue(Observation.available_cities())

    def test_new_categories_items_states_and_cities_are_used_everywhere(self):
        self.load(self.valid)
        self.assertEqual(Observation.available_categories(), ['Dairy'])
        self.assertEqual(Observation.category_item_map, {'Dairy': ['Whole Milk, Gallon']})
        self.assertEqual(Observation.state_city_map, {'Illinois': ['Chicago']})
        # The sample prices let the sample-data generator make rows for the new item and state
        sample = Observation.get_test_data()
        self.assertEqual(set(sample['Item']), {'Whole Milk, Gallon'})
        self.assertEqual(set(sample['City']), {'Chicago'})

    def test_mistakes_are_reported_clearly(self):
        def changed(change):
            options = copy.deepcopy(self.valid)
            change(options)
            return options

        mistakes = {
            'not valid JSON': '{"categories": [',
            'needs a non-empty "items" list': changed(lambda o: o['categories'][0].update(items=[])),
            'needs a "sample_base_price" above 0': changed(
                lambda o: o['categories'][0]['items'][0].update(sample_base_price=0)),
            "repeats the item 'Whole Milk, Gallon'": changed(lambda o: o['categories'].append(
                {'name': 'Drinks', 'items': [{'name': 'Whole Milk, Gallon', 'sample_base_price': 3}]})),
            "repeats the city 'Chicago'": changed(lambda o: o['states'].append(
                {'name': 'Ohio', 'cities': ['Chicago'], 'sample_price_level': 1, 'sample_price_spread': 0.1})),
            'needs a "name"': changed(lambda o: o['states'][0].update(name=' Illinois ')),  # spaces at the ends
            'needs a "sample_price_spread" of 0 or more': changed(
                lambda o: o['states'][0].update(sample_price_spread=-0.1)),
            '"states" must be a non-empty list': changed(lambda o: o.pop('states')),
        }
        for message, options in mistakes.items():
            with self.subTest(message):
                with self.assertRaisesRegex(ValueError, message.replace('(', r'\(')):
                    self.load(options)


if __name__ == '__main__':
    unittest.main()

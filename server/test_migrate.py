"""
Tests for migrate.py
"""
# Built-ins
import sqlite3
import unittest
# 3rd-party
# Internal
import cpi
from migrate import migrate
from temp_database import TempDatabaseMixin


class TestMigrate(TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        # A throwaway database with fresh (already clean) sample data, plus one row in the old format
        super().setUp()
        with sqlite3.connect(cpi.db_file) as con:
            self.old_row_id = con.execute(
                'INSERT INTO Observation (Date, Item, Price, Category, State, City) VALUES (?, ?, ?, ?, ?, ?)',
                ('2022-06-20 00:00:00', 'Wool Socks, Pair', 20.587336131853935, 'Clothing', 'California', 'Los Angelos'),
            ).lastrowid

    def test_migrate_fixes_only_the_old_row(self):
        self.assertEqual(migrate(cpi.db_file), {'dates': 1, 'prices': 1, 'cities': 1})
        with sqlite3.connect(cpi.db_file) as con:
            row = con.execute('SELECT Date, Price, City FROM Observation WHERE rowid = ?', (self.old_row_id,)).fetchone()
        self.assertEqual(row, ('2022-06-20', 20.59, 'Los Angeles'))

    def test_migrate_twice_changes_nothing_the_second_time(self):
        migrate(cpi.db_file)
        self.assertEqual(migrate(cpi.db_file), {'dates': 0, 'prices': 0, 'cities': 0})


if __name__ == '__main__':
    unittest.main()

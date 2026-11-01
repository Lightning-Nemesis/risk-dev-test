"""
One-off clean-up of the rows already in the database, so they match what the app now writes.
Safe to run more than once: rows that are already clean are left alone.
Run it from this folder with: python migrate.py  (uses DATABASE_PATH from .env, like app.py)
"""
# Built-ins
import os
import sqlite3
# 3rd-party
from dotenv import load_dotenv
# Internal
import cpi


def migrate(db_path: str) -> dict:
    """Clean up the existing rows in one transaction, and return how many rows each fix changed."""
    with sqlite3.connect(db_path) as con:
        # '2022-06-20 00:00:00' -> '2022-06-20', the date format write() stores
        dates = con.execute('UPDATE Observation SET Date = date(Date) WHERE Date != date(Date)').rowcount
        # 20.587336131853935 -> 20.59: prices are money, so round to the cent like write() does
        prices = con.execute('UPDATE Observation SET Price = round(Price, 2) WHERE Price != round(Price, 2)').rowcount
        # The city was misspelled in Observation.state_city_map, and so in every row created from it
        cities = con.execute('UPDATE Observation SET City = ? WHERE City = ?',
                             ('Los Angeles', 'Los Angelos')).rowcount
    return {'dates': dates, 'prices': prices, 'cities': cities}


if __name__ == '__main__':
    load_dotenv()
    server_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(server_dir, os.getenv('DATABASE_PATH', cpi.db_file))
    print(f'Cleaning up {db_path}')
    for fix, count in migrate(db_path).items():
        print(f'  {fix}: {count} rows changed')

"""
Library for modeling prices for various objects
"""
# Built-ins
import datetime
import functools
import itertools
import logging
import random
import sqlite3
from typing import Optional
# 3rd-party
import pandas as pd
# Internal


logger = logging.getLogger(__name__)
db_file = 'test.db'


class Observation:

    Date: Optional[datetime.date] = None
    Item: Optional[str] = None
    Price: Optional[float] = None
    Category: Optional[str] = None
    State: Optional[str] = None
    City: Optional[str] = None
    AddedOn: datetime.datetime = datetime.datetime.now()

    # Columns of the Observation table. Only these names are ever put into SQL text built from caller input
    columns = ('Date', 'Item', 'Price', 'Category', 'State', 'City', 'AddedOn')

    category_item_map = {'Food': ['USDA Grade-A eggs, Dozen'],
                         'Fuel': ['Regular Gasoline, Gallon'],
                         'Clothing': ['Wool Socks, Pair']}
    state_city_map = {'California': ['Los Angeles', 'San Francisco'],
                      'New York': ['New York City'],
                      'Texas': ['Austin', 'Dallas']}
    item_base_price = {'USDA Grade-A eggs, Dozen': 2.99,
                       'Regular Gasoline, Gallon': 4.65,
                       'Wool Socks, Pair': 21.95}
    state_price_mu_std = {'California': (1.5, 0.15),
                          'New York': (1.75, 0.25),
                          'Texas': (1, 0.10)}

    @classmethod
    @functools.lru_cache(maxsize=None)
    def available_items(cls):
        return list(itertools.chain.from_iterable(cls.category_item_map.values()))

    @classmethod
    @functools.lru_cache(maxsize=None)
    def available_categories(cls):
        return list(cls.category_item_map.keys())

    @classmethod
    @functools.lru_cache(maxsize=None)
    def available_states(cls):
        return list(cls.state_city_map.keys())

    @classmethod
    @functools.lru_cache(maxsize=None)
    def available_cities(cls):
        return list(itertools.chain.from_iterable(cls.state_city_map.values()))

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            try:
                setattr(self, k, v)
            except AttributeError:
                logger.warning(f'{k} is not a valid attribute of Observation. Ignoring...')

    def write(self):
        """Insert this observation as a new row. Date must be a datetime.date; Price is rounded to the cent."""
        # The ? placeholders send the values to SQLite separately from the SQL text, so no value can change the query
        sql = 'INSERT INTO Observation (Date, Item, Price, Category, State, City) VALUES (?, ?, ?, ?, ?, ?)'
        values = (self.Date.strftime('%Y-%m-%d'), self.Item, round(self.Price, 2), self.Category, self.State,
                  self.City)
        with sqlite3.connect(db_file) as con:
            con.execute(sql, values)

    @classmethod
    def create_table(cls):
        sql = '''
        create table Observation (
            Date date not null,
            Item text not null,
            Price numeric not null,
            Category text not null,
            State text not null,
            City text not null,
            AddedOn datetime default current_timestamp
        );
        '''
        with sqlite3.connect(db_file) as con:
            con.execute('drop table if exists Observation')
            con.execute(sql)
            # Load test data
            df = cls.get_test_data()
            df.to_sql('Observation', con=con, if_exists='append', index=False)

    @classmethod
    def get_test_data(cls) -> pd.DataFrame:
        dt_range = pd.date_range(end=datetime.date.today(), periods=10, freq='D', inclusive='both')
        dt_range = dt_range.strftime('%Y-%m-%d')  # YYYY-MM-DD strings, the same date format write() stores
        combos = [{'Date': dt, 'Category': cat, 'Item': item, 'State': state, 'City': city}
                  for cat, items in cls.category_item_map.items()
                  for item in items
                  for state, cities in cls.state_city_map.items()
                  for city in cities
                  for dt in dt_range
                  for _ in range(5)]  # Create 5 prices per combo
        df = pd.DataFrame(combos)
        # Set all base prices to the average price for the item
        df['Price'] = df.apply(lambda s: cls.item_base_price[s['Item']], axis=1)
        # Multiply the base price by the state scaling factor
        df['Price'] = df.apply(lambda s: s['Price'] * cls.state_price_mu_std[s['State']][0], axis=1)
        # Generate a gaussian price based on the state standard deviation
        df['Price'] = df.apply(lambda s: random.gauss(s['Price'], s['Price'] * cls.state_price_mu_std[s['State']][1]),
                               axis=1)
        # Prices are money, so round to the cent, the same as write()
        df['Price'] = df['Price'].round(2)
        return df

    @staticmethod
    def table_df() -> pd.DataFrame:
        with sqlite3.connect(db_file) as con:
            # Newest first, so a new row is on top. rowid is SQLite's own row number: a unique id for each row
            sql = 'select rowid as id, * from Observation order by AddedOn desc, rowid desc'
            return pd.read_sql(sql, con)

    @staticmethod
    def price_counts() -> pd.DataFrame:
        """How many observations share each item, date and price, i.e. each point on the prices-over-time graph."""
        with sqlite3.connect(db_file) as con:
            sql = ('select Item, Date, Price, count(*) as Count from Observation '
                   'group by Item, Date, Price order by Date, Price')
            return pd.read_sql(sql, con)

    @staticmethod
    def average_prices(date: str) -> pd.DataFrame:
        """The average price of each item in each city on one date (YYYY-MM-DD), and how many observations each
        average is based on."""
        with sqlite3.connect(db_file) as con:
            sql = ('select Item, City, avg(Price) as AveragePrice, count(*) as Count from Observation '
                   'where Date = ? group by Item, City')
            return pd.read_sql(sql, con, params=(date,))

    @staticmethod
    def latest_date() -> Optional[str]:
        """The most recent observation date (YYYY-MM-DD), or None when there are no observations."""
        with sqlite3.connect(db_file) as con:
            return con.execute('select max(Date) from Observation').fetchone()[0]

    def delete_matching(self, n_to_delete: int = 1, order_to_delete_in: Optional[dict] = None, **kwargs):
        """Delete up to n_to_delete rows matching every key-value pair in kwargs, and return how many were deleted.

        Ex. kwargs = {'State': 'Texas', 'City': 'Dallas'} matches all rows where State = 'Texas' AND City = 'Dallas'.
        order_to_delete_in is {<column to order matching rows by>: <True for ascending, False for descending>}, e.g.
        {'AddedOn': False} deletes the most recently added rows first. Rows that tie are taken in the order they were
        added: newest first when ordering by AddedOn descending, otherwise oldest first. Without order_to_delete_in,
        rows are deleted in the order they were added. A Date can be a datetime.date or 'YYYY-MM-DD' text.

        Raises ValueError for an unknown column, no column to match on (so the whole table is never deleted by
        accident), an order direction that isn't True or False, or an n_to_delete that isn't a whole number >= 0.
        """
        order_to_delete_in = order_to_delete_in or {}
        if isinstance(n_to_delete, bool) or not isinstance(n_to_delete, int) or n_to_delete < 0:
            # A negative LIMIT means "no limit" in SQLite, so -1 would delete every matching row
            raise ValueError('n_to_delete must be a whole number of 0 or more')
        if not kwargs:
            raise ValueError('Give at least one column to match on, so the whole table is never deleted by accident')
        # Column names can't be ? placeholders, so only names from Observation.columns ever reach the SQL text
        for column in [*kwargs, *order_to_delete_in]:
            if column not in self.columns:
                raise ValueError(f'Unknown column {column!r}; expected one of: {", ".join(self.columns)}')
        if not all(isinstance(ascending, bool) for ascending in order_to_delete_in.values()):
            raise ValueError('order_to_delete_in values must be True (ascending) or False (descending)')

        if isinstance(kwargs.get('Date'), datetime.date):
            kwargs['Date'] = kwargs['Date'].strftime('%Y-%m-%d')  # the format write() stores
        where = ' AND '.join(f'{column} = ?' for column in kwargs)
        order_by = [f'{column} {"ASC" if ascending else "DESC"}' for column, ascending in order_to_delete_in.items()]
        # AddedOn only has one-second resolution, so rows can tie. rowid is the exact order rows were added: it breaks
        # ties newest first when ordering by AddedOn descending, otherwise oldest first
        order_by.append('rowid ASC' if order_to_delete_in.get('AddedOn', True) else 'rowid DESC')
        # SQLite can't portably DELETE ... LIMIT, so pick the rowids to delete in a subquery
        sql = (f'DELETE FROM Observation WHERE rowid IN '
               f'(SELECT rowid FROM Observation WHERE {where} ORDER BY {", ".join(order_by)} LIMIT ?)')
        with sqlite3.connect(db_file) as con:
            return con.execute(sql, [*kwargs.values(), n_to_delete]).rowcount


if __name__ == '__main__':
    pass

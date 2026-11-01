"""
Library for modeling prices for various objects
"""
# Built-ins
import datetime
import itertools
import json
import logging
import os
import random
import sqlite3
from typing import Optional
# 3rd-party
import pandas as pd
# Internal


logger = logging.getLogger(__name__)
db_file = 'test.db'
# The editable list of categories with their items, and states with their cities (see "Editing the options" in
# server/README.md). It's read when this module is imported; Observation.load_options() can read another file
options_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'options.json')


class Observation:

    Date: Optional[datetime.date] = None
    Item: Optional[str] = None
    Price: Optional[float] = None
    Category: Optional[str] = None
    State: Optional[str] = None
    City: Optional[str] = None
    AddedOn: Optional[datetime.datetime] = None  # the database sets it (current_timestamp, UTC) when a row is written

    # Columns of the Observation table. Only these names are ever put into SQL text built from caller input
    columns = ('Date', 'Item', 'Price', 'Category', 'State', 'City', 'AddedOn')

    # Filled from the options file by load_options(): the items in each category and the cities in each state, plus
    # the prices used only to generate sample data (an item's base price; a state's price level and spread)
    category_item_map = {}
    state_city_map = {}
    item_base_price = {}
    state_price_mu_std = {}

    @classmethod
    def load_options(cls, path: str):
        """Read the options file (JSON) and replace the categories, items, states and cities with its contents.

        Raises ValueError naming the first problem, such as a missing price or a city listed twice, so a bad edit stops
        the server at startup with a clear message instead of failing later.
        """
        try:
            with open(path, encoding='utf-8') as file:
                options = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f'{path} is not valid JSON: {error}') from error

        def check(condition, where, problem):
            if not condition:
                raise ValueError(f'{path}: {where} {problem}')

        def is_name(value):  # text that isn't blank and has no spaces at either end (the API trims what users send)
            return isinstance(value, str) and value != '' and value == value.strip()

        def is_number(value):  # True and False count as numbers in Python, so rule them out
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        check(isinstance(options, dict), 'the file', 'must hold one JSON object with "categories" and "states"')
        categories, states = options.get('categories'), options.get('states')
        check(isinstance(categories, list) and categories, '"categories"', 'must be a non-empty list')
        check(isinstance(states, list) and states, '"states"', 'must be a non-empty list')

        category_items, base_prices = {}, {}
        for i, category in enumerate(categories):
            where = f'categories[{i}]'
            check(isinstance(category, dict) and is_name(category.get('name')), where, 'needs a "name"')
            check(category['name'] not in category_items, where, f'repeats the category {category["name"]!r}')
            items = category.get('items')
            check(isinstance(items, list) and items, where, 'needs a non-empty "items" list')
            category_items[category['name']] = []
            for j, item in enumerate(items):
                where = f'categories[{i}].items[{j}]'
                check(isinstance(item, dict) and is_name(item.get('name')), where, 'needs a "name"')
                check(item['name'] not in base_prices, where, f'repeats the item {item["name"]!r}')
                price = item.get('sample_base_price')
                check(is_number(price) and price > 0, where, 'needs a "sample_base_price" above 0')
                category_items[category['name']].append(item['name'])
                base_prices[item['name']] = price

        state_cities, price_levels = {}, {}
        for i, state in enumerate(states):
            where = f'states[{i}]'
            check(isinstance(state, dict) and is_name(state.get('name')), where, 'needs a "name"')
            check(state['name'] not in state_cities, where, f'repeats the state {state["name"]!r}')
            cities = state.get('cities')
            check(isinstance(cities, list) and cities and all(is_name(city) for city in cities), where,
                  'needs a non-empty "cities" list of names')
            for city in cities:
                # The graphs group by city name, so the same name in two states would merge their prices
                listed = any(city in names for names in state_cities.values()) or cities.count(city) > 1
                check(not listed, where, f'repeats the city {city!r}: each city name can appear only once')
            level, spread = state.get('sample_price_level'), state.get('sample_price_spread')
            check(is_number(level) and level > 0, where, 'needs a "sample_price_level" above 0')
            check(is_number(spread) and spread >= 0, where, 'needs a "sample_price_spread" of 0 or more')
            state_cities[state['name']] = list(cities)
            price_levels[state['name']] = (level, spread)

        cls.category_item_map, cls.item_base_price = category_items, base_prices
        cls.state_city_map, cls.state_price_mu_std = state_cities, price_levels

    # Not cached, because load_options() can replace the lists they come from
    @classmethod
    def available_items(cls):
        return list(itertools.chain.from_iterable(cls.category_item_map.values()))

    @classmethod
    def available_categories(cls):
        return list(cls.category_item_map.keys())

    @classmethod
    def available_states(cls):
        return list(cls.state_city_map.keys())

    @classmethod
    def available_cities(cls):
        return list(itertools.chain.from_iterable(cls.state_city_map.values()))

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            # setattr accepts any name, so check it against the table's columns: a typo such as Prise=3.99 is reported
            # and ignored, instead of being stored silently while Price stays empty
            if k in self.columns:
                setattr(self, k, v)
            else:
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
    def table_df(limit: Optional[int] = None) -> pd.DataFrame:
        """All observations, or only the newest `limit` of them."""
        with sqlite3.connect(db_file) as con:
            # Newest first, so a new row is on top. rowid is SQLite's own row number: a unique id for each row
            sql = 'select rowid as id, * from Observation order by AddedOn desc, rowid desc'
            params = []
            if limit is not None:
                sql += ' limit ?'
                params.append(limit)
            return pd.read_sql(sql, con, params=params)

    @staticmethod
    def row_count() -> int:
        """How many observations there are."""
        with sqlite3.connect(db_file) as con:
            return con.execute('select count(*) from Observation').fetchone()[0]

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


# Read the options as soon as this module is imported, so everything that uses Observation (the API, migrate.py and
# the tests) has them
Observation.load_options(options_file)


if __name__ == '__main__':
    pass

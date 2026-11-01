"""
Tests for app.py
"""
# Built-ins
import datetime
import re
import unittest
from unittest import mock
# 3rd-party
# Internal
from app import app
from cpi import Observation
from temp_database import TempDatabaseMixin


class TestErrorResponses(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_unknown_url_returns_json_404(self):
        response = self.client.get('/api/does-not-exist')
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.get_json())

    def test_wrong_method_returns_json_405_with_allow_header(self):
        response = self.client.put('/api/options')
        self.assertEqual(response.status_code, 405)
        self.assertIn('error', response.get_json())
        self.assertIn('GET', response.headers['Allow'])

    def test_unexpected_error_returns_json_500_without_details(self):
        # Make the database call fail, to simulate a bug in the server
        with mock.patch.object(Observation, 'table_df', side_effect=RuntimeError('secret detail')):
            with self.assertLogs(app.logger, 'ERROR'):
                response = self.client.get('/api/observations')
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.get_json())
        self.assertNotIn('secret detail', response.get_data(as_text=True))


class TestListObservations(TempDatabaseMixin, unittest.TestCase):

    def test_rows_have_an_id_and_a_utc_added_on(self):
        rows = app.test_client().get('/api/observations').get_json()
        self.assertEqual(len({row['id'] for row in rows}), len(rows))  # a unique id per row, for the table
        # ISO 8601 with Z (UTC), so browsers convert it to the viewer's own time zone
        self.assertTrue(all(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', row['AddedOn']) for row in rows))


class TestSaveObservation(TempDatabaseMixin, unittest.TestCase):

    # A far-past date, so the random sample data (always the last 10 days) never shares it
    valid = {'Date': '2020-01-15', 'Category': 'Fuel', 'Item': 'Regular Gasoline, Gallon', 'Price': '4.659',
             'State': 'Texas', 'City': 'Austin'}

    def setUp(self):
        super().setUp()
        self.client = app.test_client()

    def save(self, **changes):
        return self.client.post('/api/observations', json={**self.valid, **changes})

    def rows_on_test_date(self):
        rows = self.client.get('/api/observations').get_json()
        return [row for row in rows if row['Date'] == self.valid['Date']]

    def test_save_valid_observation(self):
        response = self.save()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['Price'], 4.66)  # rounded to the cent
        newest = self.client.get('/api/observations').get_json()[0]  # the newest row comes first
        self.assertEqual((newest['Date'], newest['Item'], newest['Price'], newest['City']),
                         ('2020-01-15', 'Regular Gasoline, Gallon', 4.66, 'Austin'))

    def test_save_accepts_tomorrow(self):
        # The server runs on UTC, where it's already tomorrow for some users
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(self.save(Date=tomorrow).status_code, 201)

    def test_save_rejects_invalid_values(self):
        day_after_tomorrow = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        invalid_values = [
            ('Price', ''), ('Price', 'abc'), ('Price', 'nan'), ('Price', 'inf'), ('Price', '-1'), ('Price', '0'),
            ('Price', '0.004'),  # rounds to 0.00
            ('Date', ''), ('Date', '2026-02-30'), ('Date', '20261030'), ('Date', '10/30/2026'),
            ('Date', day_after_tomorrow),
            ('Category', 'Toys'), ('Item', 'Wool Socks, Pair'),  # socks aren't Fuel
            ('State', 'Ohio'), ('City', 'San Francisco'),  # San Francisco isn't in Texas
        ]
        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                response = self.save(**{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.get_json()['fields'])
        self.assertEqual(self.rows_on_test_date(), [])  # nothing was saved

    def test_save_reports_every_invalid_field_at_once(self):
        values = {**self.valid, 'Price': 'abc', 'City': 'San Francisco'}
        del values['Date']
        response = self.client.post('/api/observations', json=values)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.get_json()['fields']), {'Date', 'Price', 'City'})

    def test_save_enforces_max_price(self):
        with mock.patch('app.MAX_PRICE', 100.0):
            self.assertEqual(self.save(Price='100').status_code, 201)
            response = self.save(Price='100.01')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['fields']['Price'], 'Price must be at most 100.00')

    def test_save_requires_a_json_object(self):
        response = self.client.post('/api/observations', data='not json', content_type='text/plain')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())


class TestPricesOverTime(TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.client = app.test_client()

    def test_counts_observations_with_the_same_item_date_and_price(self):
        eggs = {'Date': '2020-01-15', 'Category': 'Food', 'Item': 'USDA Grade-A eggs, Dozen', 'State': 'Texas'}
        # Three eggs observations at 2.99 (two in Dallas, one in Austin: city doesn't matter) and one at 3.49
        for city, price in [('Dallas', '2.99'), ('Dallas', '2.99'), ('Austin', '2.99'), ('Dallas', '3.49')]:
            self.client.post('/api/observations', json={**eggs, 'City': city, 'Price': price})
        series = self.client.get('/api/charts/prices-over-time').get_json()

        self.assertEqual([s['item'] for s in series], Observation.available_items())  # fixed order keeps colors
        eggs_series = series[0]
        points = zip(eggs_series['dates'], eggs_series['prices'], eggs_series['counts'])
        counts_on_test_date = {price: count for date, price, count in points if date == '2020-01-15'}
        self.assertEqual(counts_on_test_date, {2.99: 3, 3.49: 1})

    def test_every_observation_is_counted_once(self):
        series = self.client.get('/api/charts/prices-over-time').get_json()
        observations = self.client.get('/api/observations').get_json()
        self.assertEqual(sum(sum(s['counts']) for s in series), len(observations))


class TestAveragePriceByCity(TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.client = app.test_client()
        # On a far-past date the sample data never uses: eggs twice in Dallas and once in Austin, socks once in Dallas
        for item, category, city, price in [('USDA Grade-A eggs, Dozen', 'Food', 'Dallas', '2.00'),
                                            ('USDA Grade-A eggs, Dozen', 'Food', 'Dallas', '4.00'),
                                            ('USDA Grade-A eggs, Dozen', 'Food', 'Austin', '5.00'),
                                            ('Wool Socks, Pair', 'Clothing', 'Dallas', '20.00')]:
            self.client.post('/api/observations', json={'Date': '2020-01-15', 'Category': category, 'Item': item,
                                                         'Price': price, 'State': 'Texas', 'City': city})

    def get(self, date):
        return self.client.get('/api/charts/average-price-by-city', query_string={'date': date})

    def test_averages_each_item_in_each_city_on_the_date(self):
        data = self.get('2020-01-15').get_json()
        self.assertEqual(data['items'], Observation.available_items())  # bar groups, always in this order
        by_city = {s['city']: s for s in data['series']}
        self.assertEqual(list(by_city), Observation.available_cities())  # bar colors, always in this order
        # Items in order: eggs, gasoline, socks. None means no bar: no observations of that item in that city
        self.assertEqual(by_city['Dallas']['averages'], [3.0, None, 20.0])
        self.assertEqual(by_city['Dallas']['counts'], [2, 0, 1])
        self.assertEqual(by_city['Austin']['averages'], [5.0, None, None])
        self.assertEqual(by_city['Los Angeles']['counts'], [0, 0, 0])

    def test_date_without_observations_points_to_the_latest_date(self):
        data = self.get('2019-01-01').get_json()
        self.assertTrue(all(count == 0 for s in data['series'] for count in s['counts']))
        latest = max(row['Date'] for row in self.client.get('/api/observations').get_json())
        self.assertEqual(data['latest_date'], latest)

    def test_rejects_an_invalid_date(self):
        for date in ['', '2020-02-30', '01/15/2020']:
            with self.subTest(date=date):
                response = self.get(date)
                self.assertEqual(response.status_code, 400)
                self.assertIn('date', response.get_json()['fields'])


class TestDeleteObservations(TempDatabaseMixin, unittest.TestCase):

    # The form's values for three observations saved on a far-past date, which the sample data never shares
    match = {'Date': '2020-01-15', 'Category': 'Food', 'Item': 'USDA Grade-A eggs, Dozen', 'State': 'Texas',
             'City': 'Dallas'}

    def setUp(self):
        super().setUp()
        self.client = app.test_client()
        for price in ('1.11', '2.22', '3.33'):  # saved in this order
            self.client.post('/api/observations', json={**self.match, 'Price': price})

    def delete(self, **params):
        query = {**self.match, 'count': '1', 'mostRecentFirst': 'true', **params}
        return self.client.delete('/api/observations', query_string=query)

    def remaining_prices(self):
        rows = self.client.get('/api/observations').get_json()
        return sorted(row['Price'] for row in rows if row['Date'] == self.match['Date'])

    def test_delete_most_recent_first(self):
        response = self.delete(count='2')
        self.assertEqual(response.get_json(), {'deleted': 2, 'requested': 2})
        self.assertEqual(self.remaining_prices(), [1.11])

    def test_delete_oldest_first(self):
        self.delete(count='2', mostRecentFirst='false')
        self.assertEqual(self.remaining_prices(), [3.33])

    def test_delete_matches_price_only_when_given(self):
        self.assertEqual(self.delete(count='5', Price='2.22').get_json()['deleted'], 1)
        self.assertEqual(self.remaining_prices(), [1.11, 3.33])

    def test_delete_more_than_match_touches_no_other_rows(self):
        total_before = len(self.client.get('/api/observations').get_json())
        self.assertEqual(self.delete(count='10').get_json(), {'deleted': 3, 'requested': 10})
        self.assertEqual(len(self.client.get('/api/observations').get_json()), total_before - 3)

    def test_delete_rejects_invalid_values(self):
        invalid_values = [('count', '0'), ('count', '-1'), ('count', '1.5'), ('count', 'abc'), ('count', ''),
                          ('mostRecentFirst', 'yes'), ('Date', ''), ('City', 'San Francisco'), ('Price', 'abc')]
        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                response = self.delete(**{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.get_json()['fields'])
        self.assertEqual(self.remaining_prices(), [1.11, 2.22, 3.33])  # nothing was deleted


if __name__ == '__main__':
    unittest.main()

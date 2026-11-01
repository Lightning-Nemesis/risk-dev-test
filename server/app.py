"""
REST API for saving price observations and reading them back.
Start it with: python app.py  (settings come from .env)
"""
# Built-ins
import datetime
import json
import logging
import math
import os
# 3rd-party
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request
from werkzeug.exceptions import HTTPException
# Internal
import cpi
from cpi import Observation


# Load server/.env. Variables already set in the environment (e.g. by Docker) take priority.
load_dotenv()

# Point cpi.py at the database named in .env, relative to this folder so it works from any working directory
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
cpi.db_file = os.path.join(SERVER_DIR, os.getenv('DATABASE_PATH', cpi.db_file))

# Highest price the API accepts, in dollars (task 6)
MAX_PRICE = float(os.getenv('MAX_PRICE', '10000'))
# How far past the server's today a date may be. The server runs on UTC, where it's already tomorrow for some users
FUTURE_DATE_SLACK = datetime.timedelta(days=1)

app = Flask(__name__)
# Log INFO messages (such as the record of each delete) even when FLASK_DEBUG is off
app.logger.setLevel(logging.INFO)


class InvalidInput(Exception):
    """Request values that failed validation. field_errors maps each invalid field to a message for the user."""

    def __init__(self, field_errors):
        super().__init__(' '.join(f'{message}.' for message in field_errors.values()))
        self.field_errors = field_errors


@app.errorhandler(InvalidInput)
def handle_invalid_input(error):
    """Report every invalid field at once: "error" is one summary sentence, "fields" has each field's message."""
    return jsonify(error=str(error), fields=error.field_errors), 400


@app.errorhandler(Exception)
def handle_error(error):
    """Return every error as JSON {"error": "<message>"}, which client/src/api.js shows to the user.

    One handler for all exceptions, because with FLASK_DEBUG=1 Flask skips a plain 500 handler and returns its
    HTML debugger page instead.
    """
    if isinstance(error, HTTPException):
        # Expected errors such as 404 Not Found or 405 Method Not Allowed: keep the status code and headers
        # (e.g. Allow on a 405), and swap the HTML body for JSON
        response = error.get_response()
        response.data = json.dumps({'error': error.description})
        response.content_type = 'application/json'
        return response
    # Anything else is a bug: log the full traceback for us, and don't leak internal details to the browser
    app.logger.exception('Unhandled error')
    return jsonify(error='Something went wrong on the server. Please try again.'), 500


# Validation of the values the client sends. Each function adds a message to `errors` for every invalid field,
# so the endpoints can report all the problems at once

def clean_text(value):
    """A request value as text without surrounding spaces, or '' when it's missing."""
    return '' if value is None else str(value).strip()


def clean_observation(values, errors, price_required=True):
    """Check the observation fields sent by the client, and return them cleaned up.

    Date becomes a datetime.date and Price becomes dollars rounded to the cent (None when it's blank and not
    required).
    """
    fields = {name: clean_text(values.get(name)) for name in ('Date', 'Category', 'Item', 'Price', 'State', 'City')}
    for name in ('Date', 'Category', 'Item', 'State', 'City'):
        if not fields[name]:
            errors[name] = f'{name} is required'

    date = None
    if 'Date' not in errors:
        date = clean_date(fields['Date'], errors)
        if date and date > datetime.date.today() + FUTURE_DATE_SLACK:
            errors['Date'] = "Date can't be in the future"

    check_linked_choice(fields, errors, 'Category', 'Item', Observation.category_item_map)
    check_linked_choice(fields, errors, 'State', 'City', Observation.state_city_map)

    price = None
    if fields['Price']:
        price = clean_price(fields['Price'], errors)
    elif price_required:
        errors['Price'] = 'Price is required'

    return {'Date': date, 'Category': fields['Category'], 'Item': fields['Item'], 'Price': price,
            'State': fields['State'], 'City': fields['City']}


def clean_date(text, errors, field='Date'):
    """Parse a date written as YYYY-MM-DD."""
    try:
        return datetime.datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        errors[field] = 'Enter a real date as YYYY-MM-DD'
        return None


def check_linked_choice(fields, errors, parent, child, options):
    """Check a pair of linked drop-downs, such as State and City: the parent must be one of the options' keys, and
    the child one of that parent's values."""
    if parent not in errors and fields[parent] not in options:
        errors[parent] = f'Choose a {parent.lower()} from the list'
    elif child not in errors and fields[parent] in options and fields[child] not in options[fields[parent]]:
        errors[child] = f"{fields[child]} isn't in {fields[parent]}"


def clean_price(text, errors):
    """Parse the price as dollars rounded to the cent."""
    try:
        price = float(text)
    except ValueError:
        price = math.nan
    if not math.isfinite(price):  # float() also accepts 'nan' and 'inf', which aren't prices
        errors['Price'] = 'Enter the price as a number, e.g. 3.99'
        return None
    price = round(price, 2)
    if price <= 0:
        errors['Price'] = 'Price must be more than 0'
    elif price > MAX_PRICE:
        errors['Price'] = f'Price must be at most {MAX_PRICE:,.2f}'
    return price


def clean_whole_number(value, errors, field, what):
    """Parse a whole number of 1 or more, such as how many observations to delete."""
    try:
        number = int(clean_text(value))
    except ValueError:
        number = 0
    if number < 1:
        errors[field] = f'Enter {what} as a whole number of 1 or more'
    return number


@app.get('/api/options')
def get_options():
    """Values for the client's drop-downs."""
    return jsonify(categories=Observation.available_categories(),
                   items=Observation.available_items(),
                   states=Observation.available_states(),
                   cities=Observation.available_cities(),
                   # Which items belong to each category and which cities to each state, for the linked drop-downs
                   category_items=Observation.category_item_map,
                   state_cities=Observation.state_city_map)


@app.get('/api/observations')
def get_observations():
    """Observations, newest first, each with a unique id, plus the total number of observations.

    ?limit=N returns only the newest N rows, so the table's response stays small however many observations there are.
    Without it, every row is returned.
    """
    errors = {}
    limit = None
    if 'limit' in request.args:
        limit = clean_whole_number(request.args.get('limit'), errors, 'limit', 'how many rows to return')
    if errors:
        raise InvalidInput(errors)
    rows = Observation.table_df(limit)
    # SQLite's current_timestamp is UTC, written 'YYYY-MM-DD HH:MM:SS'. Send it as ISO 8601 with a Z, so the browser
    # knows it's UTC and shows it in the viewer's own time zone
    rows['AddedOn'] = rows['AddedOn'].str.replace(' ', 'T') + 'Z'
    return jsonify(total=Observation.row_count(), observations=rows.to_dict('records'))


@app.get('/api/charts/prices-over-time')
def get_prices_over_time():
    """Data for the 'Item Prices Over Time' graph (task 4). One series per item: a point for each date and price,
    with how many observations share it, so the client can size each point by its count."""
    counts = Observation.price_counts()
    series = []
    for item in Observation.available_items():  # always the same order, so each item keeps its color
        rows = counts[counts['Item'] == item]
        series.append({'item': item, 'dates': rows['Date'].tolist(), 'prices': rows['Price'].tolist(),
                       'counts': rows['Count'].tolist()})
    return jsonify(series)


@app.get('/api/charts/average-price-by-city')
def get_average_price_by_city():
    """Data for the 'Average Item Price by City' graph (task 5): the average price of each item in each city on the
    date given as ?date=YYYY-MM-DD.

    One series per city (a bar color), with an average and an observation count for each item (a bar group). The
    average is null where a city has no observations of that item. latest_date is the most recent date with any
    observations, so the client can offer it when the chosen date has none.
    """
    errors = {}
    date = clean_date(clean_text(request.args.get('date')), errors, field='date')
    if errors:
        raise InvalidInput(errors)

    items = Observation.available_items()  # always the same order, so the bar groups don't move
    averages = Observation.average_prices(date.isoformat()).to_dict('records')
    by_item_and_city = {(row['Item'], row['City']): row for row in averages}
    series = []
    for city in Observation.available_cities():  # always the same order, so each city keeps its color
        rows = [by_item_and_city.get((item, city)) for item in items]
        series.append({'city': city,
                       'averages': [row['AveragePrice'] if row else None for row in rows],
                       'counts': [row['Count'] if row else 0 for row in rows]})
    return jsonify(date=date.isoformat(), items=items, series=series, latest_date=Observation.latest_date())


@app.post('/api/observations')
def create_observation():
    """Save one observation from the form as a new row (task 1), and return it as saved (Price rounded to the cent)."""
    values = request.get_json(silent=True)
    if not isinstance(values, dict):
        abort(400, 'Send the observation as a JSON object')
    errors = {}
    observation = clean_observation(values, errors)
    if errors:
        raise InvalidInput(errors)
    Observation(**observation).write()
    return jsonify({**observation, 'Date': observation['Date'].isoformat()}), 201


@app.delete('/api/observations')
def delete_observations():
    """Delete up to `count` observations matching the form (task 3), and return how many were deleted.

    Query parameters: Date, Category, Item, State and City to match on, Price to match only when given, count, and
    mostRecentFirst ('true' deletes the most recently added first, 'false' the oldest first).
    """
    errors = {}
    match = clean_observation(request.args, errors, price_required=False)
    count = clean_whole_number(request.args.get('count'), errors, 'count', 'how many observations to delete')
    most_recent_first = request.args.get('mostRecentFirst')
    if most_recent_first not in ('true', 'false'):
        errors['mostRecentFirst'] = 'mostRecentFirst must be true or false'
    if errors:
        raise InvalidInput(errors)

    if match['Price'] is None:
        del match['Price']  # no price entered, so match any price
    # In order_to_delete_in, True sorts ascending (oldest first) and False descending (most recent first)
    deleted = Observation().delete_matching(n_to_delete=count,
                                            order_to_delete_in={'AddedOn': most_recent_first == 'false'},
                                            **match)
    # Deleting can't be undone, so every delete is recorded in the server log
    criteria = ', '.join(f'{column}={value}' for column, value in match.items())
    order = 'most recent' if most_recent_first == 'true' else 'oldest'
    app.logger.info('Deleted %d of %d requested observations matching %s, %s first', deleted, count, criteria, order)
    return jsonify(deleted=deleted, requested=count)


if __name__ == '__main__':
    app.run(host=os.getenv('FLASK_RUN_HOST', '127.0.0.1'),
            port=int(os.getenv('FLASK_RUN_PORT', '5001')),
            debug=os.getenv('FLASK_DEBUG') == '1',
            # With FLASK_DEBUG=1 the server restarts on code changes; this makes it restart on options edits too
            extra_files=[cpi.options_file])

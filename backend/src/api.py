'''
App module
'''

import json
from flask import abort, Flask, jsonify, request
from flask_cors import CORS
from schema import And, Optional, Schema, SchemaError, Use
from sqlalchemy import func
from .auth.auth import AuthError, requires_auth
from .database.models import db_drop_and_create_all, setup_db, Drink

app = Flask(__name__)
setup_db(app)
CORS(app)
db_drop_and_create_all()


# HELPERS


def is_valid_schema(data):
    '''Check data schema is valid'''
    schema = Schema({
        Optional('id'): And(Use(int)),
        'recipe': [
            {
                'name': And(Use(str), len),
                'color': And(Use(str), len),
                'parts': And(Use(int), lambda n: 1 <= n <= 9)
            }
        ],
        'title': And(Use(str), len)
    })
    try:
        schema.validate(data)
        return True
    except SchemaError:
        return False


# ROUTES


@app.route('/drinks')
@requires_auth('get:drinks')
def get_drinks():
    '''Handle GET requests for drinks'''
    drinks = Drink.query.all()
    return jsonify({
        'success': True,
        'drinks': [drink.short() for drink in drinks]
    })


@app.route('/drinks-detail')
@requires_auth('get:drinks-detail')
def get_drinks_detail():
    '''Handle GET requests for drinks detail'''
    drinks = Drink.query.all()
    return jsonify({
        'success': True,
        'drinks': [drink.long() for drink in drinks]
    })


@app.route('/drinks', methods=['POST'])
@requires_auth('post:drinks')
def post_drinks():
    '''Handle POST requests for drinks'''
    body = request.get_json()
    if not is_valid_schema(body):
        abort(422)
    title = body["title"]
    recipe = body["recipe"]
    drink = Drink.query.filter(
        func.lower(Drink.title) == title.lower()
    ).first()
    if drink is not None:
        abort(422)
    drink = Drink(
        title=title,
        recipe=json.dumps(recipe)
    )
    drink.insert()
    return jsonify({
        'success': True,
        'drinks': [drink.long()]
    })


@app.route('/drinks/<int:drink_id>', methods=['PATCH'])
@requires_auth('patch:drinks')
def patch_drink(drink_id):
    '''Handle PATCH requests for drinks by id'''
    body = request.get_json()
    if not is_valid_schema(body):
        abort(422)
    title = body["title"]
    drink = Drink.query.filter(
        Drink.id != drink_id,
        func.lower(Drink.title) == title.lower()
    ).first()
    if drink is not None:
        abort(422)
    drink = Drink.query.get(drink_id)
    if drink is None:
        abort(404)
    recipe = body["recipe"]
    drink.title = title
    drink.recipe = json.dumps(recipe)
    drink.update()
    return jsonify({
        'success': True,
        'drinks': [drink.long()]
    })


@app.route('/drinks/<int:drink_id>', methods=['DELETE'])
@requires_auth('delete:drinks')
def delete_drink(drink_id):
    '''Handle DELETE requests for drinks by id'''
    drink = Drink.query.get(drink_id)
    if drink is None:
        abort(404)
    drink.delete()
    return jsonify({
        'success': True,
        'delete': drink_id
    })


# Error Handling


@app.errorhandler(400)
def bad_request(error):
    '''Handle HTTP 400 errors'''
    return jsonify({
        'success': False,
        'error': 400,
        'message': 'Bad Request'
    }), 400


@app.errorhandler(404)
def not_found(error):
    '''Handle HTTP 404 errors'''
    return jsonify({
        'success': False,
        'error': 404,
        'message': 'Not Found'
    }), 404


@app.errorhandler(422)
def unprocessable_entity(error):
    '''Handle HTTP 422 errors'''
    return jsonify({
        'success': False,
        'error': 422,
        'message': 'Unprocessable Entity'
    }), 422


@app.errorhandler(500)
def internal_server(error):
    '''Handle HTTP 500 errors'''
    return jsonify({
        'success': False,
        'error': 500,
        'message': 'Internal Server Error'
    }), 500


@app.errorhandler(AuthError)
def auth_error(error):
    '''Handle Auth errors'''
    return jsonify({
        'success': False,
        'error': error.status_code,
        'message': error.error['description']
    }), error.status_code

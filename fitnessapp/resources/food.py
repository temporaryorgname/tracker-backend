from flask import Blueprint
from flask import request
from flask_restful import Api, Resource
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.utils import secure_filename
from flasgger import SwaggerView

import datetime
import json
import os
from PIL import Image
import base64
from io import BytesIO

import os
import boto3

from fitnessapp import database

blueprint = Blueprint('food', __name__)
api = Api(blueprint)

class Food(Resource):
    @login_required
    def get(self, food_id):
        """ Return food entry with the given ID.
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        definitions:
          Food:
            type: object
            properties:
              id:
                type: integer
              date:
                type: string
              name:
                type: string
              quantity:
                type: string
              calories:
                type: number
              protein:
                type: number
              photo_id:
                type: integer
              photo_group_id:
                type: integer
        responses:
          200:
            description: Food entry
            schema:
              $ref: '#/definitions/Food'
        """
        food = database.Food.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=food_id) \
                .order_by(database.Food.date).all()
        return food.to_dict(), 200

    @login_required
    def put(self, food_id):
        """ Update a food entry with a new entry.
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - in: body
            description: New entry.
            required: true
            schema:
              $ref: '#/definitions/Food'
        responses:
          200:
            schema:
              type: object
              properties:
                message:
                  type: string
          400:
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        data = request.get_json()

        # Check that there's an entry at this location belonging to the current user
        f = database.Food.query \
                .filter_by(id=food_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()
        if f is None:
            return json.dumps({
                'error': "ID not found"
            }), 404

        # Create new Food object
        f = database.Food.from_dict(data)
        f.id = food_id
        f.user_id = current_user.get_id()
        try:
            f.validate()
        except Exception as e:
            return json.dumps({
                'error': str(e)
            }), 400

        database.db_session.add(f)
        database.db_session.flush()
        database.db_session.commit()

        return json.dumps({'message': 'success'}), 200

    @login_required
    def delete(self, food_id):
        """ Delete an entry with the given ID.
        ---
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            schema:
              type: object
              properties:
                message:
                  type: string
          404:
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        print("Requesting to delete entry %s." % food_id)
        f = database.Food.query \
                .filter_by(id=food_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()

        if f is None:
            return json.dumps({
                "error": "Unable to find food entry with ID %d." % food_id
            }), 404

        database.db_session.delete(f)
        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

class FoodList(SwaggerView):
    @login_required
    def get(self):
        """ Return all food entries matching the given criteria.
        ---
        parameters:
          - name: date
            in: query
            type: string
            required: true
            format: date
            description: Date
        responses:
          200:
            description: A list of food entries.
            schema:
              type: array
              items:
                $ref: '#/definitions/Food'
        """
        date = request.args.get('date')
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        if date is None:
            foods = database.Food.query \
                    .filter_by(user_id=current_user.get_id()) \
                    .order_by(database.Food.date).all()
        else:
            foods = database.Food.query \
                    .order_by(database.Food.date.desc()) \
                    .filter_by(date=date, user_id=current_user.get_id()) \
                    .all()
        data = [f.to_dict() for f in foods]
        return data, 200

    @login_required
    def post(self):
        """ Create a new food entry
        ---
        parameters:
          - in: body
            description: Entry to create.
            required: true
            schema:
                type: object
                properties:
                  date:
                    type: string
                  name:
                    type: string
                  quantity:
                    type: string
                  calories:
                    type: number
                  protein:
                    type: number
                  photo_id:
                    type: integer
                  photo_group_id:
                    type: integer
        responses:
          201:
            description: ID of newly-created entry.
            schema:
              type: object
              properties:
                id:
                  type: integer
        """
        data = request.get_json()

        f = database.Food.from_dict(data)
        f.user_id = current_user.get_id()
        try:
            f.validate()
        except Exception as e:
            return json.dumps({
                'error': str(e)
            }), 400

        database.db_session.add(f)
        database.db_session.flush()
        database.db_session.commit()

        return json.dumps({
            'id': str(f.id)
        }), 201

    @login_required
    def delete(self):
        """ Delete all food entries matching the given criteria.
        ---
        parameters:
          - name: date
            in: query
            type: string
            required: true
            format: date
            description: Date
        responses:
          200:
            schema:
              type: object
              properties:
                message:
                  type: string
          404:
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        data = request.get_json()
        print("Requesting to delete entry %s." % data['id'])

        for food_id in data['id']:
            f = database.Food.query \
                    .filter_by(id=food_id) \
                    .filter_by(user_id=current_user.get_id()) \
                    .one()
            if f is None:
                return json.dumps({
                    "error": "Unable to find food entry with ID %d." % food_id
                }), 404
            database.db_session.delete(f)

        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

api.add_resource(Food, '/foods/<int:id>')
api.add_resource(FoodList, '/foods')

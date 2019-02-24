from flask import Blueprint
from flask import request
from flask_restful import Api, Resource
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.utils import secure_filename
from flasgger import SwaggerView
import traceback

import datetime
import os
from PIL import Image
import base64
from io import BytesIO
import numpy as np

import os
import boto3

from fitnessapp import database
from fitnessapp import dbutils

blueprint = Blueprint('food', __name__)
api = Api(blueprint)

class Food(Resource):
    @login_required
    def get(self, food_id):
        """ Return food entry with the given ID.
        ---
        tags:
          - food
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
                .one()
        if food.photo_group_id is not None:
            photo_ids = database.Photo.query \
                    .with_entities(
                            database.Photo.id
                    )\
                    .filter_by(user_id=current_user.get_id()) \
                    .filter_by(group_id=food.photo_group_id) \
                    .all()
            photo_ids = [x[0] for x in photo_ids]
        elif food.photo_id is not None:
            photo_ids = [food.photo_id]
        else:
            photo_ids = []
        return {**food.to_dict(), 'photo_ids': photo_ids}, 200

    @login_required
    def put(self, food_id):
        """ Update a food entry with a new entry.
        ---
        tags:
          - food
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
            return {
                'error': "ID not found"
            }, 404

        # Create new Food object
        f.update_from_dict(data)
        try:
            f.validate()
        except Exception as e:
            return {
                'error': str(e)
            }, 400

        database.db_session.commit()

        return {'message': 'success'}, 200

    @login_required
    def delete(self, food_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - food
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
            return {
                "error": "Unable to find food entry with ID %d." % food_id
            }, 404

        database.db_session.delete(f)
        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

class FoodList(Resource):
    @login_required
    def get(self):
        """ Return all food entries matching the given criteria.
        ---
        tags:
          - food
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
        if date is None:
            foods = database.Food.query \
                    .filter_by(user_id=current_user.get_id()) \
                    .filter(database.Food.parent_id.is_(None)) \
                    .order_by(database.Food.id) \
                    .all()
        else:
            foods = database.Food.query \
                    .order_by(database.Food.date.desc()) \
                    .filter_by(user_id=current_user.get_id()) \
                    .filter_by(date=date) \
                    .filter(database.Food.parent_id.is_(None)) \
                    .order_by(database.Food.id) \
                    .all()
            print(len(foods), 'entries found')
        data = [dbutils.food_to_dict(f, True, True) for f in foods]
        return data, 200

    @login_required
    def post(self):
        """ Create a new food entry
        ---
        tags:
          - food
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
                  photo_ids:
                    type: array
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
        try:
            ids = dbutils.update_food_from_dict(data, user_id=current_user.get_id())
        except Exception as e:
            print(traceback.format_exc())
            return {
                'error': str(e)
            }, 400

        foods = database.Food.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter(database.Food.id.in_(ids)) \
                .all()

        return {
            'ids': ids,
            'entities': [
                dbutils.food_to_dict(f, True, True) for f in foods
            ]
        }, 201

    @login_required
    def delete(self):
        """ Delete all food entries matching the given criteria.
        ---
        tags:
          - food
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
        print(type(data))
        print(data)
        for d in data:
            print("Requesting to delete entry %s." % d['id'])

            food_id = d['id']
            f = database.Food.query \
                    .filter_by(id=food_id) \
                    .filter_by(user_id=current_user.get_id()) \
                    .one()
            if f is None:
                return {
                    "error": "Unable to find food entry with ID %d." % food_id
                }, 404
            dbutils.delete_food(f)

        return {"message": "Deleted successfully"}, 200

class FoodSearch(Resource):
    @login_required
    def get(self):
        """ Search food entries for names matching the query string.
        The search is case-insensitive.
        ---
        tags:
          - food
        parameters:
          - name: q
            in: query
            type: string
            required: true
        responses:
          200:
            description: Food entries
            schema:
              properties:
                name:
                  type: string
                quantity:
                  type: string
                calories:
                  type: number
                protein:
                  type: number
                count:
                  type: number
                  description: The number of times this same entry appears.
        """
        if 'q' not in request.args:
            return 'Invalid request. A query is required.', 400
        query = request.args['q']
        foods = database.Food.query \
                .with_entities(
                        func.mode().within_group(database.Food.name),
                        database.Food.quantity,
                        database.Food.calories,
                        database.Food.protein,
                        func.count('*')
                ) \
                .filter_by(user_id=current_user.get_id()) \
                .filter(database.Food.name.ilike('%{0}%'.format(query))) \
                .group_by(
                        func.lower(database.Food.name),
                        database.Food.quantity,
                        database.Food.calories,
                        database.Food.protein,
                ) \
                .order_by(func.count('*').desc()) \
                .limit(5) \
                .all()
        def cast_decimal(dec):
            if dec is None:
                return None
            return float(dec)
        def to_dict(f):
            return {
                'name': f[0],
                'quantity': f[1],
                'calories': cast_decimal(f[2]),
                'protein': cast_decimal(f[3]),
                'count': f[4]
            }
        return {
            'history': [to_dict(f) for f in foods]
        }, 200

class FoodSummary(Resource):
    @login_required
    def get(self):
        """ Give a summary of the user's food consumption
        ---
        tags:
          - food
        responses:
          200:
            schema:
              properties:
                goal_calories:
                  type: number
                calorie_history:
                  type: array
                  description: A list of total calories consumed in the last week. The number at index 0 is today's Calorie consumption, 1 is yesterday, etc.
        """
        start_date = datetime.date.today()-datetime.timedelta(days=7)
        foods = database.engine.execute("""
            SELECT date, SUM(calories)
            FROM public.food
            WHERE date > '{start_date}'
              AND user_id = '{user_id}'
            GROUP BY date
            ORDER BY date DESC
        """.format(start_date=start_date, user_id=current_user.get_id()))

        # Save the data so we can iterate over it more than once
        foods = [x for x in foods]

        def cast_decimal(dec):
            if dec is None:
                return None
            return float(dec)
        def to_dict(f):
            return {
                'date': str(f[0]),
                'calories': cast_decimal(f[1]),
            }
        # Compute rate of change of Calorie consumption
        points = []
        for time,cals in foods:
            if cals is None:
                continue
            time = (time-start_date).total_seconds()
            cals = int(cals)
            points.append((time,cals))
        calorie_change_per_day = None
        if len(points) > 2:
            # Compute line of best fit
            x = [t for t,c in points]
            y = [c for t,c in points]
            slope,_ = np.polyfit(x,y,1)
            calorie_change_per_day = slope*(24*60*60)
        return {
            'history': [to_dict(f) for f in foods],
            'calorie_change_per_day': calorie_change_per_day
        }, 200

api.add_resource(FoodList, '/foods')
api.add_resource(Food, '/foods/<int:food_id>')
api.add_resource(FoodSearch, '/foods/search')
api.add_resource(FoodSummary, '/foods/summary')

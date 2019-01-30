from flask import Blueprint
from flask import request
from flask_restful import Api, Resource
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.utils import secure_filename
from flasgger import SwaggerView

import datetime
import os
from PIL import Image
import base64
from io import BytesIO
import numpy as np

from fitnessapp import database

blueprint = Blueprint('body', __name__)
api = Api(blueprint)

class BodyweightList(Resource):
    @login_required
    def get(self):
        """ Return bodyweight entries.
        ---
        tags:
          - body
        definitions:
          Bodyweight:
            type: object
            properties:
              id:
                type: integer
              date:
                type: string
              time:
                type: string
              bodyweight:
                type: number
        parameters:
          - name: id
            in: query
            type: number
          - name: date
            in: query
            type: string
          - name: user_id
            in: query
            type: number
          - name: page
            in: query
            type: number
            description: Page number. If not provided, will return the 10 most recent entries.
        responses:
          200:
            schema:
              type: array
              items:
                $ref: '#/definitions/Bodyweight'
        """
        # Get filters from query parameters
        filterable_params = ['id', 'date', 'user_id'];
        filter_params = {}
        for p in filterable_params:
            val = request.args.get(p)
            if val is not None:
                filter_params[p] = val
        page = request.args.get('page')
        if page is None:
            page = 0
        weights = database.Bodyweight.query \
                .filter_by(user_id=current_user.get_id()) \
                .order_by(database.Bodyweight.date.desc()) \
                .order_by(database.Bodyweight.time.desc()) \
                .limit(10) \
                .offset(page*10) \
                .all()
        return [{
            'id': w.id,
            'date': str(w.date),
            'time': str(w.time) if w.time is not None else '',
            'bodyweight': float(w.bodyweight)
        } for w in weights], 200

    def delete(self):
        # Get filters from query parameters
        filterable_params = ['id', 'date']
        filter_params = {}
        for p in filterable_params:
            val = request.args.get(p)
            if val is not None:
                filter_params[p] = val
        if len(filter_params) == 0:
            return {
                'error': "No filters provided."
            }, 400

        weights = database.Bodyweight.query \
                .filter_by(**filter_params) \
                .filter_by(user_id=current_user.get_id()) \
                .all()

        if weights is None:
            return {
                'error': "Unable to find requested bodyweight entry."
            }, 404

        for w in weights:
            database.db_session.delete(w)
        database.db_session.flush()
        database.db_session.commit()
        return {
            'message': "Deleted successfully"
        }, 200

    @login_required
    def post(self):
        """ Create a new bodyweight entry.
        ---
        tags:
          - body
        parameters:
          - in: body
            required: true
            schema:
              type: object
              properties:
                bodyweight:
                  type: number
                date:
                  type: string
                  example: '2019-01-01'
                time:
                  type: string
                  example: '4:00:00'
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
        bw = database.Bodyweight()

        try:
            bw.bodyweight = float(data['bodyweight'])
        except:
            return {
                'error': 'No valid bodyweight provided.'
            }, 400
        if 'date' in data:
            bw.date = data['date']
        else:
            return {
                'error': 'No valid date provided.'
            }, 400
        if 'time' in data:
            bw.time= data['time']

        bw.user_id = current_user.get_id()

        database.db_session.add(bw)
        database.db_session.flush()
        database.db_session.commit()

        return {
            'id': bw.id,
            'message': 'Body weight added successfully.'
        }, 200

class Bodyweights(Resource):
    @login_required
    def delete(self, entry_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - body
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
        weight = database.Bodyweight.query \
                .filter_by(id=entry_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()

        if weight is None:
            return {
                'error': "Unable to find requested bodyweight entry."
            }, 404

        database.db_session.delete(weight)
        database.db_session.flush()
        database.db_session.commit()
        return {
            'message': "Deleted successfully"
        }, 200

class BodyweightSummary(Resource):
    @login_required
    def get(self):
        """ Give a summary of the user's bodyweight history
        ---
        tags:
          - body
        responses:
          200:
            schema:
              properties:
                by_time:
                  type: array
                  description: An array containing the mean bodyweight as a function of time of day.
                history:
                  type: object
                  properties:
                    start_date:
                      type: string
                    end_date:
                      type: string
                    data:
                      type: array
                      items: number
                      description: Evenly-spaced bodyweight where the first data point is on `start_date` and the last is on `end_date`.
        """
        weights = database.Bodyweight.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter(database.Bodyweight.time.isnot(None)) \
                .filter(database.Bodyweight.bodyweight.isnot(None)) \
                .all()

        # Compute mean weight by time of day
        weight_by_hour = [[] for _ in range(24)]
        for w in weights:
            weight_by_hour[w.time.hour].append(float(w.bodyweight))
        mean_by_hour = [np.mean(x) if len(x) > 0 else None for x in weight_by_hour]

        # Compute history
        num_buckets = 20
        start_date = weights[0].date
        end_date = weights[-1].date
        bucket_size = (end_date-start_date)/num_buckets
        weight_buckets = [[] for _ in range(num_buckets)]
        current_bucket = 0
        for w in weights:
            while w.date > start_date+(current_bucket+1)*bucket_size:
                current_bucket += 1
            weight_buckets[current_bucket].append(float(w.bodyweight))
            print(w.to_dict())
        mean_weights_over_time = [np.mean(x) if len(x)>0 else None for x in weight_buckets]

        return {
            'by_time': mean_by_hour,
            'history': {
                'start_date': str(start_date),
                'end_date': str(end_date),
                'data': mean_weights_over_time
            }
        }, 200

api.add_resource(BodyweightList, '/body/weights')
api.add_resource(Bodyweights, '/body/weights/<int:entry_id>')
api.add_resource(BodyweightSummary, '/body/weights/summary')



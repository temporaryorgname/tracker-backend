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

from tracker_database import Bodyweight, UserProfile, WeightUnitsEnum
from fitnessapp.extensions import db

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
        weights = db.session.query(Bodyweight) \
                .filter_by(user_id=current_user.get_id()) \
                .order_by(Bodyweight.date.desc()) \
                .order_by(Bodyweight.time.desc()) \
                .limit(10) \
                .offset(page*10) \
                .all()
        units = db.session.query(UserProfile) \
                .with_entities(
                        UserProfile.prefered_units
                )\
                .filter_by(id=current_user.get_id()) \
                .one()[0]
        multiplier = 1
        if units == WeightUnitsEnum.lbs:
            multiplier = 1/0.45359237
        data = [{
            'id': w.id,
            'date': str(w.date),
            'time': str(w.time) if w.time is not None else '',
            'bodyweight': float(w.bodyweight)*multiplier
        } for w in weights]
        data = dict([(d['id'],d) for d in data])
        return {
            'entities': {
                'bodyweight': data
            }
        }, 200

    @login_required
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

        weights = db.session.query(Bodyweight) \
                .filter_by(**filter_params) \
                .filter_by(user_id=current_user.get_id()) \
                .all()
        ids = [w.id for w in weights]

        if weights is None:
            return {
                'error': "Unable to find requested bodyweight entry."
            }, 404

        for w in weights:
            db.session.delete(w)
        db.session.flush()
        db.session.commit()
        return {
            'message': "Deleted successfully",
            'entities': {
                'bodyweight': dict([(i,None) for i in ids])
            }
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
        bw = Bodyweight()
        units = db.session.query(UserProfile) \
                .with_entities(
                        UserProfile.prefered_units
                )\
                .filter_by(id=current_user.get_id()) \
                .one()[0]

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

        if units == WeightUnitsEnum.lbs:
            bw.bodyweight *= 0.45359237

        bw.user_id = current_user.get_id()

        db.session.add(bw)
        db.session.flush()
        db.session.commit()

        return {
            'message': 'Body weight added successfully.',
            'entities': {
                'bodyweight': {
                    bw.id: data
                }
            }
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
        weight = db.session.query(Bodyweight) \
                .filter_by(id=entry_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()

        if weight is None:
            return {
                'error': "Unable to find requested bodyweight entry."
            }, 404

        db.session.delete(weight)
        db.session.flush()
        db.session.commit()
        return {
            'message': "Deleted successfully",
            'entities': {
                'bodyweight': [{weight.id: None}]
            }
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
        weights = db.session.query(Bodyweight) \
                .filter_by(user_id=current_user.get_id()) \
                .filter(Bodyweight.time.isnot(None)) \
                .filter(Bodyweight.bodyweight.isnot(None)) \
                .order_by(Bodyweight.date) \
                .order_by(Bodyweight.time) \
                .all()
        units = db.session.query(UserProfile) \
                .with_entities(
                        UserProfile.prefered_units
                )\
                .filter_by(id=current_user.get_id()) \
                .one()[0]
        units_scale = 1
        if units == WeightUnitsEnum.lbs:
            units_scale = 1/0.45359237

        # Compute mean weight by time of day
        weight_by_hour = [[] for _ in range(24)]
        for w in weights:
            weight_by_hour[w.time.hour].append(float(w.bodyweight))
        mean_by_hour = [np.mean(x)*units_scale if len(x) > 0 else None for x in weight_by_hour]

        # Compute normalized mean weight by time of day
        window_size = datetime.timedelta(days=7)
        min_window_points = 5
        window_start_index = 0 # Window includes this point
        window_end_index = 0 # Window excludes this point
        for i,w in enumerate(weights):
            if w.date > weights[0].date+window_size/2:
                window_end_index = i
                break
        normalized_weight_by_hour = [[] for _ in range(24)]
        for w in weights:
            while weights[window_start_index].date < w.date-window_size/2:
                window_start_index += 1
            while window_end_index < len(weights) and weights[window_end_index].date < w.date+window_size/2:
                window_end_index += 1
            while window_end_index-window_start_index < min_window_points:
                window_start_index -= 1
                window_end_index += 1
            window_start_index = max(0,window_start_index)
            window_end_index = min(len(weights),window_end_index)
            mean_val = np.mean([float(w.bodyweight) for w in weights[window_start_index:window_end_index]])
            normalized_weight_by_hour[w.time.hour].append(float(w.bodyweight)/mean_val-1)
        normalized_mean_by_hour = [np.mean(x) if len(x) > 0 else None for x in normalized_weight_by_hour]

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
        mean_weights_over_time = [np.mean(x)*units_scale if len(x)>0 else None for x in weight_buckets]
        history = {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'data': mean_weights_over_time
        }

        # Compute rate of change
        points = []
        rate_of_change = None
        start_date = weights[-1].date-datetime.timedelta(days=7)
        for w in weights:
            if w.date < start_date:
                continue
            points.append((
                (w.date-start_date).total_seconds(),
                float(w.bodyweight)
            ))
        weight_change_per_day = None
        if len(points) > 2:
            # Compute line of best fit
            x = [t for t,w in points]
            y = [w for t,w in points]
            slope,_ = np.polyfit(x,y,1)
            weight_change_per_day = slope*(24*60*60)*units_scale

        # Compute average bodyweight
        avg_weight = 0
        count = 0
        for w in reversed(weights):
            if datetime.date.today()-w.date > datetime.timedelta(days=7) and count > 5:
                break
            avg_weight += float(w.bodyweight)
            count += 1
        avg_weight *= units_scale
        if count == 0:
            avg_weight = None
        else:
            avg_weight /= count

        return {
            'summary': {
                'by_time': mean_by_hour,
                'normalized_by_time': normalized_mean_by_hour,
                'history': history,
                'weight_change_per_day': weight_change_per_day,
                'units': units.name,
                'avg_weight': avg_weight
            }
        }, 200

api.add_resource(BodyweightList, '/body/weights')
api.add_resource(Bodyweights, '/body/weights/<int:entry_id>')
api.add_resource(BodyweightSummary, '/body/weights/summary')



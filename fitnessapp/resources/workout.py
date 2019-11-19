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

from tracker_database import WorkoutSet, Exercise
from fitnessapp.extensions import db

blueprint = Blueprint('workoutset', __name__)
api = Api(blueprint)

class WorkoutSetList(Resource):
    #@login_required
    def get(self):
        """ Return workout sets.
        ---
        tags:
          - workout
        definitions:
          WorkoutSet:
            type: object
            properties:
              id:
                type: integer
              date:
                type: string
                example: '2019-01-01'
              exercise_id:
                type: number
              parent_id:
                type: number
                description: ID of a parent workout set. This is used for grouping sets together.
              reps:
                type: number
                description: Number of repetitions of the exercise performed.
              duration:
                type: number
                description: Duration of the exercise in seconds.
                example: 30
              tempo:
                type: string
                description: Duration of each portion of the movement (eccentric, pause, concentric, rest).
                example: '1:0:X:1'
              order:
                type: number
                description: The order in which this set was performed relative to other sets on the same day.
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
        responses:
          200:
            schema:
              type: array
              items:
                $ref: '#/definitions/WorkoutSet'
        """
        # Get filters from query parameters
        filterable_params = ['id', 'date', 'user_id'];
        filter_params = {}
        for p in filterable_params:
            val = request.args.get(p)
            if val is not None:
                filter_params[p] = val
        worksets = db.session.query(WorkoutSet) \
                .filter_by(user_id=current_user.get_id()) \
                .order_by(WorkoutSet.date.desc()) \
                .order_by(WorkoutSet.order.desc()) \
                .all()
        data = [{
            'id': s.id,
            'date': str(s.date),
            'reps': s.reps,
        } for s in worksets]
        data = dict([(d['id'],d) for d in data])
        return {
            'entities': {
                'workout_sets': data
            }
        }, 200

    #@login_required
    def post(self):
        """ Create a new workout set entry.
        ---
        tags:
          - workout
        parameters:
          - in: body
            name: body
            required: true
            schema:
              $ref: '#/definitions/WorkoutSet'
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

        workset = WorkoutSet(**data)
        workset.user_id = current_user.get_id()

        db.session.add(workset)
        db.session.flush()
        db.session.commit()

        return {
            'message': 'Workout set added successfully.',
            'entities': {
                'workout_set': {
                    workset.id: workset.to_dict()
                }
            }
        }, 200

class WorkoutSets(Resource):
    #@login_required
    def delete(self, entity_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - workout
        parameters:
          - name: entity_id
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
        entity = db.session.query(WorkoutSet) \
                .filter_by(id=entity_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()

        if entity is None:
            return {
                'error': "Unable to find requested entity."
            }, 404

        db.session.delete(entity)
        db.session.flush()
        db.session.commit()
        return {
            'message': "Deleted successfully",
            'entities': {
                'workout_set': {entity.id: None}
            }
        }, 200

    #@login_required
    def put(self, entity_id):
        """ Update a workout set entry with a new entry.
        ---
        tags:
          - workout
        parameters:
          - name: entity_id
            in: path
            type: integer
            required: true
          - in: body
            name: body
            description: Updated entry.
            required: true
            schema:
              $ref: '#/definitions/WorkoutSet'
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

        entity = db.session.query(WorkoutSet) \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=entity_id) \
                .first()

        if entity is None:
            return {
                'error': "Unable to find requested entity."
            }, 404

        for k,v in data.items():
            entity.__setattr__(k,v)

        db.session.flush()
        db.session.commit()

        return {
            'message': 'success',
            'entities': {
                'workout_set': {
                    entity_id: entity.to_dict()
                }
            }
        }, 200

api.add_resource(WorkoutSetList, '/workout/sets')
api.add_resource(WorkoutSets, '/workout/sets/<int:entity_id>')

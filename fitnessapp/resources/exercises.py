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

from tracker_database import Exercise
from fitnessapp.extensions import db

blueprint = Blueprint('exercises', __name__)
api = Api(blueprint)

class ExerciseList(Resource):
    #@login_required
    def get(self):
        """ Return exercises.
        ---
        tags:
          - exercise
        definitions:
          Exercise:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
                example: 'Squat'
              description:
                type: string
        responses:
          200:
            schema:
              type: array
              items:
                $ref: '#/definitions/Exercise'
        """
        # Get filters from query parameters
        entities = db.session.query(Exercise) \
                .all()
        data = [e.to_dict() for e in entities]
        data = dict([(d['id'],d) for d in data])
        return {
            'entities': {
                'exercises': data
            }
        }, 200

    #@login_required
    def post(self):
        """ Create a new exercise
        ---
        tags:
          - exercise
        parameters:
          - in: body
            name: body
            required: true
            schema:
              $ref: '#/definitions/Exercise'
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

        exercise = Exercise(**data)

        db.session.add(exercise)
        db.session.flush()
        db.session.commit()

        return {
            'message': 'Exercise added successfully.',
            'entities': {
                'exercise': {
                    exercise.id: exercise.to_dict()
                }
            }
        }, 200

class Exercises(Resource):
    #@login_required
    def delete(self, entity_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - exercise
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
        entity = db.session.query(Exercise) \
                .filter_by(id=entity_id) \
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
                'exercise': {entity.id: None}
            }
        }, 200

    #@login_required
    def put(self, entity_id):
        """ Update an exercise entry with a new entry.
        ---
        tags:
          - exercise
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
              $ref: '#/definitions/Exercise'
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

        entity = db.session.query(Exercise) \
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
                'exercise': {
                    entity_id: entity.to_dict()
                }
            }
        }, 200

api.add_resource(ExerciseList, '/exercises')
api.add_resource(Exercises, '/exercises/<int:entity_id>')

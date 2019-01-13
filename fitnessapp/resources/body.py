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
        responses:
          200:
            schema:
              type: array
              items:
                $ref: '#/definitions/Bodyweight'
        """
        weights = database.Bodyweight.query \
                .filter_by(user_id=current_user.get_id()) \
                .order_by(database.Bodyweight.date.desc()) \
                .order_by(database.Bodyweight.time.desc()) \
                .all()
        return [{
            'id': w.id,
            'date': str(w.date),
            'time': str(w.time) if w.time is not None else '',
            'bodyweight': float(w.bodyweight)
        } for w in weights], 200

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

api.add_resource(BodyweightList, '/body/weights')
api.add_resource(Bodyweights, '/body/weights/<int:entry_id>')



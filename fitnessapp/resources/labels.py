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

import tracker_database as database

blueprint = Blueprint('labels', __name__)
api = Api(blueprint)

class Labels(Resource):
    @login_required
    def get(self, label_id):
        """ Return label with the given ID.
        ---
        tags:
          - labels
        parameters:
          - name: label_id
            in: path
            type: integer
            required: true
        definitions:
          Label:
            type: object
            properties:
              id:
                type: integer
              tag_id:
                type: integer
                description: ID of tag associated with this label.
              bounding_box:
                type: array
                items:
                  type: array
                  items:
                    type: number
                example: [[0,0],[0,0]]
              bounding_polygon:
                type: array
                items: 
                  type: array
                  items:
                    type: number
                example: [[0,0],[0,0],[0,0]]
        responses:
          200:
            schema:
              $ref: '#/definitions/Label'
        """
        return {
                'error': 'Not implemented'
        }, 501

    @login_required
    def put(self, label_id):
        """ Update a label with a new entry.
        ---
        tags:
          - labels
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - in: body
            required: true
            schema:
              $ref: '#/definitions/Label'
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

        # Check that this label exists and is owned by the current user
        label = database.PhotoLabel.query \
                .filter_by(id=label_id) \
                .filter_by(user_id=current_user.get_id()) \
                .one()

        # Create new label to replace current one
        label = database.PhotoLabel.from_dict(data)
        label.id = label_id

        database.db_session.add(label)
        database.db_session.flush()
        database.db_session.commit()

        return {'message': 'Success?', 'id': label.id}, 200

    @login_required
    def delete(self, label_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - labels
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
        label = database.PhotoLabel.query \
                .filter_by(id=label_id) \
                .filter_by(user_id=current_user.get_id()) \
                .one()
        database.db_session.delete(label)
        database.db_session.flush()
        database.db_session.commit()

        return {'message': 'Success?', 'id': label.id}, 200

class LabelList(Resource):
    @login_required
    def get(self):
        """ Return some labels?
        ---
        tags:
          - labels
        parameters:
          - name: photo_id
            in: query
            type: number
            description: Not yet implemented. This does nothing for now.
        responses:
          200:
            description: A list of labels
            schema:
              type: array
              items:
                $ref: '#/definitions/Label'
        """
        return {
                'error': 'Not implemented'
        }, 501

    @login_required
    def post(self):
        """ Create a new tag.
        ---
        tags:
          - labels
        parameters:
          - in: body
            description: Entry to create.
            required: true
            schema:
                type: object
                properties:
                  tag_id:
                    type: number
                  bounding_box:
                    type: array
                    items:
                      type: array
                      items:
                        type: number
                    example: [[0,0],[0,0]]
                  bounding_polygon:
                    type: array
                    items: 
                      type: array
                      items:
                        type: number
                    example: [[0,0],[0,0],[0,0]]
        responses:
          201:
            description: ID of newly-created label.
            schema:
              type: object
              properties:
                id:
                  type: integer
        """
        data = request.get_json()

        label = database.PhotoLabel.from_dict(data)
        label.user_id = current_user.get_id()
        try:
            label.validate()
        except Exception as e:
            return {'error': str(e)}, 400

        database.db_session.add(label)
        database.db_session.flush()
        database.db_session.commit()

        return {'id': label.id}, 200

api.add_resource(LabelList, '/labels')


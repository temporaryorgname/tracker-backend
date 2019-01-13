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

blueprint = Blueprint('photo_groups', __name__)
api = Api(blueprint)

class PhotoGroupList(Resource):
    @login_required
    def get(self):
        """ Return all photo entries matching the given criteria.
        ---
        tags:
          - photo groups
        definitions:
          PhotoGroup:
            type: object
            properties:
              id:
                type: integer
              user_id:
                type: integer
                description: ID of the user who uploaded this photo.
              parent_id:
                type: integer
                description: ID of the photo group containing this photo group.
              date:
                type: string
                description: Date on which the photos contained in this group were taken.
        parameters:
          - name: id 
            in: query
            type: number
          - name: user_id 
            in: query
            type: number
          - name: parent_id 
            in: query
            type: number
            description: ID of the parent photo group.
          - name: date
            in: query
            type: string
            format: date
        responses:
          200:
            description: A list of photo groups.
            schema:
              type: array
              items:
                $ref: '#/definitions/PhotoGroup'
        """
        # Get filters from query parameters
        filterable_params = ['id', 'user_id', 'parent_id', 'date']
        filter_params = {}
        for p in filterable_params:
            val = request.args.get(p)
            if val is not None:
                filter_params[p] = val

        groups = database.PhotoGroup.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(**filter_params) \
                .all()
        data = [g.to_dict() for g in groups]
        return data, 200

    @login_required
    def post(self):
        """ Create a new photo group.
        ---
        tags:
          - photo groups
        parameters:
          - in: body
            description: Entry to create.
            required: true
            schema:
                type: object
                properties:
                  date:
                    type: string
                  parent_id:
                    type: number
                  user_id:
                    type: number
        responses:
          201:
            description: ID of newly-created group.
            schema:
              type: object
              properties:
                id:
                  type: integer
        """
        data = request.get_json()

        group = database.PhotoGroup.from_dict(data)
        group.user_id = current_user.get_id()

        database.db_session.add(group)
        database.db_session.flush()
        database.db_session.commit()

        return {
            'id': group.id
        },200

api.add_resource(PhotoGroupList, '/photo_groups')


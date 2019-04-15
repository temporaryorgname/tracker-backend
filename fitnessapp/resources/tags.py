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

from fitnessapp import database

blueprint = Blueprint('tags', __name__)
api = Api(blueprint)

class TagList(Resource):
    @login_required
    def get(self):
        """ Return all tags belonging to the logged in user
        ---
        tags:
          - tags
        definitions:
          Tag:
            type: object
            properties:
              id:
                type: integer
              user_id:
                type: integer
                description: ID of the user who created this tag
              parent_id:
                type: integer
              tag:
                type: string
                description: A human-readable identifier representing the tag.
              description:
                type: string
                description: A description of what this tag represents.
        parameters:
          - name: user_id 
            in: query
            type: number
            description: Not yet implemented. This does nothing for now.
        responses:
          200:
            description: A list of tags
            schema:
              type: array
              items:
                $ref: '#/definitions/Tag'
        """
        user_id = current_user.get_id()
        # TODO: Filter by user
        tags = database.Tag.query.all()
        tags = dict([(t.id, t.to_dict()) for t in tags])
        return {
            'entities': {
                'tags': tags
            }
        }, 200

    @login_required
    def post(self):
        """ Create a new tag.
        ---
        tags:
          - tags
        parameters:
          - in: body
            description: Entry to create.
            required: true
            schema:
                type: object
                properties:
                  parent_id:
                    type: number
                  user_id:
                    type: number
                  tag:
                    type: string
                  description:
                    type: string
        responses:
          201:
            description: ID of newly-created tag.
            schema:
              type: object
              properties:
                id:
                  type: integer
        """
        data = request.get_json()

        tag = database.Tag.from_dict(data)
        tag.user_id = current_user.get_id()
        try:
            tag.validate()
        except Exception as e:
            return {'error': str(e)}, 400

        database.db_session.add(tag)
        database.db_session.flush()
        database.db_session.commit()

        return {
                'message': 'Success?',
                'entities': {
                    'tags': {tag.id: tag.to_dict()}
                }
        }, 200

class TagSearch(Resource):
    @login_required
    def get(self):
        """ Return some tags matching the provided query. Limit of five results.
        ---
        tags:
          - tags
        parameters:
          - name: q
            in: query
            type: string
            description: String to search for.
        responses:
          200:
            description: A list of tags
            schema:
              type: array
              items:
                $ref: '#/definitions/Tag'
        """
        if 'q' not in request.args:
            return 'Invalid request. A query is required.', 400
        query = request.args['q']
        tags = database.Tag.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter(database.Tag.tag.ilike('%{0}%'.format(query))) \
                .limit(5) \
                .all()
        data = [t.to_dict() for t in tags]
        return data, 200

api.add_resource(TagList, '/tags')
api.add_resource(TagSearch, '/tags/search')

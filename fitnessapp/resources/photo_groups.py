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
from fitnessapp import dbutils

blueprint = Blueprint('photo_groups', __name__)
api = Api(blueprint)

class PhotoGroups(Resource):
    @login_required
    def get(self, group_id):
        """ Return photo group with the given ID.
        ---
        tags:
          - photo groups
        parameters:
          - name: id
            in: path
            type: integer
            required: true
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
        responses:
          200:
            description: Photo group entry
            schema:
              $ref: '#/definitions/PhotoGroup'
        """
        group = database.PhotoGroup.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=group_id) \
                .one()
        if group is None:
            return {
                'error': 'Photo ID not found'
            }, 404
        return group.to_dict(), 200

    @login_required
    def put(self, group_id):
        """ Update a photo group with a new entry.
        ---
        tags:
          - photo groups
        responses:
          501:
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        return {'error': 'Not implemented'}, 501

    @login_required
    def delete(self, group_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - photo groups
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
        group = database.PhotoGroup.query \
                .filter_by(id=group_id) \
                .filter_by(user_id=current_user.get_id()) \
                .one()
        if group is None:
            return {
                "error": "Unable to find photo group with ID %d." % group_id
            }, 404
        database.db_session.delete(group)

        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

class PhotoGroupList(Resource):
    @login_required
    def get(self):
        """ Return all photo entries matching the given criteria.
        ---
        tags:
          - photo groups
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

    @login_required
    def delete(self):
        """ Delete all photo groups matching the given criteria.
        ---
        tags:
          - photo groups
        parameters:
          - in: body
            description: Filter parameters for the object(s) to delete.
            required: true
            schema:
                type: object
                properties:
                  id:
                    type: number
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

            group_id = d['id']
            g = database.Food.query \
                    .filter_by(id=group_id) \
                    .filter_by(user_id=current_user.get_id()) \
                    .one()
            if f is None:
                return {
                    "error": "Unable to find photo group with ID %d." % group_id
                }, 404
            database.db_session.delete(g)

        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

class PhotoGroupFood(Resource):
    @login_required
    def get(self, group_id):
        """ Return the food entry associated with the given photo group.
        ---
        tags:
          - photo groups
          - food
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Food entry
            schema:
              $ref: '#/definitions/Food'
        """
        group = database.PhotoGroup.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=group_id) \
                .first()
        if group is None:
            return {
                'error': 'Photo group ID not found'
            }, 404

        food = database.Food.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(photo_group_id=group.id) \
                .filter_by(parent_id=None) \
                .all()
        return [dbutils.food_to_json(
            f, with_photos=True, with_children=True
        ) for f in food], 200

class PhotoGroupPhotos(Resource):
    @login_required
    def get(self, group_id):
        """ Return the photos associated with the given photo group.
        ---
        tags:
          - photo groups
          - photos
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            schema:
              $ref: '#/definitions/Photo'
        """
        group = database.PhotoGroup.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=group_id) \
                .first()
        if group is None:
            return {
                'error': 'Photo group ID not found'
            }, 404

        photos = database.Photo.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(group_id=group.id) \
                .all()
        return [p.to_dict() for p in photos], 200

api.add_resource(PhotoGroups, '/photo_groups/<int:group_id>')
api.add_resource(PhotoGroupList, '/photo_groups')
api.add_resource(PhotoGroupFood, '/photo_groups/<int:group_id>/food')
api.add_resource(PhotoGroupPhotos, '/photo_groups/<int:group_id>/photos')

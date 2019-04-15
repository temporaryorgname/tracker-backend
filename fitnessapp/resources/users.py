from flask import Blueprint
from flask import request
from flask_restful import Api, Resource
import flask_login
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
import bcrypt

from fitnessapp import database

blueprint = Blueprint('users', __name__)
api = Api(blueprint)

class UserList(Resource):
    def post(self):
        """ Create a new user
        ---
        tags:
          - users
        parameters:
          - in: body
            required: true
            schema:
              type: object
              properties:
                name:
                  type: string
                email:
                  type: string
                  example: 'name@email.com'
                password:
                  type: string
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

        user = database.User()
        user.email = data['email']
        user.password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt(12))

        existing_user = database.User.query \
                .filter_by(email=user.email) \
                .all()
        if len(existing_user) == 0:
            database.db_session.add(user)
            database.db_session.flush()
            database.db_session.commit()
            flask_login.login_user(user)
        else:
            return {
                'error': "User already exists"
            }, 400

        profile = database.UserProfile()
        profile.id = user.id
        profile.display_name = data['name']
        profile.prefered_units = 'kg'
        database.db_session.add(profile)
        database.db_session.flush()
        database.db_session.commit()

        return {
            'message': "User created"
        }, 200

class UserProfiles(Resource):
    @login_required
    def get(self, user_id):
        """ Return user with the given ID.
        ---
        tags:
          - user profiles
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
        definitions:
          UserProfile:
            type: object
            properties:
              id:
                type: integer
              display_name:
                type: string
              last_activity:
                type: date
              prefered_units:
                type: string
              target_weight:
                type: number
              target_calories:
                type: number
              weight_goal:
                type: string
              country:
                type: string
              state:
                type: string
              city:
                type: string
        responses:
          200:
            description: User profile
            schema:
              $ref: '#/definitions/UserProfile'
        """
        user_id = int(user_id)
        user = database.UserProfile.query \
                .filter_by(id=user_id) \
                .first()

        if user is None:
            return {
                'error': 'No user matching ID '+str(user_id)
            }, 400

        if user_id == current_user.get_id():
            result = {
                'id': user.id,
                'display_name': user.display_name,
                'gender': user.gender,
                'last_activity': user.last_activity,

                'prefered_units': user.prefered_units,

                'target_weight': user.target_weight,
                'target_calories': user.target_calories,
                'weight_goal': user.weight_goal,

                'country': user.country,
                'state': user.state,
                'city': user.city
            }
        else:
            result = {
                'id': user.id,
                'display_name': user.display_name,
                'last_activity': user.last_activity
            }
        return {
            'entities': {
                'userProfiles': {
                    user.id: result
                }
            }
        }, 200

    @login_required
    def put(self, user_id):
        """ Update a user's profile
        ---
        tags:
          - user profiles
        parameters:
          - name: id
            in: path
            type: integer
            required: true
          - in: body
            description: Updated entry.
            required: true
            schema:
              $ref: '#/definitions/UserProfile'
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

        # Make sure the user is modifying their own account
        if user_id != current_user.get_id():
            return {
                'error': 'You do not have permission to modify this account'
            }, 400

        user = database.UserProfile.query \
                .filter_by(id=user_id) \
                .filter_by(id=current_user.get_id()) \
                .one()
        if user is None:
            return {
                'error': "ID not found"
            }, 404

        # Create new Food object
        user.update_from_dict(data)
        try:
            user.validate()
        except Exception as e:
            return {
                'error': str(e)
            }, 400

        database.db_session.commit()

        return {
                'message': 'success',
                'entities': {
                    'userProfiles': {
                        # TODO
                    }
                }
        }, 200

api.add_resource(UserList, '/users')
api.add_resource(UserProfiles, '/user_profiles/<int:user_id>')

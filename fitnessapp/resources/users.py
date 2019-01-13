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

blueprint = Blueprint('users', __name__)
api = Api(blueprint)

class Users(Resource):
    @login_required
    def get(self, user_id):
        """ Return user with the given ID.
        ---
        tags:
          - users
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
        definitions:
          User:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              email:
                type: string
              verified_email:
                type: string
              last_activity:
                type: date
        responses:
          200:
            description: User
            schema:
              $ref: '#/definitions/User'
        """
        user_id = int(user_id)
        user = database.User.query \
                .filter_by(id=user_id) \
                .first()

        if user is None:
            return {
                'error': 'No user matching ID '+str(user_id)
            }, 400

        if user_id == current_user.get_id():
            return {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'verified_email': user.verified_email,
                'last_activity': user.last_activity
            }, 200
        else:
            return {
                'id': user.id,
                'name': user.name,
                'last_activity': user.last_activity
            }, 200

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
        user.name = data['name']
        user.email = data['email']
        user.password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt(12))

        existing_user = database.User.query.filter_by(email=user.email).all()
        if len(existing_user) == 0:
            database.db_session.add(user)
            database.db_session.flush()
            database.db_session.commit()
            flask_login.login_user(user)
            return {
                'message': "User created"
            }, 200
        else:
            return {
                'error': "User already exists"
            }, 400

api.add_resource(Users, '/users/<int:user_id>')
api.add_resource(UserList, '/users')

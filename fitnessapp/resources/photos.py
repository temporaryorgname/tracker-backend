from flask import Blueprint, Response, send_file
from flask import request
from flask_restful import Api, Resource
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug import FileWrapper
from werkzeug.utils import secure_filename
from flasgger import SwaggerView

import datetime

from fitnessapp import dbutils
from tracker_database import Photo, Food
from fitnessapp.extensions import db

blueprint = Blueprint('photos', __name__)
api = Api(blueprint)

class Photos(Resource):
    @login_required
    def get(self, photo_id):
        """ Return photo entry with the given ID.
        ---
        tags:
          - photos
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        definitions:
          Photo:
            type: object
            properties:
              id:
                type: integer
              user_id:
                type: integer
                description: ID of the user who uploaded this photo.
              food_id:
                type: integer
                description: ID of food entry associated with this photo.
              date:
                type: string
                description: Date on which the photo was taken.
        responses:
          200:
            description: Photo entry
            schema:
              $ref: '#/definitions/Photo'
        """
        photo = db.session.query(Photo) \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=photo_id) \
                .one()
        if photo is None:
            return {
                'error': 'Photo ID not found'
            }, 404
        return photo.to_dict(), 200

    @login_required
    def put(self, photo_id):
        """ Update a photo entry with a new entry.
        ---
        tags:
          - photos
        responses:
          501:
            schema:
              type: object
              properties:
                error:
                  type: string
        """
        data = request.get_json()
        photo = db.session.query(Photo) \
                .filter_by(id=photo_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()

        if photo is None:
            return {'error': 'No photo found with this ID.'}, 404

        if data['group_id']:
            photo.group_id = int(data['group_id'])

        db.session.flush()
        db.session.commit()

        return {'message': 'Updated successfully'}, 200

    @login_required
    def delete(self, photo_id):
        """ Delete an entry with the given ID.
        ---
        tags:
          - photos
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
        p = db.session.query(Photo) \
                .filter_by(id=photo_id) \
                .filter_by(user_id=current_user.get_id()) \
                .one()
        if p is None:
            return {
                "error": "Unable to find photo with ID %d." % photo_id
            }, 404
        dbutils.delete_photo(p)

        return {
            "message": "Deleted successfully",
            "entities": {
                "photos": {
                    photo_id: None
                }
            }
        }, 200

class PhotoList(Resource):
    @login_required
    def get(self):
        """ Return all photo entries matching the given criteria.
        ---
        tags:
          - photos
        parameters:
          - name: id 
            in: query
            type: number
          - name: user_id 
            in: query
            type: number
          - name: group_id 
            in: query
            type: number
          - name: date
            in: query
            type: string
            format: date
        responses:
          200:
            description: A list of photo entries.
            schema:
              type: array
              items:
                $ref: '#/definitions/Photo'
        """
        # Get filters from query parameters
        filterable_params = ['id', 'user_id', 'date', 'group_id']
        filter_params = {}
        for p in filterable_params:
            val = request.args.get(p)
            if val is not None:
                filter_params[p] = val
        # Query database
        photos = db.session.query(Photo) \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(**filter_params) \
                .all()
        return {
            'entities': {
                'photos': dict([(p.id,dbutils.photo_to_dict(p)) for p in photos])
            }
        }, 200

    @login_required
    def post(self):
        """ Create a new photo entry
        ---
        tags:
          - photos
        consumes:
          - multipart/form-data
        parameters:
          - in: formData
            name: date
            type: string
            description: Date on which the photo was taken
          - in: formData
            name: file
            type: file
            description: File to upload
        responses:
          201:
            description: ID of newly-created entry.
            schema:
              type: object
              properties:
                id:
                  type: integer
        """
        # check if the post request has the file part
        if 'file' not in request.files:
            return "No file provided.", 400
        file = request.files['file']

        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return "No file name.", 400
        if file:
            # Create food entry
            photo = Photo()
            photo.file_name = ""
            photo.user_id = current_user.get_id()
            photo.upload_time = datetime.datetime.utcnow()
            photo.date = request.form.get('date')
            photo.time = request.form.get('time')

            db.session.add(photo)
            db.session.flush()

            # Save photo
            file_name = str(photo.id)
            photo.file_name = file_name
            dbutils.save_photo_data(file, file_name=file_name, delete_local=False)
            # Get EXIF data if needed
            exif_data = dbutils.get_photo_exif(file_name)
            if exif_data is not None:
                if photo.time is None and 0x9003 in exif_data:
                    photo.time = exif_data[0x9003].split(' ')[1]
                if photo.date is None and 0x9003 in exif_data:
                    photo.date = exif_data[0x9003].split(' ')[0].replace(':','-')
            # Save file name
            db.session.flush()
            db.session.commit()

            return {
                'message': 'Photo uploaded successfully.',
                'entities': {
                    'photos': {
                        photo.id: dbutils.photo_to_dict(photo)
                    }
                }
            }, 200

    @login_required
    def delete(self):
        """ Delete all photos matching the given criteria.
        ---
        tags:
          - photos
        parameters:
          - in: body
            description: Object(s) to delete
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
        deleted_ids = []
        for d in data:
            print("Requesting to delete entry %s." % d['id'])

            photo_id = d['id']
            deleted_ids.append(photo_id)
            p = db.session.query(Photo) \
                    .filter_by(id=photo_id) \
                    .filter_by(user_id=current_user.get_id()) \
                    .one()
            if p is None:
                return {
                    "error": "Unable to find photo with ID %d." % photo_id
                }, 404
            dbutils.delete_photo(p, commit=False)

        db.session.commit()
        return {
            "message": "Deleted successfully",
            "entities": {
                "photos": dict([(i,None) for i in deleted_ids])
            }
        }, 200

class PhotoFood(Resource):
    @login_required
    def get(self, photo_id):
        """ Return the food entry associated with the given photo.
        ---
        tags:
          - photos
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
        photo = db.session.query(Photo) \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=photo_id) \
                .first()
        if photo is None:
            return {
                'error': 'Photo ID not found'
            }, 404

        if photo.group_id is None:
            food = db.session.query(Food) \
                    .filter_by(user_id=current_user.get_id()) \
                    .filter_by(photo_id=photo_id) \
                    .filter_by(parent_id=None) \
                    .all()
        else:
            food = db.session.query(Food) \
                    .filter_by(user_id=current_user.get_id()) \
                    .filter_by(photo_group_id=photo.group_id) \
                    .filter_by(parent_id=None) \
                    .all()
        return [dbutils.food_to_json(
            f, with_photos=True, with_children=True
        ) for f in food], 200

class PhotoFile(Resource):
    @login_required
    def get(self, photo_id):
        """ Return the file saved under the given photo id.
        ---
        tags:
          - photos
        parameters:
          - name: id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: PNG File
        """
        photo = db.session.query(Photo) \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=photo_id) \
                .first()
        if photo is None:
            return {
                'error': 'Photo ID not found'
            }, 404

        file_name = dbutils.get_photo_file_name(photo.id, format='png', size=700)
        return send_file(file_name, mimetype='image/png', attachment_filename='file.png')

api.add_resource(PhotoList, '/photos')
api.add_resource(Photos, '/photos/<int:photo_id>')
#api.add_resource(PhotoFood, '/photos/<int:photo_id>/food')
api.add_resource(PhotoFile, '/photos/<int:photo_id>/file')

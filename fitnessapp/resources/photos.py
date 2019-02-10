from flask import Blueprint
from flask import request
from flask import current_app as app
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

import os
import boto3

from fitnessapp import database
from fitnessapp import dbutils

s3 = boto3.resource('s3')
if 'LOGS_PHOTO_BUCKET_NAME' in os.environ:
    PHOTO_BUCKET_NAME = os.environ['LOGS_PHOTO_BUCKET_NAME']
else:
    PHOTO_BUCKET_NAME = 'dev-hhixl-food-photos-700'

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
              group_id:
                type: integer
                description: ID of the group of photos this photo belongs to.
              date:
                type: string
                description: Date on which the photo was taken.
        responses:
          200:
            description: Photo entry
            schema:
              $ref: '#/definitions/Photo'
        """
        photo = database.Photo.query \
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
        return {'error': 'Not implemented'}, 501

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
        p = database.Photo.query \
                .filter_by(id=photo_id) \
                .filter_by(user_id=current_user.get_id()) \
                .one()
        if p is None:
            return {
                "error": "Unable to find photo with ID %d." % photo_id
            }, 404
        database.db_session.delete(p)

        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

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
        photos = database.Photo.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(**filter_params) \
                .all()
        return [p.to_dict() for p in photos], 200

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
            photo = database.Photo()
            photo.file_name = ""
            photo.user_id = current_user.get_id()
            photo.upload_time = datetime.datetime.utcnow()
            photo.date = request.form.get('date')
            photo.time = request.form.get('time')
            database.db_session.add(photo)
            database.db_session.flush()
            database.db_session.commit()
            # Use ID as file name
            photo.file_name = photo.id
            filename = str(photo.file_name)
            # Save file
            filename_original = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            filename_700 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-700' % filename)
            filename_32 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-32' % filename)
            file.save(filename_original)
            # Resize photo
            img = Image.open(filename_original)
            img.thumbnail((700,700))
            # Remove transparency if there's an alpha channel
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                print('Found transparency. Processing alpha channels.')
                alpha = img.split()[3]
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=alpha)
                img = background
            # Save smaller image
            img.save(filename_700, 'jpeg') 
            # Upload small image to AWS
            with open(filename_700, 'rb') as data:
                s3.Bucket(PHOTO_BUCKET_NAME).put_object(Key=filename, Body=data)
            # Resize to tiny thumbnail size
            img.thumbnail((32,32))
            img.save(filename_32, 'jpeg') 
            # Delete large local files
            os.remove(filename_original)
            os.remove(filename_700)
            # Save file name
            database.db_session.flush()
            database.db_session.commit()
            return {'id': photo.id},200

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
        for d in data:
            print("Requesting to delete entry %s." % d['id'])

            photo_id = d['id']
            p = database.Photo.query \
                    .filter_by(id=photo_id) \
                    .filter_by(user_id=current_user.get_id()) \
                    .one()
            if f is None:
                return {
                    "error": "Unable to find photo with ID %d." % photo_id
                }, 404
            database.db_session.delete(p)

        database.db_session.flush()
        database.db_session.commit()
        return {"message": "Deleted successfully"}, 200

class PhotoData(Resource):
    @login_required
    def get(self, photo_id):
        """ Return all photo entries matching the given criteria.
        ---
        tags:
          - photos
        parameters:
          - name: photo_id 
            in: path
            type: number
            required: true
          - name: size
            in: query
            type: number
            enum: [32,700]
            description: Maximum size of either dimensions.
        responses:
          200:
            description: A list of photo entries.
            schema:
              type: object
              properties:
                data:
                  type: string
                  description: A base64 representation of the image file.
        """
        size = request.args.get('size')
        if size is None:
            size = 32
        size = int(size)
        if size not in [32,700]:
            return {'error': 'Unsupported size.'}, 400

        filename = str(photo_id)
        fp = database.Photo.query \
                .filter_by(id=photo_id) \
                .one()
        if fp is None:
            return "File ID not found.", 404

        def get_Local_image(size):
            filename = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    '%s-%s'%(fp.file_name, size))
            try:
                return Image.open(filename)
            except Exception:
                print('Failed to load tiny thumbnail locally for file %s.' % filename)
        def get_s3_image(size):
            filename = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    '%s-700'%(fp.file_name))
            filename_resized = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    '%s-%s'%(fp.file_name,size))
            try:
                with open(filename, "wb") as f:
                    s3.Bucket(PHOTO_BUCKET_NAME) \
                      .Object(str(photo_id)) \
                      .download_fileobj(f)
                img = Image.open(filename)
                if size == 700:
                    return img
                img.thumbnail((size,size))
                img.save(filename_resized,'PNG')
                return img
            except Exception as e:
                print("Unable to retrieve file %s from AWS servers." % filename)

        img = get_Local_image(size)
        if img is None:
            img = get_s3_image(size)
        if img is None:
            return {
                'error': 'Unable to retrieve file %s' % filename
            }, 404

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue())
        # TODO: Return a application/octect-stream response instead of a JSON-wrapped base64 string.
        return {
            'id': photo_id,
            'format': 'png',
            'data': img_str.decode()
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
        photo = database.Photo.query \
                .filter_by(user_id=current_user.get_id()) \
                .filter_by(id=photo_id) \
                .first()
        if photo is None:
            return {
                'error': 'Photo ID not found'
            }, 404

        if photo.group_id is None:
            food = database.Food.query \
                    .filter_by(user_id=current_user.get_id()) \
                    .filter_by(photo_id=photo_id) \
                    .filter_by(parent_id=None) \
                    .all()
        else:
            food = database.Food.query \
                    .filter_by(user_id=current_user.get_id()) \
                    .filter_by(photo_group_id=photo.group_id) \
                    .filter_by(parent_id=None) \
                    .all()
        return [dbutils.food_to_json(
            f, with_photos=True, with_children=True
        ) for f in food], 200

api.add_resource(PhotoList, '/photos')
api.add_resource(Photos, '/photos/<int:photo_id>')
#api.add_resource(PhotoData, '/photos/<int:photo_id>/data')
api.add_resource(PhotoData, '/photo_data/<int:photo_id>')
api.add_resource(PhotoFood, '/photos/<int:photo_id>/food')

from flask import render_template
from flask import Blueprint
from flask import request
from flask import current_app as app
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.utils import secure_filename

import datetime
import json
import os
from PIL import Image
import base64
from io import BytesIO

import os
import boto3

from fitnessapp import database

s3 = boto3.resource('s3')
if 'LOGS_PHOTO_BUCKET_NAME' in os.environ:
    PHOTO_BUCKET_NAME = os.environ['LOGS_PHOTO_BUCKET_NAME']
else:
    PHOTO_BUCKET_NAME = 'dev-hhixl-food-photos-700'
food_bp = Blueprint('food', __name__)

@food_bp.route('/foods', methods=['GET'])
@login_required
def get_food():
    date = request.args.get('date')
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    if date is None:
        foods = database.Food.query \
                .filter_by(user_id=current_user.get_id()) \
                .order_by(database.Food.date).all()
    else:
        foods = database.Food.query \
                .order_by(database.Food.date.desc()) \
                .filter_by(date=date, user_id=current_user.get_id()) \
                .all()
    data = [f.to_dict() for f in foods]
    return json.dumps(data), 200

@food_bp.route('/foods', methods=['POST'])
@login_required
def new_food():
    data = request.get_json()

    f = database.Food.from_dict(data)
    f.user_id = current_user.get_id()
    try:
        f.validate()
    except Exception as e:
        return json.dumps({
            'error': str(e)
        }), 400

    database.db_session.add(f)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({
        'id': str(f.id)
    }), 200

@food_bp.route('/foods/<food_id>', methods=['PUT'])
@login_required
def update_food(food_id): # TODO: Does not work for numerical values yet
    data = request.get_json()

    # Check that there's an entry at this location belonging to the current user
    f = database.Food.query \
            .filter_by(id=food_id) \
            .filter_by(user_id=current_user.get_id()) \
            .first()
    if f is None:
        return json.dumps({
            'error': "ID not found"
        }), 404

    # Create new Food object
    f = database.Food.from_dict(data)
    f.id = food_id
    f.user_id = current_user.get_id()
    try:
        f.validate()
    except Exception as e:
        return json.dumps({
            'error': str(e)
        }), 400

    database.db_session.add(f)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({'message': 'success'}), 200

@food_bp.route('/foods', methods=['DELETE'])
@login_required
def delete_many_foods():
    data = request.get_json()
    print("Requesting to delete entry %s." % data['id'])

    for food_id in data['id']:
        f = database.Food.query \
                .filter_by(id=food_id) \
                .filter_by(user_id=current_user.get_id()) \
                .one()
        if f is None:
            return json.dumps({
                "error": "Unable to find food entry with ID %d." % food_id
            }), 404
        database.db_session.delete(f)

    database.db_session.flush()
    database.db_session.commit()
    return "Deleted successfully",200

@food_bp.route('/foods/<food_id>', methods=['DELETE'])
@login_required
def delete_food(food_id):
    print("Requesting to delete entry %s." % food_id)
    f = database.Food.query \
            .filter_by(id=food_id) \
            .filter_by(user_id=current_user.get_id()) \
            .first()

    if f is None:
        return json.dumps({
            "error": "Unable to find food entry with ID %d." % food_id
        }), 404

    database.db_session.delete(f)
    database.db_session.flush()
    database.db_session.commit()
    return "Deleted successfully",200

@food_bp.route('/foods/search', methods=['GET'])
@login_required
def search_food():
    if 'q' not in request.args:
        return 'Invalid request. A query is required.', 400
    query = request.args['q']
    foods = database.Food.query \
            .with_entities(
                    func.mode().within_group(database.Food.name),
                    database.Food.quantity,
                    database.Food.calories,
                    database.Food.protein,
                    func.count('*')
            ) \
            .filter_by(user_id=current_user.get_id()) \
            .filter(database.Food.name.ilike('%{0}%'.format(query))) \
            .group_by(
                    func.lower(database.Food.name),
                    database.Food.quantity,
                    database.Food.calories,
                    database.Food.protein,
            ) \
            .order_by(func.count('*').desc()) \
            .limit(5) \
            .all()
    def cast_decimal(dec):
        if dec is None:
            return None
        return float(dec)
    def to_dict(f):
        return {
            'name': f[0],
            'quantity': f[1],
            'calories': cast_decimal(f[2]),
            'protein': cast_decimal(f[3]),
            'count': f[4]
        }
    data = [to_dict(f) for f in foods]
    return json.dumps(data), 200

@food_bp.route('/photos', methods=['GET'])
@login_required
def get_photos():
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
    return json.dumps([p.to_dict() for p in photos]), 200

@food_bp.route('/photos/<int:photo_id>', methods=['GET'])
@login_required
def get_photo_by_id(photo_id):
    photo = database.Photo.query \
            .filter_by(user_id=current_user.get_id()) \
            .filter_by(id=photo_id) \
            .one()
    if photo is None:
        return json.dumps({
            'error': 'Photo ID not found'
        }), 404
    return json.dumps(photo.to_dict()), 200

@food_bp.route('/photos/<int:photo_id>/data', methods=['GET'])
@login_required
def get_photo_data(photo_id):
    size = int(request.args.get('size'))
    if size is None:
        size = 32
    if size not in [32,700]:
        return json.dumps({'error': 'Unsupported size.'}), 400

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
        return json.dumps({
            'error': 'Unable to retrieve file %s' % filename
        }), 404

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue())
    return json.dumps({
        'data': img_str.decode()
    }), 200

@food_bp.route('/photos', methods=['POST'])
@login_required
def add_food_photo():
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
        return json.dumps({'id': food_photo.id}),200

@food_bp.route('/food/photo/predict/<int:photo_id>', methods=['GET'])
@login_required
def predict_class(photo_id):
    return json.dumps([]), 200

@food_bp.route('/photo_groups', methods=['GET'])
@login_required
def get_food_photo_groups():
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
    return json.dumps(data), 200

@food_bp.route('/photo_groups', methods=['POST'])
@login_required
def add_food_photo_group():
    data = request.get_json()

    group = database.PhotoGroup.from_dict(data)
    group.user_id = current_user.get_id()

    database.db_session.add(group)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({
        'id': str(group.id)
    }),200

@food_bp.route('/tags', methods=['GET'])
@login_required
def get_tags():
    user_id = current_user.get_id()
    # TODO: Filter by user
    tags = database.Tag.query.all()
    tags = [t.to_dict() for t in tags]
    return json.dumps(tags), 200

@food_bp.route('/tags', methods=['POST'])
@login_required
def create_tag():
    data = request.get_json()

    tag = database.Tag.from_dict(data)
    tag.user_id = current_user.get_id()
    try:
        tag.validate()
    except Exception as e:
        return json.dumps({'error': str(e)}), 400

    database.db_session.add(tag)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({'message': 'Success?', 'id': tag.id}), 200

@food_bp.route('/tags/search', methods=['GET'])
@login_required
def search_tags():
    if 'q' not in request.args:
        return 'Invalid request. A query is required.', 400
    query = request.args['q']
    tags = database.Tag.query \
            .filter_by(user_id=current_user.get_id()) \
            .filter(database.Tag.tag.ilike('%{0}%'.format(query))) \
            .limit(5) \
            .all()
    data = [{
        'id': t.id,
        'tag': t.tag,
        'parent_id': t.parent_id
    } for t in tags]
    return json.dumps(data), 200

@food_bp.route('/photos/<photo_id>/labels', methods=['GET'])
@login_required
def get_photo_labels(photo_id):
    labels = database.PhotoLabel.query \
            .filter_by(photo_id=photo_id) \
            .filter_by(user_id=current_user.get_id()) \
            .all()
    labels = [l.to_dict() for l in labels]

    return json.dumps(labels),200

@food_bp.route('/photos/<photo_id>/labels', methods=['POST'])
@login_required
def create_food_photo_labels(photo_id):
    data = request.get_json()

    label = database.PhotoLabel.from_dict(data)
    label.user_id = current_user.get_id()
    label.photo_id = photo_id
    try:
        label.validate()
    except Exception as e:
        return json.dumps({'error': str(e)}), 400

    database.db_session.add(label)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({'id': label.id}), 200

@food_bp.route('/labels/<label_id>', methods=['PUT'])
@login_required
def update_photo_labels(label_id):
    data = request.get_json()

    # Check that this label exists and is owned by the current user
    label = database.FoodPhotoLabel.query \
            .filter_by(id=label_id) \
            .filter_by(user_id=current_user.get_id()) \
            .one()

    # Create new label to replace current one
    label = database.PhotoLabel.from_dict(data)
    label.id = label_id

    database.db_session.add(label)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({'message': 'Success?', 'id': label.id}), 200

@food_bp.route('/labels/<int:label_id>', methods=['DELETE'])
@login_required
def delete_food_photo_labels(photo_id,label_id):
    print('Deleting label?')
    label = database.FoodPhotoLabel.query \
            .filter_by(id=label_id) \
            .filter_by(user_id=current_user.get_id()) \
            .one()
    database.db_session.delete(label)
    database.db_session.flush()
    database.db_session.commit()

    return json.dumps({'message': 'Success?', 'id': label.id}), 200

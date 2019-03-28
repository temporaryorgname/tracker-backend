from collections import defaultdict
from sqlalchemy.sql import func, or_, and_, not_
import datetime
import os
from PIL import Image
from io import BytesIO
import base64
import boto3

from flask import current_app as app

from fitnessapp import database

s3 = boto3.resource('s3')
if 'LOGS_PHOTO_BUCKET_NAME' in os.environ:
    PHOTO_BUCKET_NAME = os.environ['LOGS_PHOTO_BUCKET_NAME']
else:
    PHOTO_BUCKET_NAME = 'dev-hhixl-food-photos-700'

def food_to_dict(food, with_photos=False, with_children_ids=False, with_children_data=False):
    """ Convert a food entry to a dictionary, along with a list of photo IDs, and children
    """
    output = food.to_dict()

    # Add photo data
    if with_photos:
        photo_ids = database.Photo.query \
                .with_entities(
                        database.Photo.id
                )\
                .filter_by(user_id=food.user_id) \
                .filter_by(food_id=food.id) \
                .all()
        output['photo_ids'] = [x[0] for x in photo_ids]

    # Add children data
    if with_children_ids:
        children = database.Food.query \
                .filter_by(user_id=food.user_id) \
                .filter_by(parent_id=food.id) \
                .all()
        output['children_ids'] = [
            c.id for c in children
        ]
    if with_children_data:
        children = database.Food.query \
                .filter_by(user_id=food.user_id) \
                .filter_by(parent_id=food.id) \
                .all()
        output['children'] = [
            food_to_dict(c, with_photos, with_children_ids, with_children_data) for c in children
        ]

    return output

def update_food_from_dict(data, user_id, parent=None):
    """ Parse a dictionary representing a food entry and return make the appropriate updates in the database
    Args:
        data: dictionary representing the food entry.
            children: children food entries of the same format as `data`
            photo_ids: a list containing IDs of photos associated with this entry.
        user_id: User who owns these entries
        parent_id: ID of the food entry that is parent to the entry represented by `data`.
    """
    # If editing an existing entry, load it up. Otherwise, create a new entry.
    if 'id' in data and data['id'] is not None:
        f = database.Food.query \
            .filter_by(id = data['id']) \
            .filter_by(user_id=user_id) \
            .first()
        f.update_from_dict(data)
    else:
        f = database.Food.from_dict(data)
        f.user_id = user_id
        database.db_session.add(f)
        database.db_session.flush()

    if parent is not None:
        f.parent_id = parent.id
        f.date = parent.date

    if 'photo_ids' in data:
        # Unset food id
        if f.id is not None:
            photos = database.Photo.query \
                    .filter_by(food_id=f.id) \
                    .filter(not_(database.Photo.id.in_(data['photo_ids']))) \
                    .all()
            for p in photos:
                p.food_id = None
        # Set food id
        photos = database.Photo.query \
                .filter(database.Photo.id.in_(data['photo_ids'])) \
                .all()
        for p in photos:
            if p.food_id is not None and p.food_id != f.id:
                raise Exception('Photo %d is already assigned to diet entry %d. Cannot reassign.' % (p.id, p.food_id))
            p.food_id = f.id

    database.db_session.flush()

    ids = [int(f.id)]

    # Parse children
    if 'children' in data:
        for child in data['children']:
            ids += update_food_from_dict(child, user_id, parent=f)

    # Commit once when everything is done.
    if parent is None:
        database.db_session.commit()

    return ids

def delete_food(food, depth=0):
    """ Delete a food entry along with all children recursively.
    """
    children = database.Food.query \
                .filter_by(parent_id=food.id) \
                .all()
    for c in children:
        delete_food(c, depth=depth+1)

    database.db_session.delete(food)
    database.db_session.flush()

    if depth == 0:
        database.db_session.commit()

def search_food_frequent(search_term, user_id):
    """ Search the user's history for the search term, ordered by frequency.
    Food items that have been logged more often will appear first.
    """
    foods = database.Food.query \
            .with_entities(
                    func.mode().within_group(database.Food.name),
                    database.Food.quantity,
                    database.Food.calories,
                    database.Food.protein,
                    func.count('*'),
                    func.max(database.Food.date)
            ) \
            .filter_by(user_id=user_id) \
            .filter(not_(database.Food.name == '')) \
            .filter(database.Food.name.ilike('%{0}%'.format(search_term))) \
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

    return [to_dict(f) for f in foods]

def search_food_recent(search_term, user_id):
    """ Search the user's history for the search term and return the five most recent matching entries.
    """
    foods = database.Food.query \
            .filter_by(user_id=user_id) \
            .filter(database.Food.name.ilike('%{0}%'.format(search_term))) \
            .order_by(database.Food.date.desc()) \
            .limit(5) \
            .all()
    return [food_to_dict(f, with_children_data=True) for f in foods]

def search_food_premade(search_term, user_id):
    """ Search the user's history for the search term and return the five most recent matching entries.
    """
    foods = database.Food.query \
            .filter_by(user_id=user_id) \
            .filter(database.Food.premade == True) \
            .filter(or_(database.Food.finished == False, database.Food.finished == None)) \
            .filter(database.Food.name.ilike('%{0}%'.format(search_term))) \
            .order_by(database.Food.date.desc()) \
            .all()
    return [food_to_dict(f, with_children_data=True) for f in foods]


def get_photo_file_name(photo_id, format='png', size=32):
    filename = str(photo_id)
    fp = database.Photo.query \
            .filter_by(id=photo_id) \
            .one()
    if fp is None:
        raise Exception("File ID not found.")

    local_file_name = os.path.join(
                app.config['UPLOAD_FOLDER'],
                '%s-%s'%(fp.file_name, size))
    def get_Local_image(size):
        try:
            return Image.open(local_file_name)
        except Exception:
            print('Failed to load tiny thumbnail locally for file %s.' % filename)
    def get_s3_image(size):
        filename = os.path.join(
                app.config['UPLOAD_FOLDER'],
                '%s-700'%(fp.file_name))
        filename_resized = local_file_name
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
        raise Exception(
            'Unable to retrieve file %s.' % filename
        )

    return local_file_name

def get_photo_data_base64(photo_id, format='png', size=32):
    file_name = get_photo_file_name(photo_id, format, size)
    with open(file_name, 'rb') as f:
        img = Image.open(f)
    buffered = BytesIO()
    img.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue())
    return img_str.decode()

def save_photo_data(file, file_name, delete_local=True):
    print('saving file ', file_name)
    # Save file
    file_name_original = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    file_name_700 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-700' % file_name)
    file_name_32 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-32' % file_name)
    file.save(file_name_original)
    # Resize photo
    img = Image.open(file_name_original)
    # Remove transparency if there's an alpha channel
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        print('Found transparency. Processing alpha channels.')
        alpha = img.split()[3]
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=alpha)
        img = background
    # Save smaller image
    img.thumbnail((700,700))
    img.save(file_name_700, 'jpeg') 
    # Upload small image to AWS
    with open(file_name_700, 'rb') as data:
        s3.Bucket(PHOTO_BUCKET_NAME).put_object(Key=file_name, Body=data)
    # Resize to tiny thumbnail size
    img.thumbnail((32,32))
    img.save(file_name_32, 'jpeg') 
    # Delete large local files
    if delete_local:
        os.remove(file_name_original)
        os.remove(file_name_700)

def get_photo_exif(file_name):
    # Save file
    file_name_original = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    img = Image.open(file_name_original)
    return img._getexif()

def photo_to_dict(photo, with_data=False, photo_size=32):
    output = photo.to_dict()
    if with_data:
        output['file_url'] = '/data/photos/%d/file' % photo.id
    return output

def delete_photo(photo, commit=True):
    # Get food entries that reference this photo and remove the reference
    food = database.Food().query \
            .filter_by(photo_id = photo.id) \
            .all()
    for f in food:
        f.photo_id = None
    database.db_session.delete(photo)
    database.db_session.flush()
    if commit:
        database.db_session.commit()


def autogoup_photos(photo_ids):
    # Group by time taken and photo similarity
    pass

def autogenerate_food_entry(photos):
    """ Given a list of photos, create a food entry to go with it """
    # Get photo date and data
    date = photos[0].date
    user_id = photos[0].user_id
    photo_id = photos[0].id
    if len(photos) > 1:
        photo_id = None
    # Check that date and user id matches for all photos
    for p in photos:
        if p.date != date:
            raise Exception('Photos were not taken on the same date.')
        if p.user_id != user_id:
            raise Exception('Photos do not belong to the same user.')
    # Pass through classifiers or object detectors and see if it matches with any known foods
    # Create appropriate entry
    food = database.Food()
    food.name = 'Unknown'
    food.date = date
    food.user_id = user_id
    food.photo_id = photo_id
    database.db_session.add(food)
    database.db_session.flush()
    for p in photos:
        p.food_id = food.id
    database.db_session.flush()
    database.db_session.commit()
    print('Creating food entry', food.id)

def autogenerate_food_entry_for_date(date):
    # TODO
    pass

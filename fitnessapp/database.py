from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import Column, Integer, String

import os

if 'LOGS_DB_URI' in os.environ:
    db_uri = os.environ['LOGS_DB_URI']
else:
    db_uri = 'postgresql://howardh:verysecurepassword@localhost:5432/howardh'
print('Initialized DB at %s' % db_uri)
engine = create_engine(db_uri, convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def cast_none(val, t):
    if val is None:
        return None
    return t(val)

class Food(Base):
    __tablename__ = 'food'
    id = Column(Integer, primary_key=True)
    user_id = Column()
    date = Column()
    time = Column()
    name = Column()
    quantity = Column()
    calories = Column()
    protein = Column()
    parent_id = Column()

    def to_dict(self):
        def get_photos(food_id):
            photos = FoodPhoto.query \
                    .filter_by(food_id = food_id) \
                    .all()
            return [p.id for p in photos]
        return {
            "id": self.id, 
            "date": str(self.date),
            "name": self.name, 
            "quantity": self.quantity,
            "calories": cast_none(self.calories, float),
            "protein": cast_none(self.protein, float),
            "photos": get_photos(self.id)
        }

class FoodPhoto(Base):
    __tablename__ = 'food_photos'
    id = Column(Integer, primary_key=True)
    food_id = Column()
    file_name = Column()
    user_id = Column()
    date = Column()
    time = Column()
    upload_time = Column()

    def to_dict(self):
        return {
            "id": self.id, 
            "food_id": self.food_id,
            "user_id": self.user_id,
            "date": cast_none(self.date, str)
        }

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    user_id = Column()
    parent_id = Column()
    tag = Column()
    description = Column()

class FoodPhotoLabel(Base):
    __tablename__ = 'food_photo_labels'
    id = Column(Integer, primary_key=True)
    user_id = Column()
    photo_id = Column()
    tag_id = Column()
    bounding_box = Column()
    bounding_polygon = Column()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column()
    email = Column()
    password = Column()
    last_activity = Column()
    verified_email = Column()
    active = False
    authenticated = False

    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

class Bodyweight(Base):
    __tablename__ = 'body'
    id = Column(Integer, primary_key=True)
    user_id = Column()
    date = Column()
    time = Column()
    bodyweight = Column()

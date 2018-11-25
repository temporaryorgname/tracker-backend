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

class FoodPhoto(Base):
    __tablename__ = 'food_photos'
    id = Column(Integer, primary_key=True)
    food_id = Column()
    file_name = Column()

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

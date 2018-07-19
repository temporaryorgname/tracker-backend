from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import Column, Integer, String

engine = create_engine('postgresql://howardh:verysecurepassword@localhost:5432/howardh', convert_unicode=True)
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
    name = Column()
    quantity = Column()
    quantity_unit = Column()
    calories = Column()
    protein = Column()

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

from flasgger import Swagger
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import tracker_database

cors = CORS()
swagger = Swagger()
login_manager = LoginManager()
db = SQLAlchemy(metadata=tracker_database.Base.metadata)

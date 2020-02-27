import config
import flask
from flask_sqlalchemy import SQLAlchemy

#import models
#import views


app = flask.Flask(__name__)
app.config.from_object(config)

SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/o365oauthtoken'


db = SQLAlchemy(app)


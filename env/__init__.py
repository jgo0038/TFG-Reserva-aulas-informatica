import config
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
#import models
#import views


app = flask.Flask(__name__)
app.config.from_object(config)
Bootstrap(app)
#SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/o365oauthtoken'


db = SQLAlchemy(app)


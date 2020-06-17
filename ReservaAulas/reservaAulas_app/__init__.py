import os
import flask
# from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from sqlalchemy import create_engine
from flask_wtf import CSRFProtect
import logging

app = flask.Flask(__name__)

app.config['SECRET_KEY'] = 'hard to guess string'
# app.secret_key = os.environ.get('SECRET_KEY')
app.jinja_env.globals['ADMIN_USERS'] = ('gestCalendar@outlook.com')

try:
    logging.basicConfig(filename='log_web_app.log', format='[|%(asctime)s| - %(name)s - %(levelname)s] - %(message)s', level=logging.INFO)
    logging.info('\n')
    logging.info('|--------------------|')
    logging.info('|INICIO DE LA WEB APP|')
    logging.info('| -  Jorge Gomez   - |')
    logging.info('|--------------------|')
    logging.info('Inicio de la aplicacion')
except Exception as ex:
    logging.warning('Fallo en la conexion: ' + ex)
# BASEDIR = os.path.abspath(os.path.dirname(__file__))
# SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/outlook'
# app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
csrf = CSRFProtect(app)
csrf.init_app(app)
# app.config.from_object(Config)
Bootstrap(app)
# engine = create_engine('mysql://root:password@localhost/outlook')
# connection = engine.raw_connection()
db = SQLAlchemy(app)
db.init_app(app)
with app.app_context():
    db.create_all()

# app.run(port=8115)

from . import db
from flask_sqlalchemy import SQLAlchemy
from reservaAulas_app.oauth_helpers import (
    datetime_from_timestamp,
    refresh_oauth_token
)
import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String, nullable=False)
    refresh_token = db.Column(db.String, nullable=False)
    email = db.Column(db.String, index=True, unique=True, nullable=False)
    expires_on = db.Column(db.DateTime, nullable=False)

class Tipos(db.Model):
    id_tipo = db.Column(db.String, primary_key = True)
    descripcion = db.Column(db.String, nullable = False)

    aulasTipo = db.relationship('Aulas', backref='tipoAula')

class Edificios(db.Model):
    id_edificio = db.Column(db.String, primary_key = True)
    nombre = db.Column(db.String, nullable = False)

    aulasEdificio = db.relationship('Aulas', backref='edifAula')


class Eventos(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    aula = db.Column(db.String, db.ForeignKey('aulas.nombre'), nullable = False)
    evento = db.Column(db.String, nullable = False)
    email = db.Column(db.String, unique = True, nullable = False)
    inicio = db.Column(db.DateTime, nullable = False)
    fin = db.Column(db.DateTime, nullable = False)
    creacion = db.Column(db.DateTime, nullable = False)

#Tabla relacion many to many entre aulas y propietarios
responsables = db.Table('responsables',
    db.Column('nombre', db.String(45), db.ForeignKey('aulas.nombre')),
    db.Column('id_propietario', db.String(45), db.ForeignKey('propietarios.id_propietario'))
)

class Propietarios(db.Model):
    id_propietario = db.Column(db.String, primary_key = True)
    descripcion = db.Column(db.String, nullable = False)
    responsable = db.Column(db.String, nullable = False)
    email = db.Column(db.String, nullable = False)

    aulasPropietario = db.relationship('Aulas', secondary=responsables, backref='propietarioAula')
    
class Aulas(db.Model):
    nombre = db.Column(db.String, primary_key = True)
    edificio = db.Column(db.String,db.ForeignKey('edificios.id_edificio'), nullable = False)
    tipo = db.Column(db.String,db.ForeignKey('tipos.id_tipo'), unique = True, nullable = False)
    capacidad = db.Column(db.Integer, nullable = False)
    propietario = db.Column(db.String,db.ForeignKey('propietarios.id_propietario'), nullable = False)
    
    eventosAula = db.relationship('Eventos', backref='aulas')

class Auditoria(db.Model):
    id_auditoria = db.Column(db.String, primary_key=True)
    id_evento = db.Column(db.Integer, nullable = False)
    usuario = db.Column(db.String, nullable = False)
    fecha_modif = db.Column(db.DateTime, nullable = False)
    identificador = db.Column(db.String, nullable = False)

def init_db():
    db.create_all()

if __name__ == '__main__':
    init_db()

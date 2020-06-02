from flask_wtf import FlaskForm
from wtforms import TextField, SubmitField, DateTimeField, SelectField, validators, IntegerField, StringField
from wtforms.fields.html5 import DateField, EmailField
from wtforms.validators import InputRequired, ValidationError

class createEventForm(FlaskForm):
    selectAula = SelectField('Selecciona aula')
    subject = TextField('Tema', validators = [InputRequired(message='Introduce un tema')])
    teacher = TextField('Nombre profesor', validators = [InputRequired(message='Introduce un nombre de un profesor')])
    email = EmailField('Email del profesor')
    startDate = DateField('Fecha inicio', validators = [InputRequired(message='Elige un fecha')])
    endDate = DateField('Fecha fin')
    day = SelectField('Selecciona día de la semana')
    startTime = DateTimeField('Hora inicio (HH:MM)',validators = [InputRequired(message='Introduce una hora')],format='%H:%M')
    endTime = DateTimeField('Hora fin (HH:MM)',validators = [InputRequired(message='Introduce una hora')],format='%H:%M')
    submit = SubmitField('Crear evento')
    
    def validate_endTime(self, form):
        if self.startTime.data and (self.startTime.data >= self.endTime.data):
            raise ValidationError('La hora de inicio no puede ser mayor que la hora final')

class selectGroupCalendar(FlaskForm):
    select = SelectField('Selecciona grupo de aulas')
    submit = SubmitField('Mostrar aulas')

class selectCalendar(FlaskForm):
    select = SelectField('Selecciona aula')
    submit = SubmitField('Mostrar eventos')

class createNewAula(FlaskForm):
    edificio = SelectField('Selecciona el edificio')
    nombreAula = TextField('Nombre del aula', validators = [InputRequired(message='Introduce un nombre para el aula')])
    tipo = SelectField('Tipo de aula')
    capacidad = IntegerField('Capacidad del aula', validators = [InputRequired(message='Introduce una capacidad del aula')])
    n_ordenadores = IntegerField('Numero de ordenadores', validators = [InputRequired(message='Introduce un numero de ordenadores (si no tiene, indique 0)')])
    propietario = SelectField('Propietario del aula')

class filterAulasForm(FlaskForm):
    capacidad = SelectField('Selecciona la capacidad del aula')
    n_ord = IntegerField('Selecciona el numero de ordenadores', validators = [InputRequired(message='Introduce una capacidad del aula')])
    edificio = SelectField('Selecciona el edificio')
    tipo = SelectField('Selecciona el tipo de aula')

class modificarAulasForm(FlaskForm):
    edificio = SelectField('Selecciona el edificio')
    nombreAula = TextField('Nombre del aula')
    tipo = SelectField('Tipo de aula')
    capacidad = IntegerField('Capacidad del aula')
    n_ordenadores = IntegerField('Numero de ordenadores')
    propietario = SelectField('Propietario del aula')
    submit = SubmitField('Guardar')
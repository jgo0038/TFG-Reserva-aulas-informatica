from flask_wtf import FlaskForm
from wtforms import TextField, SubmitField, DateTimeField, SelectField, validators, IntegerField, StringField, TimeField
from wtforms.fields.html5 import DateField, EmailField
from wtforms.validators import InputRequired, ValidationError, Email

class createEventForm(FlaskForm):
    selectAula = SelectField('Selecciona aula')
    subject = TextField('Tema', validators = [InputRequired(message='Introduce un tema')])
    teacher = TextField('Nombre profesor', validators = [InputRequired(message='Introduce un nombre de un profesor')])
    email = EmailField('Email del profesor')
    startDate = DateField('Fecha inicio ', validators = [InputRequired(message='Elige un fecha')])
    endDate = DateField('Fecha fin', validators = [InputRequired(message='Elige un fecha')])
    day = SelectField('Selecciona día de la semana', validators = [InputRequired(message='Elige un día')])
    startTime = DateTimeField('Hora inicio (HH:MM)',validators = [InputRequired(message='Introduce una hora')],format='%H:%M')
    endTime = DateTimeField('Hora fin (HH:MM)',validators = [InputRequired(message='Introduce una hora')],format='%H:%M')
    submit = SubmitField('Reservar')
    
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

class filterAulasForm2(FlaskForm):
    select = SelectField('Selecciona aula')
    capacidad = IntegerField('Inserta la capacidad minima del aula')
    n_ord = IntegerField('Inserta el numero minimo de ordenadores')
    tipo = SelectField('Selecciona el tipo de aula')
    startDate = DateField('Fecha inicio *',validators = [InputRequired(message='Introduce una fecha de inicio')])
    endDate = DateField('Fecha fin *',validators = [InputRequired(message='Introduce una fecha limite')])
    startTime = DateTimeField('Hora inicio (HH:MM) *',validators = [InputRequired(message='Introduce una hora')],format='%H:%M')
    endTime = DateTimeField('Hora fin (HH:MM) *',validators = [InputRequired(message='Introduce una hora')],format='%H:%M')
    submit = SubmitField('Mostrar eventos')

class modificarEvent(FlaskForm):
    tema = StringField('Tema')
    user = StringField('Usuario')
    fechaIni = DateTimeField('Fecha inicio',format='%Y-%m-%d %H:%M:%S')
    horaIni = TimeField('Hora inicio (HH:MM)',format='%H:%M')
    horaFin = TimeField('Hora fin (HH:MM)',format='%H:%M')
    submit = SubmitField('Modificar')

class modificarPropietarioForm(FlaskForm):
    id_propietario = StringField('ID')
    descripcion = StringField('Descripcion')
    responsable = StringField('Responsable')
    email = StringField('Email')
    submit = SubmitField('Modificar')

class anadirPropietarioForm(FlaskForm):
    id_propietario = StringField('Identificador', validators = [InputRequired(message='Introduce un ID')])
    descripcion = StringField('Descripcion', validators = [InputRequired(message='Introduce una descripción')])
    responsable = StringField('Responsable', validators = [InputRequired(message='Introduce un responsable')])
    email = StringField('Email', validators = [InputRequired(message='Introduce un email')])
    submit = SubmitField('Crear')

class filtrarHoras(FlaskForm):
    fechaInicio = DateField('Fecha inicio *', validators = [InputRequired(message='Introduce una fecha inicial')])
    fechaFin = DateField('Fecha fin *', validators = [InputRequired(message='Introduce una fecha final')])
    submit = SubmitField('Filtrar')

class filtrarAulas(FlaskForm):
    capacidad = IntegerField('Capacidad')
    n_ord = IntegerField('Número de ordenadores')
    submit = SubmitField('Filtrar')
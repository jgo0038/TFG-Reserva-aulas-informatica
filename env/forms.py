from wtforms import Form
from wtforms import TextField, SubmitField, DateTimeField, SelectField
from wtforms.validators import InputRequired
from wtforms.fields.html5 import DateField

class createEventForm(Form):
    selectCalendar = SelectField('Selecciona calendario')
    subject = TextField('Tema')
    start = DateTimeField('Fecha inicio')
    end = DateTimeField('Fecha fin')
    submit = SubmitField('Crear evento')

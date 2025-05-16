from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SubmitField


class UploadImageForm(FlaskForm):
    image = FileField('Выберите фото', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения')])
    submit = SubmitField('Загрузить')

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired


class CategoryForm(FlaskForm):
    name = StringField("Название категории", validators=[DataRequired()])
    type = SelectField("Тип", choices=[("income", "Доход"), ("expense", "Расход")], validators=[DataRequired()])
    submit = SubmitField("Добавить")

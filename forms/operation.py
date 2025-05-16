import datetime
from flask_wtf import FlaskForm
from wtforms import FloatField, DateTimeField, StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, InputRequired


class OperationForm(FlaskForm):
    date = DateTimeField("Дата", format='%Y-%m-%d %H:%M:%S',
                         validators=[DataRequired(message="Укажите дату операции")],
                         default=datetime.datetime.now)
    amount = FloatField("Сумма", validators=[InputRequired(message="Введите сумму (число)")])
    category = SelectField("Категория", coerce=int, validators=[DataRequired()])
    type = SelectField("Тип операции", choices=[("income", "Доход"), ("expense", "Расход")], validators=[DataRequired()])
    description = StringField("Описание")
    submit = SubmitField("Добавить операцию")

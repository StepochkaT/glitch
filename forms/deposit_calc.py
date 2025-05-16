import datetime
from flask_wtf import FlaskForm
from wtforms import DateTimeField, SelectField, SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired, NumberRange


class DepositCalculatorForm(FlaskForm):
    name = StringField("Имя вклада", validators=[DataRequired()])
    date = DateTimeField("Дата открытия", default=datetime.datetime.now, format='%Y-%m-%d')
    amount = IntegerField("Сумма", validators=[DataRequired(), NumberRange(min=1)])
    term = IntegerField("Срок вклада", default=1, validators=[DataRequired(), NumberRange(min=1)])
    type_term = SelectField("Тип вклада", choices=[("year", "Год"), ("month", "Месяц")],
                            validators=[DataRequired()])
    percent = IntegerField("Процентная ставка", default=5, validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Рассчитать")
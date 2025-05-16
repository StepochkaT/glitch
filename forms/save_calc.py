import datetime
from flask_wtf import FlaskForm
from wtforms import DateTimeField, SelectField, SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired, NumberRange


class SavingsCalculatorForm(FlaskForm):
    name = StringField("Название цели", validators=[DataRequired()])
    date = DateTimeField("Дата начала", default=datetime.datetime.now, format='%Y-%m-%d')
    amount = IntegerField("Сумма", validators=[DataRequired(), NumberRange(min=1)])
    payment_type = SelectField("Сколько нужно откладывать каждый",
                               choices=[("day", "день"), ("week", "неделю"), ("month", "месяц")],
                               validators=[DataRequired()])
    quantity = IntegerField("В течении", validators=[DataRequired(), NumberRange(min=1)])
    type_repayment = SelectField(choices=[("month", "Месяц/месяцев"), ("year", "Год/лет")], validators=[DataRequired()])
    submit = SubmitField("Рассчитать")
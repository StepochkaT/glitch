import datetime
from flask_wtf import FlaskForm
from wtforms import DateTimeField, SelectField, SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired, NumberRange


class CreditCalculatorForm(FlaskForm):
    name = StringField("Имя кредита", validators=[DataRequired()])
    date = DateTimeField("Дата выдачи", default=datetime.datetime.now, format='%Y-%m-%d')
    amount = IntegerField("Сумма кредита/займа", validators=[DataRequired(), NumberRange(min=1)])
    percent = IntegerField("Процентная ставка", default=5, validators=[DataRequired(), NumberRange(min=1)])
    term = IntegerField("Срок кредита", default=3, validators=[DataRequired(), NumberRange(min=1)])
    type_term = SelectField('ㅤ', choices=[("year", "Год"), ("month", "Месяц")],
                            validators=[DataRequired()])
    submit = SubmitField("Рассчитать")
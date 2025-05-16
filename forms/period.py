from flask_wtf import FlaskForm
from wtforms import HiddenField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional


class PeriodForm(FlaskForm):
    date_range = HiddenField()
    operation_type = SelectField(
        'Тип операции',
        choices=[('all', 'Все'), ('income', 'Доходы'), ('expense', 'Расходы')],
        default='all',
        validators=[DataRequired()]
    )
    category = SelectField('Категория', choices=[('all', 'Все')], default='all', validators=[Optional()])
    submit = SubmitField("Подтвердить")

from flask_wtf import FlaskForm
from wtforms import SubmitField

class BudgetForm(FlaskForm):
    submit = SubmitField("Сохранить бюджет")

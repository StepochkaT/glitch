from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField, EmailField
from wtforms.validators import DataRequired


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    username = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


from wtforms.validators import DataRequired, Email, EqualTo, Length


class NameChangeForm(FlaskForm):
    username = StringField("Новое имя", validators=[DataRequired(), Length(min=3, max=32)])


class PasswordStepOneForm(FlaskForm):
    current_password = PasswordField("Текущий пароль", validators=[DataRequired()])


class PasswordStepTwoForm(FlaskForm):
    new_password = PasswordField("Новый пароль", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Изменить пароль')

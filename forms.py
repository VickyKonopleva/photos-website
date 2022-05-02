from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField

##WTForm
class AddPhotoForm(FlaskForm):
    photo_title = StringField("Название", validators=[DataRequired()])
    photo_place = StringField("Где сделано фото", validators=[DataRequired()])
    img_url = StringField("Ссылка URL на фото", validators=[DataRequired(), URL()])
    submit = SubmitField("Добавить фото!")

class RegisterForm(FlaskForm):
    first_name=StringField("Имя", validators=[DataRequired()])
    last_name = StringField("Фамилия", validators=[DataRequired()])
    department = StringField("Филиал", validators=[DataRequired()])
    email=StringField("Email", validators=[DataRequired()])
    password=PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Зарегистрироваться!")

class LoginForm(FlaskForm):
    email = StringField("Ваш E-mail", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти!")

class CommentForm(FlaskForm):
    body = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Comment it!")


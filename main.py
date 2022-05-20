import random

from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import AddPhotoForm, RegisterForm, LoginForm, CommentForm, EditPhotoForm
from flask_gravatar import Gravatar
from functools import wraps
import os

#конфигурация
login_manager=LoginManager()
Base = declarative_base()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL.replace('postgres://', 'postgresql://', 1)", "sqlite:///north_photos_project.db")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


#Конфигурация баз данных

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    first_name = db.Column(db.String(1000))
    last_name = db.Column(db.String(1000))
    department = db.Column(db.String(1000))
    photos = relationship("Photo", back_populates="photo_author")
    comments=relationship("Comment", back_populates="comment_author")
    votes_given=relationship("Vote", back_populates="voting_user")

class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('user.id'))
    photo_author = relationship("User", back_populates="photos")
    photo_title = db.Column(db.String(250), nullable=False)
    photo_place = db.Column(db.String(500), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_photo")
    votes = relationship("Vote", back_populates="parent_photo")

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    photo_id = Column(Integer, ForeignKey('photos.id'))
    parent_photo = relationship("Photo", back_populates="comments")
    author_id = Column(Integer, ForeignKey('user.id'))
    comment_author = relationship("User", back_populates="comments")
    comment_text = db.Column(db.Text, nullable=False)

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('user.id'))
    voting_user = relationship("User", back_populates="votes_given")
    photo_id = Column(Integer, ForeignKey('photos.id'))
    parent_photo = relationship("Photo", back_populates="votes")
    like = db.Column(Integer())


# db.create_all()

#логин_менеджер
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#загрузить домашнюю страницу со всеми фото
@app.route('/')
def get_all_photos():
    photos = Photo.query.all()
    return render_template("index.html" , photos = sorted(photos, key=lambda photo: len(photo.votes), reverse=True))

#проголосовать за фото
@app.route('/vote')
def vote_for_photo():
    # получить выбранное фото из базы данных
    photo_id = request.args.get('photo_id')
    requested_photo = Photo.query.get(photo_id)
    # загрузить новый голос в базу
    new_vote= Vote(
        voting_user = current_user,
        parent_photo = requested_photo,
        like=1
    )
    db.session.add(new_vote)
    db.session.commit()
    return redirect(url_for('get_all_photos'))

# войти на сайт под своей учетной записью
@app.route('/login', methods=["POST", "GET"])
def login():
    # форма для входа в свую учетную запись
    form=LoginForm()
    # действия по проверке введенных пользователем в форму данных (сверка их с данными из базы)
    # если введенный логин-пароль совпадают, то успешный вход, иначе - предупреждение flash об ошибке
    if form.validate_on_submit():
        user_emal = form["email"].data
        user_password = form["password"].data
        user=db.session.query(User).filter_by(email=user_emal).first()
        if user:
            if check_password_hash(user.password, user_password):
                login_user(user)
                return redirect(url_for('get_all_photos'))
            else:
                flash("Неправильный пароль")
        else:
            flash("Пользователя с таким e-mail не существует")
    return render_template("login.html", form=form)

# зарегистрировать нового пользователя
@app.route('/register', methods=["POST", "GET"])
def register():
    # регистрационная форма
    form=RegisterForm()
    # создание нового пользователся в базе данных
    if form.validate_on_submit():
        user_first_name=form["first_name"].data
        user_last_name = form["last_name"].data
        user_departmnet = form["department"].data
        user_password=form["password"].data
        user_emal = form["email"].data
        # проверка, не сущетвует ли уже в базе пользователь с таким же email
        if not db.session.query(User).filter_by(email=user_emal).first():

            new_user=User( first_name=user_first_name,
                           last_name = user_last_name,
                           department = user_departmnet,
                           email=user_emal,
                           password=generate_password_hash(user_password, method='pbkdf2:sha256', salt_length=8)
                          )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_photos'))
        else:
            flash("Пользователь с таким e-mail уже зарегистрирован")
            # return redirect(url_for('login'))
    return render_template("register.html", form=form)

# выход из учетной записи пользователя
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_photos'))

# просмотр фото из ленты
@app.route("/photo", methods=["GET", "POST"])
def view_photo():
    # форма для комментария (!!отключена)
    form = CommentForm()
    # получение из базы данных запрошенного фото
    photo_id = request.args.get('photo_id')
    requested_photo = Photo.query.get(photo_id)
    # перемешивание массива с проголосовавшими за фото пользователями
    votes = sorted(requested_photo.votes, key=lambda voting_user: random.random())
    return render_template("view_photo.html", photo=requested_photo, comment_form = form, votes = votes)

# добавление нового фото
@app.route("/new-photo", methods=["GET", "POST"])
def add_new_photo():
    # форма для добавления фото
    form = AddPhotoForm()
    # добавление фото в базу данных
    if form.validate_on_submit():
        new_photo = Photo(
            photo_title=form.photo_title.data,
            photo_place=form.photo_place.data,
            img_url=form.img_url.data,
            photo_author=current_user,
            date=date.today().strftime("%d.%m.%Y")
        )
        db.session.add(new_photo)
        db.session.commit()
        return redirect(url_for("get_all_photos"))
    return render_template("make-photo.html", form=form)

# декоратор для доступа к редактированию и удалению фото только для админа и автора фото
def admin_and_author_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        photo_id = request.args.get('photo_id')
        photo = Photo.query.get(photo_id)
        if not current_user.is_authenticated or (photo.photo_author.id != current_user.id and current_user.id != 1) :
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# редактирование фото (доступно только для автора и админа фото)
@app.route("/edit-photo", methods=["GET", "POST"])
@admin_and_author_only
def edit_photo():
    # запрос к базе данных для получения фото для редактирования
    photo_id = request.args.get('photo_id')
    photo_to_edit = Photo.query.get(photo_id)
    # форма для редактирования фото
    edit_form = EditPhotoForm(
        photo_title=photo_to_edit.photo_title,
        photo_place=photo_to_edit.photo_place,
    )
    # загрузить исправленные данные по фото в базу данных
    if edit_form.validate_on_submit():
        photo_to_edit.photo_title = edit_form.photo_title.data
        photo_to_edit.photo_place = edit_form.photo_place.data
        db.session.commit()
        return redirect(url_for("view_photo", photo_id=photo_to_edit.id))

    return render_template("make-photo.html", form=edit_form, is_edit=True)

# удалить фото (доступно только для автора и админа фото)
@app.route("/delete_photo",  methods=["GET", "POST"])
@admin_and_author_only
def delete_photo():
    # запросить у базы данных фото для удаления
    photo_id = request.args.get('photo_id')
    photo_to_delete = Photo.query.get(photo_id)
    # удалить запрошенное фото
    db.session.delete(photo_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_photos'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


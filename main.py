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
from forms import AddPhotoForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os


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


##CONFIGURE TABLES

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def get_all_photos():
    photos = Photo.query.all()
    return render_template("index.html" , photos = photos)

@app.route('/pho')
def get_land():
    requested_photo = Photo.query.get(1)
    return render_template("view_photo.html", photo=requested_photo)

@app.route('/vote')
def vote_for_photo():
    photo_id = request.args.get('photo_id')
    requested_photo = Photo.query.get(photo_id)
    photo_likes = requested_photo.votes
    # if photo_likes == None:
    #     photo_likes = 0
    new_vote= Vote(
        voting_user = current_user,
        parent_photo = requested_photo,
        like=1
    )
    db.session.add(new_vote)
    db.session.commit()
    return redirect(url_for('get_all_photos'))

# @app.route("/about")
# def about():
#     return render_template("about.html")
#
#
# @app.route("/contact")
# def contact():
#     return render_template("contact.html")

@app.route('/login', methods=["POST", "GET"])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        user_emal = form["email"].data
        user_password = form["password"].data
        user=db.session.query(User).filter_by(email=user_emal).first()
        if user:
            if check_password_hash(user.password, user_password):
                login_user(user)
                return redirect(url_for('get_all_photos'))
            else:
                print("Invalid password")
                flash("Invalid password")
        else:
            flash("User doesn't exist")
            print("User doesn't exist")
    return render_template("login.html", form=form)

@app.route('/register', methods=["POST", "GET"])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        user_first_name=form["first_name"].data
        user_last_name = form["last_name"].data
        user_departmnet = form["department"].data
        user_password=form["password"].data
        user_emal = form["email"].data
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
            print("Ooops")
            flash("User already exists")
            # return redirect(url_for('login'))
    return render_template("register.html", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_photos'))


@app.route("/photo", methods=["GET", "POST"])
def view_photo():
    photo_id = request.args.get('photo_id')
    requested_photo = Photo.query.get(photo_id)
    return render_template("view_photo.html", photo=requested_photo)


@app.route("/new-post", methods=["GET", "POST"])
# @admin_only
def add_new_photo():
    form = AddPhotoForm()
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


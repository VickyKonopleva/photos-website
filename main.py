from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os
import psycopg2


login_manager=LoginManager()
# class for parent-child relationships between tables
Base = declarative_base()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager.init_app(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

##CONNECT TO DB
#'DATABASE_URL' set as a local env var
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments=relationship("Comment", back_populates="comment_author")

class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('user.id'))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('user.id'))
    comment_author = relationship("User", back_populates="comments")
    post_id=Column(Integer, ForeignKey('blog_posts.id'))
    parent_post=relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)



#db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        user_name=form["name"].data
        user_password=form["password"].data
        user_emal = form["email"].data
        if not db.session.query(User).filter_by(email=user_emal).first():

            new_user=User( name=user_name,
                          email=user_emal,
                          password=generate_password_hash(user_password, method='pbkdf2:sha256', salt_length=8)
                          )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("User already exists")
            return redirect(url_for('login'))
    return render_template("register.html", form=form)


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
                return redirect(url_for('get_all_posts'))
            else:
                flash("Invalid password")
        else:
            flash("User doesn't exist")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form=CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        new_comment_text=form.body.data
        new_comment=Comment(text=new_comment_text,
                            comment_author=current_user,
                            parent_post=requested_post)
        db.session.add(new_comment)
        db.session.commit()
        return render_template('post.html', post=requested_post, comment_form=form)
    return render_template("post.html", post=requested_post, comment_form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from datetime import datetime
from email.message import EmailMessage
import smtplib
import math
import os

app = Flask(__name__)
app.secret_key = "hello"

params = {
    "admin_user": os.getenv("ADMIN_USER"),
    "admin_pass": os.getenv("ADMIN_PASS"),
    "no_of_posts": int(os.getenv("NO_OF_POSTS", 3)),
}

app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
)

mail = Mail(app)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not set")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)


elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Contacts(db.Model):
        
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(25), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    msg = db.Column(db.String(250), nullable=False)
    datetime = db.Column(db.String(80))

class Codes(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(25))
    content = db.Column(db.String(250))
    slug = db.Column(db.String(50))
    img_file = db.Column(db.String(250))
    datetime = db.Column(db.String(80))

with app.app_context():
    db.create_all()

@app.route("/")
def Home():
    codes = Codes.query.limit(params["no_of_posts"]).all()
    return render_template("index.html", codes=codes)

@app.route("/codes/<string:code_slug>")
def codes(code_slug):
    code = Codes.query.filter_by(slug=code_slug).first_or_404()
    return render_template("codes.html", codes=code, params=params)

@app.route("/codes_list")
def codes_list():
    all_codes = Codes.query.all()
        
    last = math.ceil(len(all_codes) / params["no_of_posts"])
    page = request.args.get("page", 1, type=int)

    start = (page - 1) * params["no_of_posts"]
    end = start + params["no_of_posts"]
    codes = all_codes[start:end]

    prev = "#" if page <= 1 else url_for("codes_list", page=page - 1)
    next = "#" if page >= last else url_for("codes_list", page=page + 1)

    return render_template("codes_list.html", codes=codes, prev=prev, next=next)

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if "user" in session and session["user"] == params["admin_user"]:
        codes = Codes.query.all()
        return render_template("admin_panel.html", codes=codes)

    if request.method == "POST":
        if (
            request.form.get("uname") == params["admin_user"]
            and request.form.get("pass") == params["admin_pass"]
        ):
            session["user"] = params["admin_user"]
            return redirect("/admin")

    return render_template("login.html", params=params)

@app.route("/edit/<string:sno>", methods=["GET", "POST"])
def edit(sno):
    if "user" not in session:
        return redirect("/admin")

    if request.method == "POST":
        title = request.form.get("box_title")
        content = request.form.get("box_content")
        slug = request.form.get("box_slug")
        img = request.form.get("box_img_file")

        if sno == "0":
            post = Codes(
                title=title,
                content=content,
                slug=slug,
                img_file=img,
                datetime=str(datetime.now()),
            )
            db.session.add(post)
        else:
            post = Codes.query.get_or_404(sno)
            post.title = title
            post.content = content
            post.slug = slug
            post.img_file = img
            post.datetime = str(datetime.now())

        db.session.commit()
        return redirect("/admin")

    post = None if sno == "0" else Codes.query.get_or_404(sno)
    return render_template("edit.html", code=post, params=params)

@app.route("/delete/<string:sno>")
def delete(sno):
    if "user" in session:
        post = Codes.query.get_or_404(sno)
        db.session.delete(post)
        db.session.commit()
    return redirect("/admin")

@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    subject = request.form.get("subject")
    message = request.form.get("message")

    entry = Contacts(
        name=name,
        email=email,
        subject=subject,
        msg=message,
        datetime=str(datetime.now()),
    )
    db.session.add(entry)
    db.session.commit()

    msg = EmailMessage()
    msg["Subject"] = f"New Message From {name}"
    msg["From"] = os.getenv("MAIL_USERNAME")
    msg["To"] = os.getenv("MAIL_USERNAME")
    msg.set_content(f"Email: {email}\n\n{message}")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.getenv("MAIL_USERNAME"),
            os.getenv("MAIL_PASSWORD"),
        )
        smtp.send_message(msg)

    return redirect(url_for("Home"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/admin")

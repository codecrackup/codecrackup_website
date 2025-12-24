from flask import Flask, render_template, request , redirect , url_for ,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from flask_mail import Mail
import math
import smtplib
from email.message import EmailMessage
import os
from sqlalchemy import inspect



params={
        "admin_user": os.getenv("ADMIN_USER"),
        "admin_pass": os.getenv("ADMIN_PASS"),
        "no_of_posts": os.getenv("NO_OF_POSTS",3),

}
app = Flask(__name__)

mail=Mail(app)






app.secret_key='hello'
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD")
)








import os

db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise RuntimeError("DATABASE_URL is not set. Check Render environment variables.")

# psycopg3 compatibility
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db=SQLAlchemy(app)
with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("codes"):
        db.create_all()

def ensure_tables():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("codes"):
            db.create_all()
ensure_tables()

class Contacts(db.Model):
    sno=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(25),nullable=False)
    email=db.Column(db.String(25),nullable=False)
    subject=db.Column(db.String(50),nullable=False)
    msg=db.Column(db.String(250),nullable=False)
    datetime=db.Column(db.String(80),nullable=True)

class Codes(db.Model):
    sno=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(25),nullable=True)
    content=db.Column(db.String(25),nullable=True)
    slug=db.Column(db.String(50),nullable=True)
    img_file=db.Column(db.String(250),nullable=True)
    datetime=db.Column(db.String(80),nullable=True)





@app.route("/")
def Home():
    codes= Codes.query.filter_by().all()[0:params['no_of_posts']]
    
    return render_template('index.html',codes=codes)

@app.route("/edit/<string:sno>",methods=['POST','GET'])
def edit(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        
        if (request.method)=='POST':
            box_title=request.form.get('box_title')
            box_content=request.form.get('box_content')
            box_slug=request.form.get('box_slug')
            box_img_file=request.form.get('box_img_file')
            date=datetime.now()
            if sno=='0':
                code=Codes(title=box_title,content=box_content,slug=box_slug,img_file=box_img_file,datetime=date)                
                db.session.add(code)
                db.session.commit()

            else:
                code= Codes.query.filter_by(sno=sno).first()
                code.title = box_title
                code.slug = box_slug
                code.content = box_content
                code.img_file = box_img_file
                code.date = date
                db.session.commit()
                return redirect('/edit/'+sno)
    code= Codes.query.filter_by(sno=sno).first()
    return render_template('edit.html', params=params,code=code)   
            


    

@app.route("/admin",methods=['GET',"POST"])
def admin_panel():
    if ('user' in session and session['user'] == params['admin_user']):
        codes=Codes.query.all()

        return render_template('admin_panel.html',codes=codes)


    if request.method=='POST':
        USER_NAME= request.form.get('uname')
        PASSWORD= request.form.get('pass')
        if (USER_NAME== params['admin_user'] and PASSWORD== params['admin_pass']):
            session['user']=USER_NAME
            codes=Codes.query.all()
            return render_template('admin_panel.html',codes=codes)
            

    code= Codes.query.filter_by().all()
    return render_template('login.html',params=params ,code=code)

@app.route("/codes/<string:code_slug>", methods=['GET'])
def codes(code_slug):
    codes= Codes.query.filter_by(slug=code_slug).first()
    
    return render_template('codes.html',params=params,codes=codes)


@app.route("/codes_list")
def codes_list():
    codes=Codes.query.all()
    last = math.ceil(len(codes)/int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    codes = codes[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
    if page == 1:
        prev = "#"
        next = url_for('codes_list', page=page + 1)
    elif page==last:
        prev = url_for('codes_list', page=page - 1)
        next = "#"
    else:
        prev = url_for('codes_list', page=page - 1)
        next = url_for('codes_list', page=page + 1)
    return render_template('codes_list.html',codes=codes,prev=prev,next=next)

@app.route("/contact",methods=["POST","GET"])
def contact():
    if (request.method=='POST'):
        # Add entry to database

        name=request.form.get('name')
        email=request.form.get('email')
        subject=request.form.get('subject')
        emsg=request.form.get('message')

        entry=Contacts(name=name,email=email,subject=subject,msg=emsg,datetime=datetime.now())
        db.session.add(entry)
        db.session.commit()
       
        # Create the email
        msg = EmailMessage()
        msg['Subject'] = 'New Message From ' + name
        msg['From'] = 'sonardarshan508@gmail.com'
        msg['To'] = 'codecrackup@gmail.com'
        mail_msg=f"Email={email}\nSubject={subject}\nMessage={emsg}"
        msg.set_content(mail_msg.title())

        # Connect to Gmail's SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(
    os.getenv("MAIL_USERNAME"),
    os.getenv("MAIL_PASSWORD")
)

            smtp.send_message(msg)

        print("Email sent!")
    return redirect(url_for("Home") + "?status=sent#contact")  


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/admin')

@app.route("/delete/<string:sno>")
def delete(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        code=Codes.query.filter_by(sno=sno).first()
        db.session.delete(code)
        db.session.commit()   
    return redirect('/admin')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)






 










from flask import Flask, flash, redirect, render_template, request, \
    url_for, Blueprint, session
from functools import wraps

from dbconnect import connection
import pymysql

from wtforms import Form, BooleanField, TextField, PasswordField, SelectField, \
TextAreaField, SelectMultipleField, validators
from passlib.hash import pbkdf2_sha256
import gc


# create the application object
app = Flask(__name__)
app.secret_key = 'secret'

# use decorators to link the function to a url\

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('login'))

    return wrap

@app.route("/logout/")
@login_required
def logout():
    session.clear()
    flash("You have been logged out!")
    gc.collect()
    return redirect(url_for('login'))
        
class LoginForm(Form):
    username = TextField('Username', [validators.Length(min=4, max=50)])
    password = PasswordField('Password', [validators.Required()])

@app.route('/', methods= ["GET", "POST"])
@app.route('/login', methods= ["GET", "POST"])
def login():
    try:
        form = LoginForm(request.form)
        email = request.form['username']
        password = request.form['password']
        c, conn = connection()

        if request.method == "POST":
            mysql = "SELECT * FROM users WHERE username=%s"
            data = c.execute(mysql, (email,))
            data1 = c.fetchone()[5]
            if pbkdf2_sha256.verify(password, data1):
                session['logged_in'] = True
                session['username'] = email
                c.close()
                conn.close()
                gc.collect()
                return redirect(url_for('profile'))
            else:
                flash("Invalid credentials, please try again")
        gc.collect();

        return render_template("login.html", form=form)

    except Exception as e:
        error = "Invalid credentials, please try again"
        return render_template("login.html", error = error, form=form)


    return render_template('login.html')  # return a string

class RegistrationForm(Form):
   # username = TextField('Username', [validators.Length(min=4, max=20)])
    email = TextField('Email Address',  [validators.Length(min=4, max=50)])
    firstName = TextField("First Name", [validators.Length(min = 2, max= 45)])
    lastName = TextField("Last Name",  [validators.Length(min = 2, max= 45)])
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    year = SelectField(u'Class Year', choices=[('freshman', 'Freshman'), ('soph', "Sophmore"), ('junior', 'Junior'), \
                                               ('senior', 'Senior'), ('graduate', 'Graduate')])
    major = TextField('Major', [validators.Length(min=4, max= 45)])

@app.route('/register', methods= ["GET", "POST"])
def register():
    try:
        form = RegistrationForm(request.form)

        if request.method == "POST" and form.validate():
            email = form.email.data
            first = form.firstName.data
            last = form.lastName.data
            year = form.year.data
            major = form.major.data
            password = pbkdf2_sha256.hash((str(form.password.data)))
            c, conn = connection()

            x = c.execute("SELECT * FROM users WHERE email=%s", (email,))

            if int(x) > 0:
                flash("Account with that email already exists")
                return render_template('register.html', form=form)
            else:
                c.execute("INSERT INTO users (username, email, FirstName, LastName, ClassYear, password, major) \
                    VALUES (%s, %s, %s, %s, %s, %s, %s)", (email, email, first, last, year, password, major))
                conn.commit()
                flash("Registration complete")
                c.close()
                conn.close()
                gc.collect()
           
                return redirect(url_for('login'))
        return render_template('register.html', form=form)

    except Exception as e:
        return(str(e))
     # render a template


class GroupCreateForm(Form):
   # username = TextField('Username', [validators.Length(min=4, max=20)])
    title = TextField('Title', [validators.Length(min=3, max=40)])
    description = TextAreaField('Description', [validators.Required()])
    days = SelectMultipleField(u'Meeting Days', choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), \
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')])
    # times = 


@app.route('/groupcreation', methods= ["GET", "POST"])
@login_required
def creategroup():
    try:
        form = GroupCreateForm(request.form)

        if request.method == "POST" and form.validate():
            createdby = session['username']
            title = form.title.data
            description = form.description.data
            days = form.days.data

            c, conn = connection()

            c.execute("INSERT INTO studydb.group (groupName, Description, createdBy) VALUES (%s, %s, %s)", (title, description, createdby))
            conn.commit()
            data = c.execute("SELECT idgroup FROM studydb.group WHERE createdBy=%s AND groupName=%s", (createdby, title))
            data = list(c.fetchall())
            groupid = data[0]
            for day in days:
                c.execute("INSERT INTO studydb.meetingDays (groupid, day) VALUES (%s, %s)", (groupid[0], day))

            flash(groupid)
            conn.commit()
            flash("Group created successfully")
            c.close()
            conn.close()
            gc.collect()

            return render_template('creategroup.html', form=form)

        return render_template('creategroup.html', form=form)

    except Exception as e:
        return(str(e))

@app.route('/profile')
@login_required
def profile():
    username = session['username']
    c, conn = connection()
    

    mysql = "SELECT * FROM users WHERE username=%s"
    data = c.execute(mysql, (username,))

    row = list(c.fetchall())
    row = row[0]
    firstName = row[2]
    lastName = row[3]
    classYear = row[4]
    major = row[6]
    fullName = firstName + " " + lastName

    c.close()
    conn.close()

    return render_template('profile.html', name=fullName, year=classYear, major=major)

@app.route('/groups', methods=["GET", "POST"])
@login_required
def allGroups():
    c,conn = connection()
    data = c.execute("SELECT * FROM studydb.group")
    groups = list(c.fetchall())
    if request.method == "POST":
        username = session['username']
        groupid = request.form['join']
        data = c.execute("SELECT * FROM studydb.memberOf WHERE username=%s AND groupID=%s", (username, groupid))
        data1 = c.execute("SELECT * FROM studydb.group WHERE idgroup=%s AND createdBy=%s", (groupid, username))
        if int(data) == 0 and int(data1) == 0:
            c.execute("INSERT INTO studydb.memberOf (username, groupID) VALUES (%s, %s)", (username, groupid))
            conn.commit()
            flash("You have joined the group successfully!")
        if data1 > 0:
            flash("You own this group!")
        c.close()
        conn.close()
    return render_template('groups.html', groups=groups)

@app.route('/mygroups', methods=['GET', 'POST'])
@login_required
def myGroups():
    c, conn = connection()
    data = c.execute("SELECT * FROM studydb.group WHERE createdBy=%s", (session['username'],))
    ownedGroups = list(c.fetchall())
    data1 = c.execute("SELECT *  FROM studydb.memberOf WHERE username=%s", (session['username']))
    memberGroups = list(c.fetchall())
    members=[]
    for group in memberGroups:
        groupid= group[1]
        result = c.execute("SELECT * FROM studydb.group WHERE idgroup=%s", (groupid,))
        member = c.fetchall()
        members.append(member)

    if request.method == "POST":
        leaveOrDelete = request.form['groupbutton']
        idgroup = request.form['groupId']
        if leaveOrDelete == "leave":
            # flash("Leave " + request.form['groupId'])
            data = c.execute("DELETE FROM studydb.memberOf WHERE username=%s AND groupID=%s", (session['username'], idgroup))
            conn.commit()


        if leaveOrDelete == "delete":
            # flash("Delete " + request.form['groupId'])
            data = c.execute("DELETE FROM studydb.memberOf WHERE groupID=%s", (idgroup,))
            conn.commit()
            data = c.execute("DELETE FROM studydb.group WHERE idgroup=%s AND createdBy=%s", (idgroup, session['username']))
            conn.commit()

    c.close()
    conn.close()
    return render_template('myGroups.html', owned=ownedGroups, member=members)



# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)
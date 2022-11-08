from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
# from data import Articles
from functools import wraps

app = Flask(__name__)

# config mySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Data@2020'
app.config['MYSQL_DB'] = 'myFlaskApp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init
mysql = MySQL(app)


# Articles = Articles()


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Article Found'
        return render_template('articles.html', msg=msg)

    # close connection
    cur.close()
    # return render_template('articles.html', articles=Articles)


@app.route('/article/<string:id>/')
def article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    query_string = "SELECT * FROM users WHERE id = %s"
    result = cur.execute(query_string, (id,))

    article = cur.fetchone()
    return render_template('article.html', article=article)

    # close connection
    cur.close()


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s, %s, %s, %s)", (name, email, username,
                                                                                               password))

        # commit
        mysql.connection.commit()

        # close connection
        cur.close()
        flash('Registered successfully you can now log in', 'success')
        return redirect(url_for('login'))
        # return render_template('register.html', form=form)

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = RegisterForm(request.form)
    if request.method == 'POST':
        # get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = mysql.connection.cursor()

        query_string = "SELECT * FROM users WHERE username = %s"
        result = cur.execute(query_string, (username,))
        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password = data['password']

            # compare password
            if sha256_crypt.verify(password_candidate, password):
                app.logger.info('PASSWORD MATCHED')
                # if passed create sessions
                session['logged_in'] = True
                session['username'] = username
                flash('Your are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)

            # close connection
            cur.close()

        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html', form=form)


# Check if user login
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please log in', 'danger')
            return redirect(url_for('login'))

    return wrap


@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Article Found'
        return render_template('dashboard.html', msg=msg)

    # close connection
    cur.close()

    # return render_template('dashboard.html')


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('Your are now Logged out', 'success')
    return redirect(url_for('login'))


class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # create cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title,body,author) VALUES(%s, %s, %s)", (title, body, session['username']))

        # commit
        mysql.connection.commit()

        # close connection
        cur.close()
        flash('Article successfully Added', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor
    cur = mysql.connection.cursor()

    # Get article by ID
    query_string = "SELECT * FROM articles WHERE id = %s"
    cur.execute(query_string, (id,))
    article = cur.fetchone()

    # get form
    form = ArticleForm(request.form)

    # Populate article form
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # create cursor
        cur = mysql.connection.cursor()
        query_string = "UPDATE articles SET title=%s, body=%s WHERE id = %s"
        cur.execute(query_string, (title, body, id,))

        # commit
        mysql.connection.commit()

        # close connection
        cur.close()
        flash('Article successfully Updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)


@app.route('/delete_article/<string:id>/', methods=['POST'])
@is_logged_in
def delete_article(id):
    # create cursor
    cur = mysql.connection.cursor()
    query_string = "DELETE FROM articles WHERE id = %s"
    cur.execute(query_string, (id,))

    # commit
    mysql.connection.commit()

    # close connection
    cur.close()
    flash('Article successfully Deleted', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True, host="0.0.0.0")

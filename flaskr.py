#!/usr/bin/python

# Imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for
from flask import abort, render_template, flash
from contextlib import closing

# Configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# Create the application
app = Flask(__name__)
app.config.from_object(__name__)


def connect_db():
    """Connect to the specified database"""
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Run script to (re)initialize database"""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    """Open database connection if not alreadt exists"""
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes database at end of request"""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.before_request
def before_request():
    """Open the database before processing requests"""
    g.sqlite_db = connect_db()


@app.teardown_request
def teardown_request(exception):
    """Tear down the application on request"""
    db = getattr(g, 'sqlite_db', None)
    if db is not None:
        db.close()


@app.route('/')
def show_entries():
    """Show the blog entries on the home page"""
    db = get_db()
    cur = db.execute('select title, text from entries order by id desc')
    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries = entries)


@app.route('/login', methods = ['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != USERNAME:
            error = 'Invalid username'
        elif request.form['password'] != PASSWORD:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You are logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/add', methods = ['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('insert into entries (title, text) values (?, ?)',
               [request.form['title'], request.form['text']])
    db.commit()
    flash('New entry posted')
    return redirect(url_for('show_entries'))


# Fire it up
if __name__ == '__main__':
    app.run()

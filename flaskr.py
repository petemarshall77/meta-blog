#!/usr/bin/python

# Imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for
from flask import abort, render_template, flash
from contextlib import closing
import os
import markdown
from flask import Markup
from flask_oauth import OAuth

# Configuration
DATABASE = 'data/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
AUTHORS = ['petemarshall77']

# On Bluemix, get the port number from environment variable VCAP_APP_PORT
# or default to 5000 on localhost
port = int(os.getenv('VCAP_APP_PORT', 5000))


# Set up OAuth link to Twitter
oauth = OAuth()
twitter = oauth.remote_app('twitter',
                           base_url = 'https://api.twitter.com/1',
                           request_token_url = 'https://api.twitter.com/oauth/request_token',
                           access_token_url = 'https://api.twitter.com/oauth/access_token',
                           authorize_url = 'https://api.twitter.com/oauth/authorize',
                           consumer_key = 'r73Aupw0YZxN0T7pimUS98yN4',
                           consumer_secret = 'GFr2fpsK6MSf53odRutuD0k6eDwfWw0kyEppdfDRLcmjofxW9v')

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

@twitter.tokengetter
def get_twitter_token(token=None):
    return session.get('twitter_token')

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
    entries = [dict(title=row[0], text=Markup(markdown.markdown(row[1]))) for row in cur.fetchall()]
    return render_template('show_entries.html', entries = entries)


@app.route('/login')
def login():
    return twitter.authorize(callback = url_for('oauth_authorized',
                                                next = request.args.get('next') or request.referrer or None))

@app.route('/oauth-authorized')
@twitter.authorized_handler
def oauth_authorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash('You did not sign in.')
        return redirect(next_url)

    session['twitter_token'] = (resp['oauth_token'], resp['oauth_token_secret'])
    session['twitter_handle'] = resp['screen_name']
    if session['twitter_handle'] in AUTHORS:
        session['is_author'] = True

    flash('You are signed in as %s.' % resp['screen_name'])
    return redirect(next_url)

@app.route('/logout')
def logout():
    session.pop('twitter_token', None)
    session.pop('twitter_handle', None)
    session.pop('is_author', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/add', methods = ['POST'])
def add_entry():
    if not session.get('twitter_token'):
        abort(401)
    db = get_db()
    db.execute('insert into entries (title, text) values (?, ?)',
               [request.form['title'], request.form['text']])
    db.commit()
    flash('New entry posted')
    return redirect(url_for('show_entries'))


# Fire it up
if __name__ == '__main__':
           app.run(host='0.0.0.0', port=port)

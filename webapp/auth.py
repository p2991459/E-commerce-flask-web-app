# auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login.utils import current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, login_required
from .models import User
from decouple import config, Csv
from functools import wraps

auth = Blueprint('auth', __name__)
ADMIN = config('ADMIN', cast=Csv())


@auth.route('/login')
def login():
    return render_template('login.html')


@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed
    # password in database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))  # if user doesn't exist or
        # password is wrong, reload the page

    # if the above check passes, then we know the user has the right
    # credentials
    login_user(user, remember=remember)
    return redirect(url_for('main.index'))


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


def is_admin():
    return current_user.email in ADMIN


def admin_required(func):
    '''
    If you decorate a view with this, it will ensure that the current user is
    admin before calling the actual view. (If they are not, it calls the
    :attr:`LoginManager.unauthorized` callback.) For example::

        @app.route('/post')
        @admin_required
        def post():
            pass

    :param func: The view function to decorate.
    :type func: function

    Inspired from flask-login @login_required
    '''
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.email not in ADMIN:
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view

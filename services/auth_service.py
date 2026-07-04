from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user
from models.models import User
from extension import db
from flask_login import login_user, logout_user, current_user






def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    return render_template('home.html')


def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('signup.html')

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or Email already exists!', 'warning')
            return render_template('signup.html')

        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login')) 

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
            return render_template('signup.html')

    return render_template('signup.html')



def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id')
        password = request.form.get('password')

        user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')

import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# -----------------------------
# DATABASE SETUP
# -----------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gotrak.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -----------------------------
# USER MODEL
# -----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=True)
    google_id = db.Column(db.String(200), nullable=True)

# -----------------------------
# GOOGLE OAUTH SETUP
# -----------------------------
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# -----------------------------
# ROUTES
# -----------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('index.html', username=session.get('username'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        user = User(username=username, email=email, password=password)
        try:
            db.session.add(user)
            db.session.commit()
            flash("Registration successful!", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("Registration failed: " + str(e), "danger")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/login/google')
def login_google():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        info = resp.json()
        email = info["email"]
        google_id = info["id"]
        user = User.query.filter_by(email=email).first()

        if not user:
            user = User(username=info.get("name", email.split("@")[0]),
                        email=email,
                        google_id=google_id)
            db.session.add(user)
            db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('index'))
    flash("Google login failed", "danger")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have logged out.", "info")
    return redirect(url_for('login'))

# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)

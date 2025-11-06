from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_dance.contrib.google import make_google_blueprint, google
import os

# ================= INISIALISASI APLIKASI =================
app = Flask(__name__)
# Secret key harus sama dengan yang ada di Render Env Vars jika ada, tapi pastikan ini adalah string yang kuat
app.secret_key = "supersecretkey123" 

# ================= DATABASE CONFIG =================
# Menggunakan sqlite untuk development, Render akan menggunakan file ini
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gotrak.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ================= LOGIN MANAGER =================
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# ================= DATABASE MODELS =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150)) # Hashed password sebaiknya digunakan
    google_id = db.Column(db.String(150), unique=True, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= GOOGLE OAUTH =================

# 1. Mengambil kunci rahasia dari Environment Variables (Render)
# Baris ini memastikan Flask-Dance bisa bekerja di lingkungan Render (HTTPS)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  
GOOGLE_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

# 2. Membuat Blueprint Google
google_bp = make_google_blueprint(
    client_id=GOOGLE_ID,
    client_secret=GOOGLE_SECRET,
    # HAPUS redirect_url. Flask-Dance akan otomatis menggunakan:
    # [DOMAIN_RENDER]/login/google/authorized, yang sudah didaftarkan di Google Cloud
    scope=["profile", "email"]
)

# 3. Mendaftarkan Blueprint dengan prefix /login
app.register_blueprint(google_bp, url_prefix="/login")

# ================= ROUTES =================
@app.route("/")
def index():
    # Jika pengguna sudah login, langsung arahkan ke halaman utama
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email sudah terdaftar!", "error")
            return redirect(url_for("register"))
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registrasi berhasil! Silakan login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("home"))
        else:
            flash("Email atau password salah!", "error")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/google_login")
def google_login():
    # Fungsi ini HANYA dipanggil setelah Google mengirimkan respons (melalui /login/google/authorized)
    if not google.authorized:
        # Pengecekan ini mungkin tidak pernah tercapai karena index.html sudah langsung ke google.login
        # Tapi jika diakses langsung, kita arahkan ke otorisasi
        return redirect(url_for("google.login"))
        
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Gagal mengambil data dari Google.", "error")
        return redirect(url_for("login"))
        
    info = resp.json()
    user = User.query.filter_by(google_id=info["id"]).first()
    
    if not user:
        # Jika pengguna baru, buat akun baru
        user = User(email=info["email"], google_id=info["id"])
        db.session.add(user)
        db.session.commit()
        
    login_user(user)
    flash(f"Login berhasil sebagai {info['email']}!", "success")
    return redirect(url_for("home"))

@app.route("/home")
@login_required
def home():
    return f"Selamat datang {current_user.email}! <a href='/survei'>Isi Survei</a> | <a href='/logout'>Logout</a>"

@app.route("/survei")
@login_required
def survei():
    return render_template("survei.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# ================= MAIN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Memastikan tabel dibuat saat aplikasi dijalankan
    app.run(debug=True)
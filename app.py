from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import qrcode
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/qr_codes'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    qrcodes = db.relationship('QRCode', backref='user', lazy=True)

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Ensure tables are created before the first request
@app.before_request
def create_tables_once():
    if not hasattr(app, '_tables_created'):
        db.create_all()
        app._tables_created = True

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        qrcodes = QRCode.query.filter_by(user_id=user.id).all()
        return render_template('dashboard.html', user=user, qrcodes=qrcodes)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        user = User(username=username, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid credentials!')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate():
    if 'user_id' not in session:
        flash('Please log in to generate QR codes.')
        return redirect(url_for('login'))
    data = request.form['data']
    user_id = session['user_id']
    filename = f"qr_{user_id}_{int(datetime.utcnow().timestamp())}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = qrcode.make(data)
    img.save(filepath)
    qr = QRCode(data=data, filename=filename, user_id=user_id)
    db.session.add(qr)
    db.session.commit()
    flash('QR code generated!')
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

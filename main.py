from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3 as db
from functools import wraps
# Added by Najib 
# added these libraries to as imports for email encryption and password hashing
import os
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = "SecretKeyForSecretStuff123"

# Added by Najib 
# This is the email encryption key setup
_env_key = os.environ.get("EMAIL_ENC_KEY")
_key_bytes = None
if _env_key:
    _key_bytes = _env_key.encode() if not isinstance(_env_key, bytes) else _env_key
else:
    # Added by Najib
    # look for the key file in documents folder or create it if it doesn't exist
    _key_path = os.path.join(os.path.dirname(__file__), "Documents", "email_key.key")
    if os.path.exists(_key_path):
        with open(_key_path, "rb") as f:
            _key_bytes = f.read()
    else:
        _key_bytes = Fernet.generate_key()
        os.makedirs(os.path.dirname(_key_path), exist_ok=True)
        with open(_key_path, "wb") as f:
            f.write(_key_bytes)

fernet = Fernet(_key_bytes)

def _decrypt_email(value):
    try:
        return fernet.decrypt(value.encode()).decode()
    except Exception:
        return value

def _encrypt_email(value):
    return fernet.encrypt(value.encode()).decode()

def _is_hashed(pw):
    return isinstance(pw, str) and pw.startswith("pbkdf2:")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    return render_template('index.html')

# added by Najib
# updated login route to handle password hashing and email encryption
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = db.connect('csgotrading.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, email, password FROM all_accounts WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        if row:
            user_id, uname, email_value, stored_pw = row
            if _is_hashed(stored_pw):
                ok = check_password_hash(stored_pw, password)
            else:
                ok = stored_pw == password
                if ok:
                    # Re-hash the password and update the database
                    new_hash = generate_password_hash(password)
                    cursor.execute(
                        "UPDATE all_accounts SET password = ? WHERE user_id = ?",
                        (new_hash, user_id)
                    )
                    conn.commit()

            if ok:
                # Check if email is encrypted; if not, encrypt and update, tested on the user "Ben", it worked
                decrypted_email = _decrypt_email(email_value)
                if decrypted_email == email_value:
                    try:
                        encrypted_email = _encrypt_email(email_value)
                        cursor.execute(
                            "UPDATE all_accounts SET email = ? WHERE user_id = ?",
                            (encrypted_email, user_id)
                        )
                        conn.commit()
                    except Exception:
                        pass

                session['user_id'] = user_id
                session['username'] = uname
                session['email'] = _decrypt_email(email_value)

                next_page = request.args.get('next')
                conn.close()
                return redirect(next_page or url_for('chat'))

        conn.close()
        return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            return render_template('register.html', error="Passwords do not match")

        elif not username or not email or not password:
            return render_template('register.html', error="All fields required")

        conn = db.connect('csgotrading.db')
        cursor = conn.cursor()
        # updated by Najib
        # hash the password and encrypt the email before storing
        hashed_pw = generate_password_hash(password)
        enc_email = _encrypt_email(email)
        # this adds a new user to the database with hashed password and encrypted email
        cursor.execute(
            "INSERT INTO all_accounts (username, password, email) VALUES (?, ?, ?)",
            (username, hashed_pw, enc_email)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/create_trade_offer', methods=['GET', 'POST'])
@login_required
def create_trade_offer():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('create_trade_offer_page.html')


@app.route('/chat')
@login_required
def chat():
    return render_template(
        'chat.html',
        username=session['username'],
        email=session['email']
    )


@app.route('/list')
def api_items():
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    query = request.args.get('q', '').strip()

    conn = db.connect('csgotrading.db')
    cursor = conn.cursor()

    if query:
        words = query.split()
        sql = "SELECT name, rarity, stattrak, souvenir, image FROM all_cs2_items WHERE "
        sql += " AND ".join(["LOWER(name) LIKE ?" for _ in words])
        sql += " LIMIT ? OFFSET ?"

        params = [f"%{word.lower()}%" for word in words]
        params.extend([per_page, offset])
        cursor.execute(sql, params)
    else:
        cursor.execute(
            "SELECT name, rarity, stattrak, souvenir, image FROM all_cs2_items LIMIT ? OFFSET ?",
            (per_page, offset)
        )

    items = cursor.fetchall()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify([
            {'name': i[0], 'rarity': i[1], 'stattrak': i[2], 'souvenir': i[3], 'image': i[4]}
            for i in items
        ])

    return render_template('list.html', items=items)


if __name__ == '__main__':
    app.run(debug=True)

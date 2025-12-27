from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3 as db
from functools import wraps

app = Flask(__name__)
app.secret_key = "SecretKeyForSecretStuff123"

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = db.connect('csgotrading.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, email FROM all_accounts WHERE username = ? AND password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]

            next_page = request.args.get('next')
            return redirect(next_page or url_for('chat'))

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
        cursor.execute("INSERT INTO all_accounts (username, password, email) VALUES (?, ?, ?)",(username, password, email))
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

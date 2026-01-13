from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3 as db
import sqlite3
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
    # Check if password is hashed using any Werkzeug hash format (pbkdf2, scrypt, argon2, bcrypt)
    return isinstance(pw, str) and any(pw.startswith(prefix) for prefix in ["pbkdf2:", "scrypt:", "argon2:", "bcrypt:"])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    return render_template('index.html')

# added by Najib
# updated login route to handle password hashing and email encryption
# removed user id (no need for it to be fetched)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()  # Convert to lowercase for case-insensitive login
        password = request.form['password']

        try:
            with db.connect('csgotrading.db', timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT username, email, password FROM all_accounts WHERE username = ?",
                    (username,)
                )
                row = cursor.fetchone()

                print(f"DEBUG: Looking for username '{username}'")
                print(f"DEBUG: Found row: {row is not None}")

                if row:
                    uname, email_value, stored_pw = row
                    ok = False

                    print(f"DEBUG: Password stored in DB starts with: {stored_pw[:20] if stored_pw else 'None'}")
                    print(f"DEBUG: Is hashed: {_is_hashed(stored_pw)}")

                    # Check password - handle both hashed and unhashed (legacy) passwords
                    if _is_hashed(stored_pw):
                        ok = check_password_hash(stored_pw, password)
                        print(f"DEBUG: Hashed password check result: {ok}")
                    else:
                        # Legacy unhashed password - verify it
                        ok = stored_pw == password
                        print(f"DEBUG: Direct comparison result: {ok}")
                        if ok:
                            # Re-hash the password and update the database
                            new_hash = generate_password_hash(password)
                            cursor.execute(
                                "UPDATE all_accounts SET password = ? WHERE username = ?",
                                (new_hash, uname)
                            )
                            conn.commit()

                    if ok:
                        # Check if email is encrypted; if not, encrypt and update
                        decrypted_email = _decrypt_email(email_value)
                        if decrypted_email == email_value:
                            try:
                                encrypted_email = _encrypt_email(email_value)
                                cursor.execute(
                                    "UPDATE all_accounts SET email = ? WHERE username = ?",
                                    (encrypted_email, uname)
                                )
                                conn.commit()
                            except Exception:
                                pass

                        session['username'] = uname
                        session['email'] = _decrypt_email(email_value)

                        next_page = request.args.get('next')
                        return redirect(next_page or url_for('chat'))

        except Exception as e:
            print("LOGIN ERROR:", e)

        return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').lower()
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if not username or not email or not password:
            return render_template('register.html', error="All fields required")

        if password != confirm:
            return render_template('register.html', error="Passwords do not match")

        # ^ swapped these to check if email exists before inserting
        # got error when trying to register with an already used email (FIXED BY K)
        try:
            with db.connect('csgotrading.db', timeout=10) as conn:
                cursor = conn.cursor()

                # Check username
                cursor.execute(
                    "SELECT 1 FROM all_accounts WHERE username = ?",
                    (username,)
                )
                if cursor.fetchone():
                    return render_template(
                        'register.html',
                        error="Username already exists"
                    )
                hashed_pw = generate_password_hash(password)
                enc_email = _encrypt_email(email)
                # Generate user ID
                import uuid
                user_id = str(uuid.uuid4())
                # Insert user
                cursor.execute(
                    "INSERT INTO all_accounts (\"user id\", username, password, email) VALUES (?, ?, ?, ?)",
                    (user_id, username, hashed_pw, enc_email)
                )
                conn.commit()

        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username already exists")

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/create_trade_offer', methods=['GET', 'POST'])
@login_required
def create_trade_offer():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('create_trade_offer_page.html')


def get_user_id(username):
    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT \"user id\" FROM all_accounts WHERE username = ?", (username,))
        result = cursor.fetchone()
        return result[0] if result else None

@app.route('/chat')
@login_required
def chat():
    return render_template(
        'chat.html',
        username=session['username'],
        email=session['email']
    )

@app.route('/api/friends')
@login_required
def get_friends():
    username = session['username']
    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username FROM all_accounts WHERE username != ?",
            (username,)
        )
        friends = [row[0] for row in cursor.fetchall()]
    return jsonify(friends)

@app.route('/api/chat_threads')
@login_required
def get_chat_threads():
    username = session['username']
    user_id = get_user_id(username)
    if not user_id:
        return jsonify([])

    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                ct."chat id",
                CASE 
                    WHEN ct."user1 id" = ? THEN a2.username 
                    ELSE a1.username 
                END AS other_user,
                m."sender id" AS last_sender
            FROM all_chat_threads ct
            JOIN all_accounts a1 ON ct."user1 id" = a1."user id"
            JOIN all_accounts a2 ON ct."user2 id" = a2."user id"
            LEFT JOIN all_messages m 
                ON m."thread id" = ct."chat id"
            WHERE ct."user1 id" = ? OR ct."user2 id" = ?
            GROUP BY ct."chat id"
            HAVING MAX(m.time)
        ''', (user_id, user_id, user_id))

        threads = []
        for row in cursor.fetchall():
            threads.append({
                'id': row[0],
                'other_user': row[1],
                'last_sender_is_me': row[2] == user_id
            })

    return jsonify(threads)

@app.route('/api/messages/<thread_id>')
@login_required
def get_messages(thread_id):
    username = session['username']
    user_id = get_user_id(username)
    if not user_id:
        return jsonify({'error': 'User not found'}), 404
    
    # Verify user has access to this thread
    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM all_chat_threads WHERE \"chat id\" = ? AND (\"user1 id\" = ? OR \"user2 id\" = ?)",
            (thread_id, user_id, user_id)
        )
        if not cursor.fetchone():
            return jsonify({'error': 'Unauthorized'}), 403
        
        cursor.execute('''
            SELECT a.username, m.content, m.time
            FROM all_messages m
            JOIN all_accounts a ON m."sender id" = a."user id"
            WHERE m."thread id" = ?
            ORDER BY m.time ASC
        ''', (thread_id,))
        messages = [{'sender': row[0], 'message': row[1], 'time': row[2]} for row in cursor.fetchall()]
    return jsonify(messages)

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    username = session['username']
    user_id = get_user_id(username)
    if not user_id:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    recipient_username = data.get('recipient')
    message_content = data.get('message')
    
    if not recipient_username or not message_content:
        return jsonify({'error': 'Missing recipient or message'}), 400
    
    recipient_id = get_user_id(recipient_username)
    if not recipient_id:
        return jsonify({'error': 'Recipient not found'}), 404
    
    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()
        
        # Get or create thread
        cursor.execute('''
            SELECT "chat id" FROM all_chat_threads 
            WHERE ("user1 id" = ? AND "user2 id" = ?) OR ("user1 id" = ? AND "user2 id" = ?)
        ''', (user_id, recipient_id, recipient_id, user_id))
        thread = cursor.fetchone()
        
        if not thread:
            # Generate a unique chat id
            import uuid
            chat_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO all_chat_threads (\"chat id\", \"user1 id\", \"user2 id\") VALUES (?, ?, ?)",
                (chat_id, user_id, recipient_id)
            )
            thread_id = chat_id
        else:
            thread_id = thread[0]
        
        # Insert message
        import uuid
        message_id = str(uuid.uuid4())
        from datetime import datetime
        cursor.execute(
            "INSERT INTO all_messages (\"message id\", \"sender id\", content, time, \"thread id\") VALUES (?, ?, ?, ?, ?)",
            (message_id, user_id, message_content, datetime.now(), thread_id)
        )
        conn.commit()
    
    return jsonify({'success': True})

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
    app.run(debug=True, use_reloader=False)

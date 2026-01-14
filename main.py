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
            SELECT ct."chat id", 
                   CASE WHEN ct."user1 id" = ? THEN a2.username ELSE a1.username END as other_user
            FROM all_chat_threads ct
            JOIN all_accounts a1 ON ct."user1 id" = a1."user id"
            JOIN all_accounts a2 ON ct."user2 id" = a2."user id"
            WHERE ct."user1 id" = ? OR ct."user2 id" = ?
        ''', (user_id, user_id, user_id))
        threads = [{'id': row[0], 'other_user': row[1]} for row in cursor.fetchall()]
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
        sql = '''
            SELECT item_id, name, rarity, stattrak, souvenir, image
            FROM all_cs2_items
            WHERE {}
            LIMIT ? OFFSET ?
        '''.format(" AND ".join(["LOWER(name) LIKE ?" for _ in words]))

        params = [f"%{word.lower()}%" for word in words]
        params.extend([per_page, offset])
        cursor.execute(sql, params)
    else:
        cursor.execute(
            '''
            SELECT item_id, name, rarity, stattrak, souvenir, image
            FROM all_cs2_items
            LIMIT ? OFFSET ?
            ''',
            (per_page, offset)
        )

    items = cursor.fetchall()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify([
            {
                'id': i[0],
                'name': i[1],
                'rarity': i[2],
                'stattrak': i[3],
                'souvenir': i[4],
                'image': i[5]
            }
            for i in items
        ])

    return render_template('list.html')

@app.route('/api/create_trade_offer', methods=['POST'])
@login_required
def api_create_trade_offer():
    data = request.get_json()

    has_items = data.get('has', [])
    wants_items = data.get('wants', [])

    # Validation
    if not has_items or not wants_items:
        return jsonify({'error': 'At least one HAS and one WANTS item required'}), 400

    user_id = get_user_id(session['username'])
    if not user_id:
        return jsonify({'error': 'User not found'}), 400

    import uuid
    from datetime import datetime

    trade_id = str(uuid.uuid4())

    try:
        with db.connect('csgotrading.db') as conn:
            cursor = conn.cursor()

            # Insert trade
            cursor.execute(
                '''
                INSERT INTO all_trade_offers
                ("trade id", "user id", time, comment)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    trade_id,
                    user_id,
                    datetime.now(),
                    ""
                )
            )

            # Insert HAS items
            for item_id in has_items:
                cursor.execute(
                    '''
                    INSERT INTO all_cs2_trade_offer_items
                    ("trade item id", "item id", "trade id", "has/wants")
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        str(uuid.uuid4()),
                        item_id,
                        trade_id,
                        True
                    )
                )

            # Insert WANTS items
            for item_id in wants_items:
                cursor.execute(
                    '''
                    INSERT INTO all_cs2_trade_offer_items
                    ("trade item id", "item id", "trade id", "has/wants")
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        str(uuid.uuid4()),
                        item_id,
                        trade_id,
                        False
                    )
                )

            conn.commit()

    except Exception as e:
        print("CREATE TRADE ERROR:", e)
        return jsonify({'error': 'Failed to create trade'}), 500

    return jsonify({'success': True, 'trade_id': trade_id})

@app.route('/api/trades')
def api_trades():
    print("ARGS:", dict(request.args))

    item_query = request.args.get("item", "").strip().lower()
    wear = request.args.get("wear", "").strip().lower()
    search_type = request.args.get("type", "any")
    rarity = request.args.get("rarity")
    stattrak = request.args.get("stattrak")
    souvenir = request.args.get("souvenir")

    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()

        conditions = []
        params = []

        if item_query:
            for word in item_query.split():
                conditions.append("LOWER(i.name) LIKE ?")
                params.append(f"%{word}%")

        if wear:
            for word in wear.split():
                conditions.append("LOWER(i.name) LIKE ?")
                params.append(f"%{word}%")

        if rarity:
            conditions.append("i.rarity = ?")
            params.append(rarity)

        if stattrak:
            conditions.append("i.stattrak = 1")

        if souvenir:
            conditions.append("i.souvenir = 1")
            
        if search_type == "has":
            conditions.append('ti."has/wants" = 1')
        elif search_type == "wants":
            conditions.append('ti."has/wants" = 0')

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        cursor.execute(f'''
            SELECT DISTINCT
                ti."trade id"
            FROM all_cs2_trade_offer_items ti
            JOIN all_cs2_items i ON ti."item id" = i.item_id
            {where_clause}
        ''', params)

        trade_ids = [row[0] for row in cursor.fetchall()]

        if not trade_ids:
            return jsonify([])

        cursor.execute(f'''
            SELECT
                t."trade id",
                t.time,
                a.username,
                a."user id"
            FROM all_trade_offers t
            JOIN all_accounts a ON t."user id" = a."user id"
            WHERE t."trade id" IN ({",".join("?" * len(trade_ids))})
            ORDER BY t.time DESC
        ''', trade_ids)

        trade_map = {
            trade_id: {
                "trade_id": trade_id,
                "username": username,
                "user_id": user_id,
                "time": time,
                "has": [],
                "wants": []
            }
            for trade_id, time, username, user_id in cursor.fetchall()
        }

        cursor.execute(f'''
            SELECT
                ti."trade id",
                ti."has/wants",
                i.item_id,
                i.name,
                i.image
            FROM all_cs2_trade_offer_items ti
            JOIN all_cs2_items i ON ti."item id" = i.item_id
            WHERE ti."trade id" IN ({",".join("?" * len(trade_ids))})
        ''', trade_ids)

        for trade_id, has_wants, item_id, name, image in cursor.fetchall():
            item = {
                "item_id": item_id,
                "name": name,
                "image": image
            }

            if has_wants:
                trade_map[trade_id]["has"].append(item)
            else:
                trade_map[trade_id]["wants"].append(item)

    return jsonify(list(trade_map.values()))




@app.route('/trades')
def trades():
    return render_template('trade_list.html')

@app.route('/my_trades')
@login_required
def my_trades():
    return render_template('my_trades.html')

@app.route('/api/my_trades')
@login_required
def api_my_trades():
    user_id = get_user_id(session['username'])

    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                t."trade id",
                t.time
            FROM all_trade_offers t
            WHERE t."user id" = ?
            ORDER BY t.time DESC
        ''', (user_id,))

        trades = cursor.fetchall()

        trade_map = {
            trade_id: {
                "trade_id": trade_id,
                "time": time,
                "has": [],
                "wants": []
            }
            for trade_id, time in trades
        }

        if not trade_map:
            return jsonify([])

        cursor.execute('''
            SELECT
                ti."trade id",
                ti."has/wants",
                i.item_id,
                i.name,
                i.image
            FROM all_cs2_trade_offer_items ti
            JOIN all_cs2_items i ON ti."item id" = i.item_id
            WHERE ti."trade id" IN ({})
        '''.format(",".join("?" * len(trade_map))), tuple(trade_map.keys()))

        for trade_id, has_wants, item_id, name, image in cursor.fetchall():
            item = {
                "item_id": item_id,
                "name": name,
                "image": image
            }
            if has_wants:
                trade_map[trade_id]["has"].append(item)
            else:
                trade_map[trade_id]["wants"].append(item)

    return jsonify(list(trade_map.values()))

@app.route('/api/delete_trade', methods=['POST'])
@login_required
def delete_trade():
    data = request.get_json()
    trade_id = data.get('trade_id')

    if not trade_id:
        return jsonify({'error': 'Missing trade id'}), 400

    user_id = get_user_id(session['username'])

    with db.connect('csgotrading.db') as conn:
        cursor = conn.cursor()

        # Ownership check
        cursor.execute(
            'SELECT 1 FROM all_trade_offers WHERE "trade id" = ? AND "user id" = ?',
            (trade_id, user_id)
        )
        if not cursor.fetchone():
            return jsonify({'error': 'Not allowed'}), 403

        # Delete items first
        cursor.execute(
            'DELETE FROM all_cs2_trade_offer_items WHERE "trade id" = ?',
            (trade_id,)
        )

        # Delete trade
        cursor.execute(
            'DELETE FROM all_trade_offers WHERE "trade id" = ?',
            (trade_id,)
        )

        conn.commit()

    return jsonify({'success': True})

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/support')
def support():
    return render_template('support.html')
    
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

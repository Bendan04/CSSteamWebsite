from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3 as db

app = Flask(__name__)
conn = db.connect('csgotrading.db')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/create_trade_offer', methods=['GET', 'POST'])
def create_trade_offer():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('create_trade_offer_page.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

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
        items_list = [
            {'name': i[0], 'rarity': i[1], 'stattrak': i[2], 'souvenir': i[3], 'image': i[4]}
            for i in items
        ]
        return jsonify(items_list)

    return render_template('list.html', items=items)

if __name__ == '__main__':
    app.run(debug=True)
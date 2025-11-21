from flask import Flask, render_template, request, redirect, url_for
import sqlite3 as db

app = Flask(__name__)
conn = db.connect('cs2_weapons.db')

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
def list_items():
    conn = db.connect('cs2_weapons.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, rarity, stattrak, souvenir, image FROM items")
    items = cursor.fetchall()

    conn.close()

    return render_template('list.html', items=items)


if __name__ == '__main__':
    app.run(debug=True)
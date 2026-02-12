from flask import Flask, render_template, redirect, request, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
app = Flask(__name__)
app.secret_key = 'secret key'

USERSDATA = "users.db"
def get_users_db():
    if 'users_db' not in g:
        users_db = sqlite3.connect(USERSDATA)
        users_db.row_factory = sqlite3.Row
    return users_db

@app.teardown_appcontext
def close_users_db(error):
    users_db = g.pop('users_db', None)
    if users_db is not None:
        users_db.close()

def get_coffee_db():
    if 'coffee_db' not in g:
        coffee_db = sqlite3.connect("coffee.db")
        coffee_db.row_factory = sqlite3.Row
    return coffee_db

@app.teardown_appcontext
def close_coffee_db(error):
    coffee_db = g.pop('coffee_db', None)
    if coffee_db is not None:
        coffee_db.close()


@app.route('/')
def index():
    db = get_coffee_db()
    coffee_items = db.execute("SELECT * FROM coffee").fetchall()

    return render_template('index.html', coffee_items=coffee_items, userName=session.get('user'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        formName = request.form.get('name')
        formPassword = request.form.get('password')

        if not formName:
            error = "Name is required"
        if not formPassword:
            error = "Password is required"
        users_db = get_users_db()
        user = users_db.execute("SELECT * FROM usersDetails WHERE name = ?", (formName,)).fetchone()

        if user and check_password_hash(user['hash'], formPassword):
            session['user'] = formName
            return redirect('/')
        else:
            error = "Invalid username or password"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        formName = request.form.get('name')
        formPassword = request.form.get('password')
        formConfirmation = request.form.get('confirmation')
        formemail = request.form.get('email')

        if not formName:
            error = "Name is required"
        if not formPassword:
            error = "Password is required"
        if not formConfirmation:
            error = "Password confirmation is required"
        if not formemail:
            error = "Email is required"
        if formPassword != formConfirmation:
            error = "Passwords do not match"

        users_db = get_users_db()
        for name, in users_db.execute("SELECT name FROM usersDetails"):
            if name == formName:
                error = "Username already taken"
        hashedPassword = generate_password_hash(formPassword)
        users_db.execute("INSERT INTO usersDetails (name, hash, email) VALUES (?, ?, ?)", (formName, hashedPassword, formemail))
        users_db.commit()
        return redirect('/')
    return render_template('register.html', error=error)

@app.route('/coffee')
def coffee():
    db = get_coffee_db()
    item = request.args.get('item')
    if item:
        coffee_items = db.execute("SELECT * FROM coffee WHERE name LIKE ?", (f"%{item}%",)).fetchall()
    else:
        coffee_items = db.execute("SELECT * FROM coffee").fetchall()


    return render_template('coffee.html', coffee_items=coffee_items, userName=session.get('user'))

@app.route('/about', methods=['GET', 'POST'])
def about():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        recommendations = request.form.get('recommendations')

        db = get_users_db()
        db.execute("INSERT INTO recommended (email, suggestion) VALUES (?, ?)", (email, recommendations))
        db.commit()
        message = "Thank you for your feedback!"

    return render_template('about.html', userName=session.get('user'), message=message )

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if not session.get('user'):
        return redirect('/login')

    item_id = int(request.form.get('item_id'))
    
    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append(item_id)
    session.modified = True
    cart_jason = json.dumps(session['cart'])


    db = get_users_db()
    db.execute("UPDATE usersDetails SET cart = ? WHERE name = ?", (cart_jason, session.get('user')))
    db.commit()

    return redirect('/coffee')

@app.route('/cart')
def cart():
    cart_items = []
    user_db = get_users_db()
    myItems = user_db.execute("SELECT cart FROM usersDetails WHERE name = ?", (session.get('user'),)).fetchone()
    if myItems and myItems['cart']:
        session['cart'] = json.loads(myItems['cart'])
    else:
        session['cart'] = []

        cart_items = []

    coffee_db = get_coffee_db()
    for item_id in session['cart']:
        item = coffee_db.execute("SELECT * FROM coffee WHERE id = ?", (item_id,)).fetchone()
        if item:
            cart_items.append(item)
            print(item)

    return render_template('cart.html', cart_items=cart_items, userName=session.get('user'))

@app.route('/removeFromCart', methods=['POST'])
def removeFromCart():
    itemID = int(request.form.get('item_id'))
    if 'cart' in session and itemID in session['cart']:
        session['cart'].remove(itemID)
        session.modified = True

        cart_jason = json.dumps(session['cart'])
        db = get_users_db()
        db.execute("UPDATE usersDetails SET cart = ? WHERE name = ?", (cart_jason, session.get('user')))
        db.commit()

    return redirect('/cart')
@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = []
    session.modified = True

    db = get_users_db()
    db.execute("UPDATE usersDetails SET cart = ? WHERE name = ?", (json.dumps([]), session.get('user')))
    db.commit()

    return redirect('/cart')
    
if __name__ == "__main__":
    app.run()

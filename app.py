from flask import Flask, render_template, request, url_for, redirect, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

# Database Configuration
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "mysql@vel5558"
app.config['MYSQL_DB'] = "inventory"
app.config['MYSQL_CURSORCLASS'] = "DictCursor"
mysql = MySQL(app)

# Home
@app.route('/')
def home():
    return render_template('home.html')

# Products View
@app.route('/products')
def products():
    con = mysql.connection.cursor()
    con.execute("SELECT * FROM products")
    result = con.fetchall()
    con.close()
    return render_template("products.html", datas=result)

# Add Products
@app.route('/add_products', methods=['GET', 'POST'])
def add_products():
    if request.method == "POST":
        pid = request.form['product_id']
        pname = request.form['product_name']
        quan = request.form['quantity']
        con = mysql.connection.cursor()
        con.execute("INSERT INTO products (product_id, product_name, quantity) VALUES (%s, %s, %s)", [pid, pname, quan])
        mysql.connection.commit()
        con.close()
        return redirect(url_for('products'))
    return render_template("add_products.html")

# Edit Product
@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    con = mysql.connection.cursor()
    sql="SELECT * FROM products WHERE product_id = %s"
    con.execute(sql, [product_id])
    product = con.fetchone()

    if request.method == 'POST':
        pname = request.form['product_name']
        quantity = request.form['quantity']
        sql="UPDATE products SET product_name = %s, quantity = %s WHERE product_id = %s"
        con.execute(sql, [pname, quantity, product_id])
        mysql.connection.commit()
        con.close()
        return redirect(url_for('products'))

    con.close()
    return render_template('edit.html', product=product)

    

# Get Available Quantity
@app.route('/get_available/<product_id>')
def get_available(product_id):
    con = mysql.connection.cursor()
    con.execute("SELECT quantity FROM products WHERE product_id = %s", [product_id])
    row = con.fetchone()

    if not row:
        con.close()
        return jsonify({"available": 0})

    total_qty = row['quantity']
    con.execute("SELECT COALESCE(SUM(quantity), 0) AS moved_qty FROM movements WHERE product_id = %s", [product_id])
    moved_qty = con.fetchone()['moved_qty']
    con.close()

    available = total_qty - moved_qty
    return jsonify({"available": available})

# Locations
@app.route('/locations')
def locations():
    con = mysql.connection.cursor()
    con.execute("SELECT * FROM locations")
    result = con.fetchall()
    con.close()
    return render_template("locations.html", datas=result)

@app.route('/add_locations', methods=['GET', 'POST'])
def add_locations():
    if request.method == "POST":
        lid = request.form['id']
        con = mysql.connection.cursor()
        con.execute("INSERT INTO locations (id) VALUES (%s)", [lid])
        mysql.connection.commit()
        con.close()
        return redirect(url_for("locations"))
    return render_template("add_locations.html")

# Edit Location
@app.route('/edit_location/<int:id>', methods=['GET', 'POST'])
def edit_location(id):
    con = mysql.connection.cursor()
    con.execute("SELECT * FROM locations WHERE id = %s", [id])
    location = con.fetchone()

    if request.method == 'POST':
        new_id = request.form['id']
        con.execute("UPDATE locations SET id = %s WHERE id = %s", [new_id, id])
        mysql.connection.commit()
        con.close()
        return redirect(url_for("locations"))

    con.close()
    return render_template("edit_location.html", location=location)


# Movements
@app.route('/movements')
def movements():
    con = mysql.connection.cursor()
    con.execute("SELECT * FROM movements")
    result = con.fetchall()
    con.close()
    return render_template("movements.html", datas=result)

@app.route('/add_movements', methods=['GET', 'POST'])
def add_movements():
    if request.method == "POST":
        mp = request.form['product_id']
        mfrom = request.form.get('from_location') or None
        mto = request.form.get('to_location') or None
        mqty = request.form['quantity']

        if not mfrom and not mto:
            return "Error: At least one of FROM or TO must be filled.", 400

        con = mysql.connection.cursor()
        con.execute("INSERT INTO movements (product_id, from_location, to_location, quantity) VALUES (%s, %s, %s, %s)", [mp, mfrom, mto, mqty])
        mysql.connection.commit()
        con.close()
        return redirect(url_for("movements"))
    con = mysql.connection.cursor()
    con.execute("SELECT product_id FROM products")
    products = con.fetchall()
    con.execute("SELECT id FROM locations")
    locations = con.fetchall()
    con.close()
    return render_template("add_movements.html", products=products, locations=locations)

@app.route('/edit_movement/<int:id>', methods=['GET', 'POST'])
def edit_movement(id):
    con = mysql.connection.cursor()
    con.execute("SELECT * FROM movements WHERE m_id = %s", [id])  
    movement = con.fetchone()
    if request.method == 'POST':
        product_id = request.form['product_id']
        from_location = request.form.get('from_location') or None
        to_location = request.form.get('to_location') or None
        quantity = request.form['quantity']
        if not from_location and not to_location:
            return "Error: At least one of FROM or TO must be filled.", 400
        con.execute("""
            UPDATE movements
            SET product_id = %s, from_location = %s, to_location = %s, quantity = %s
            WHERE m_id = %s
        """, (product_id, from_location, to_location, quantity, id))
        mysql.connection.commit()
        con.close()
        return redirect(url_for("movements"))


    con.execute("SELECT product_id FROM products")
    products = con.fetchall()
    con.execute("SELECT id FROM locations")
    locations = con.fetchall()
    con.close()
    return render_template("edit_movement.html", movement=movement, products=products, locations=locations)
# Balance
@app.route('/balance')
def balance():
    con = mysql.connection.cursor()
    con.execute("SELECT product_id, from_location, to_location, quantity FROM movements")
    data = con.fetchall()
    con.close()
    stock = {}
    for row in data:
        product = row['product_id']
        from_loc = row['from_location']
        to_loc = row['to_location']
        qty = row['quantity']
        if (product, from_loc) not in stock:
            stock[(product, from_loc)] = 0
        stock[(product, from_loc)] -= qty
        if (product, to_loc) not in stock:
            stock[(product, to_loc)] = 0
        stock[(product, to_loc)] += qty

    result = [{'product': p, 'location': l, 'quantity': q} for (p, l), q in stock.items()]

    return render_template('balance.html', datas=result)
if __name__ == "__main__":
    app.secret_key = "abc123"
    app.run(debug=True)

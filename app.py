from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key for production!

# ----------------------- DATA STORAGE -----------------------
# In-memory sample data
products = [
    {
        'id': 1,
        'name': 'Smartphone',
        'price': 299.99,
        'description': 'Latest smartphone with advanced features',
        'image': 'smartphone.png'
    },
    {
        'id': 2,
        'name': 'Laptop',
        'price': 899.99,
        'description': 'High performance laptop for work and gaming',
        'image': 'laptop.png'
    },
    {
        'id': 3,
        'name': 'Headphones',
        'price': 59.99,
        'description': 'Noise-cancelling headphones',
        'image': 'headphones.png'
    }
]

# Sample in-memory users list
users = [
    {
        'id': 1,
        'username': 'admin',
        'password': 'admin123',  # NEVER store plaintext passwords in production!
        'is_admin': True
    },
    {
        'id': 2,
        'username': 'john',
        'password': 'password123',
        'is_admin': False
    }
]


# The cart is a dictionary mapping user_id to a list of items.
# Each item is a dict: {'product_id': int, 'quantity': int}
cart = {}

# ----------------------- UTILITY FUNCTIONS -----------------------
# Configure the upload folder and allowed file extensions
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_current_user():
    if 'user_id' in session:
        return next((u for u in users if u['id'] == session['user_id']), None)
    return None

def is_admin():
    user = get_current_user()
    return user is not None and user.get('is_admin', False)



# ----------------------- USER AUTHENTICATION -----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)
        if user:
            session['user_id'] = user['id']
            print("User logged in:", user)  # Debugging output
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')
    return render_template('login.html')




@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Ensure the username doesn't exist already
        if any(u['username'] == username for u in users):
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        new_id = max(u['id'] for u in users) + 1 if users else 1
        # Always create a normal user; admin rights are not granted here
        new_user = {'id': new_id, 'username': username, 'password': password, 'is_admin': False}
        users.append(new_user)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


# ----------------------- HTML ROUTES -----------------------
@app.route('/')
def index():
    """Home page showing all products."""
    return render_template('index.html', products=products, user=get_current_user())

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page with add-to-cart form."""
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('index'))
    return render_template('product_detail.html', product=product, user=get_current_user())

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Add a product to the current user's cart."""
    user = get_current_user()
    if not user:
        flash('Please log in to add items to your cart.', 'danger')
        return redirect(url_for('login'))
    product_id = int(request.form['product_id'])
    quantity = int(request.form.get('quantity', 1))
    user_id = user['id']
    if user_id not in cart:
        cart[user_id] = []
    # If product already exists in cart, update the quantity.
    item = next((item for item in cart[user_id] if item['product_id'] == product_id), None)
    if item:
        item['quantity'] += quantity
    else:
        cart[user_id].append({'product_id': product_id, 'quantity': quantity})
    flash('Item added to cart!', 'success')
    return redirect(url_for('cart_view'))

@app.route('/cart')
def cart_view():
    """Display the current user's shopping cart."""
    user = get_current_user()
    if not user:
        flash('Please log in to view your cart.', 'danger')
        return redirect(url_for('login'))
    user_cart = cart.get(user['id'], [])
    cart_items = []
    total = 0
    for item in user_cart:
        product = next((p for p in products if p['id'] == item['product_id']), None)
        if product:
            item_total = product['price'] * item['quantity']
            total += item_total
            cart_items.append({'product': product, 'quantity': item['quantity'], 'total': item_total})
    return render_template('cart.html', cart_items=cart_items, total=total, user=user)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """Remove an item from the cart."""
    user = get_current_user()
    if not user:
        flash('Please log in to modify your cart.', 'danger')
        return redirect(url_for('login'))
    user_id = user['id']
    if user_id in cart:
        cart[user_id] = [item for item in cart[user_id] if item['product_id'] != product_id]
        flash('Item removed from cart!', 'success')
    return redirect(url_for('cart_view'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout page to review cart and place order."""
    user = get_current_user()
    if not user:
        flash('Please log in to place an order.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        user_cart = cart.get(user['id'], [])
        if not user_cart:
            flash('Your cart is empty!', 'danger')
            return redirect(url_for('cart_view'))
        total = 0
        for item in user_cart:
            product = next((p for p in products if p['id'] == item['product_id']), None)
            if product:
                total += product['price'] * item['quantity']
        # Here you would normally process payment and store order details.
        cart[user['id']] = []  # Clear the cart after the order is placed.
        flash(f'Order placed successfully! Total amount: ₹{total:.2f}', 'success')
        return redirect(url_for('index'))
    else:
        user_cart = cart.get(user['id'], [])
        cart_items = []
        total = 0
        for item in user_cart:
            product = next((p for p in products if p['id'] == item['product_id']), None)
            if product:
                item_total = product['price'] * item['quantity']
                total += item_total
                cart_items.append({'product': product, 'quantity': item['quantity'], 'total': item_total})
        return render_template('checkout.html', cart_items=cart_items, total=total, user=user)
# -------------------------------------------------------------
# ----------------------- ADMIN ROUTES -----------------------
@app.route('/admin')
def admin_dashboard():
    user = get_current_user()
    print("Current user:", user)  # Debugging output
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))
    return render_template('admin/dashboard.html', products=products, user=user)



# def admin_dashboard():
#     user = get_current_user()
#     print("Current user:", user)  # Debugging output
#     if not is_admin():
#         flash('Access denied. Admins only.', 'danger')
#         return redirect(url_for('index'))
#     return render_template('admin/dashboard.html', products=products, user=user)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def admin_add_product():
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        
        # Process file upload if available
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            filename = 'default.png'  # Use a default image if no valid file is uploaded

        new_id = max([p['id'] for p in products]) + 1 if products else 1
        new_product = {
            'id': new_id,
            'name': name,
            'price': float(price),
            'description': description,
            'image': filename
        }
        products.append(new_product)
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_product.html', user=get_current_user())

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def admin_edit_product(product_id):
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))
    
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        product['name'] = request.form['name']
        product['price'] = float(request.form['price'])
        product['description'] = request.form['description']
        
        # Check for new file upload
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            product['image'] = filename  # Update product image if new file is uploaded
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_product.html', product=product, user=get_current_user())



@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def admin_delete_product(product_id):
    """Admin can delete a product."""
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))
    
    global products
    products = [p for p in products if p['id'] != product_id]
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# ----------------------- API ENDPOINTS -----------------------
# These endpoints return JSON data.

@app.route('/api/products', methods=['GET'])
def api_get_products():
    return jsonify(products)

@app.route('/api/products/<int:product_id>', methods=['GET'])
def api_get_product(product_id):
    product = next((p for p in products if p['id'] == product_id), None)
    if product:
        return jsonify(product)
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/products', methods=['POST'])
def api_add_product():
    new_product = request.json
    if 'id' not in new_product:
        new_product['id'] = max([p['id'] for p in products]) + 1 if products else 1
    products.append(new_product)
    return jsonify({'message': 'Product added', 'product': new_product}), 201

# (Additional API endpoints for updating or deleting products, managing users, cart, and orders
# can be added here using PUT and DELETE methods as needed.)

# ----------------------- RUN THE APP -----------------------
if __name__ == '__main__':
    app.run(debug=True)


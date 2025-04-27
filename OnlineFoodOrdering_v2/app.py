# app.py
from flask import render_template, redirect, request, session, url_for, Flask, jsonify
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import random
import string
from werkzeug.utils import secure_filename

from models import init_app, db
from models.user import User
from models.food_category import FoodCategory
from models.menu_item import MenuItem
from models.order import Order
from models.order_item import OrderItem
from models.review import Review
from models.user import User
#imports all of the tables for the databases and use within app.
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
#app config
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_KEY_PREFIX'] = 'helloo'
app.config['SESSION_COOKIE_NAME'] = 'Bookstorevsession'
app.secret_key = "Kc5c3zTk'-3<&BdL:P92O{_(:-NkY+KMMW"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_app(app)

#websites index
@app.route('/')
def index():
    return render_template('index.html')

#apps login routing
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        print(email)
        print(password)

        # Query the user from the database
        user = User.query.filter_by(email=email, password=password).first()

        if user:
            print('aksjkjsjksj')
            # Store user information in session
            session['user_id'] = user.id
            session['role'] = user.role

            # Redirect based on user role
            if user.role == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/user/dashboard')
        else:
            error = 'Invalid email or password.'

    return render_template('login.html', error=error)

#apps path to register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        # Check if passwords match
        if password != confirm_password:
            error = 'Passwords do not match.'
            return render_template('register.html', error=error)

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = 'User already exists.'
            return render_template('register.html', error=error)

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=password,  # In production, hash the password!
            role=role,
            created_at=datetime.now()
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
        except Exception as e:
            db.session.rollback()
            error = f'Registration failed: {str(e)}'
            return render_template('register.html', error=error)

    return render_template('register.html')

#gets users path for use in database and admin side.
@app.route('/get_users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{k: v for k, v in u.__dict__.items() if not k.startswith('_')} for u in users])

#user dashboard, which shows shop / orders / log in / log out info and etc.
@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.order_date.desc()).all()

    return render_template('user/dashboard.html', user=user, orders=orders)

#gets product for display within app html, shows everything we've added and imports food categorys
@app.route('/get_products')
def get_products():
    from models.menu_item import MenuItem
    from models.food_category import FoodCategory

    items = MenuItem.query.all()
    products = []

    for item in items:
        category = FoodCategory.query.filter_by(id=item.category_id).first()
        products.append({
            'id': item.id,
            'title': item.name,
            'price': item.price,
            'stock': item.stock,
            'image_url': item.image_url,
            'book_type': category.category_name if category else 'Uncategorized'
        })

    return jsonify(products)

#app path for uploaded image files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/get_food_categories', methods=['GET'])
def get_food_categories():
    from models.food_category import FoodCategory

    categories = FoodCategory.query.all()
    return jsonify([
        {
            'id': category.id,
            'name': category.category_name,
            'description': category.description
        }
        for category in categories
    ])
#shows product details, for example we display allergy information in our products, so shows based on this code.
@app.route('/product_details/<int:product_id>')
def product_details(product_id):
    from models.menu_item import MenuItem
    from models.food_category import FoodCategory
    from models.review import Review
    from models.user import User

    if 'user_id' not in session:
        return redirect('/login')

    product = MenuItem.query.get_or_404(product_id)
    category = FoodCategory.query.get(product.category_id)

    # Join reviews with usernames using menu_item_id
    review_data = db.session.query(Review, User.username) \
        .join(User, Review.user_id == User.id) \
        .filter(Review.menu_item_id == product.id).all()

    reviews = [{
        'username': username,
        'rating': review.rating,
        'comment': review.comment
    } for review, username in review_data]

    return render_template(
        'user/product_details.html',
        product=product,
        category=category,
        reviews=reviews,
        is_admin=(session.get('role') == 'admin')
    )

#shows stock updates when changed within the admin side.
@app.route('/update_stock', methods=['POST'])
def update_stock():
    from models.menu_item import MenuItem

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    product_id = request.form.get('product_id')
    new_stock = request.form.get('stock')

    item = MenuItem.query.get(product_id)
    if item and new_stock.isdigit():
        item.stock = int(new_stock)
        db.session.commit()

    return redirect(f'/product_details/{product_id}')

#reviews section
@app.route('/submit_review', methods=['POST'])
def submit_review():
    from models.review import Review

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    user_id = session['user_id']
    product_id = request.form.get('menu_item_id')  # renamed from 'product_id'
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')

    review = Review(
        user_id=user_id,
        menu_item_id=product_id,
        rating=rating,
        comment=comment
    )

    db.session.add(review)
    db.session.commit()

    return redirect(f'/product_details/{product_id}')

#adds order to database and admin side when submit by customer
@app.route('/add_order', methods=['POST'])
def add_order():
    from models.order import Order
    from datetime import datetime
    user_id = session.get('user_id')
    if not user_id:
        user_id = request.headers.get('User-Id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(force=True)
    total_amount = float(data.get('total_amount'))

    order = Order(
        user_id=int(user_id),
        order_date=datetime.now(),
        total_amount=total_amount,
        status='Pending'
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({'order_id': order.id})

#adds the items from the shop into the order_items and postman code.
@app.route('/add_order_items', methods=['POST'])
def add_order_items():
    from models.order_item import OrderItem
    from models.menu_item import MenuItem

    data = request.get_json()
    order_id = data['order_id']
    items = data['items']

    for item in items:
        product = MenuItem.query.get(item['product_id'])

        if product and product.stock >= item['quantity']:
            # Save order item
            db.session.add(OrderItem(
                order_id=order_id,
                menu_item_id=item['product_id'],  # ✅ updated field name
                quantity=item['quantity'],
                price=product.price
            ))

            # Update stock
            product.stock -= item['quantity']
        else:
            return jsonify({'error': f'Insufficient stock for item ID {item["product_id"]}'}), 400

    db.session.commit()
    return jsonify({'success': True})

#shows shopping cart with whatever items have been added to it.
@app.route('/cart')
def cart():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')
    return render_template('user/cart.html')

#shows orders and their status on admin side.
@app.route('/orders')
def orders():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')
    return render_template('user/orders.html')

#gets all active orders within the database
@app.route('/get_orders', methods =  ['GET', 'POST'])
def get_orders():
    from models.order import Order

    if 'user_id' not in session:
        return jsonify([])

    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.order_date.desc()).all()

    return jsonify([{
        'id': o.id,
        'status': o.status,
        'order_date': o.order_date.strftime('%Y-%m-%d %H:%M'),
        'total_amount': o.total_amount
    } for o in orders])

#shows order details, wether its pending, cancelled, completed etc.
@app.route('/get_order_details/<int:order_id>')
def get_order_details(order_id):
    from models.order import Order
    from models.order_item import OrderItem
    from models.menu_item import MenuItem

    if 'user_id' not in session:
        return redirect('/login')

    order = Order.query.get_or_404(order_id)

    # Only show customer's own order
    if session.get('role') == 'customer' and order.user_id != session['user_id']:
        return "Unauthorized", 403

    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    item_details = []

    for item in order_items:
        menu_item = MenuItem.query.get(item.menu_item_id)
        item_details.append({
            'menu_item_id': item.menu_item_id,
            'name': menu_item.name,
            'image_url': menu_item.image_url,
            'quantity': item.quantity,
            'price': item.price
        })

    return render_template(
        'user/order_details.html',
        order=order,
        items=item_details
    )

#fundamentals for cancelling an order on the user side, shows on admin side when cancelled.
@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    from models.order import Order
    from models.order_item import OrderItem
    from models.menu_item import MenuItem

    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect('/login')

    order_id = request.form.get('order_id')
    order = Order.query.filter_by(id=order_id, user_id=session['user_id']).first()

    if order and order.status.strip().lower() == 'pending':
        # Cancel the order
        order.status = 'Cancelled'

        # Restore stock
        items = OrderItem.query.filter_by(order_id=order.id).all()
        for item in items:
            product = MenuItem.query.get(item.menu_item_id)
            if product:
                product.stock += item.quantity

        db.session.commit()

    return redirect(f'/get_order_details/{order_id}')

#code for admin side, setting an order as being complete.
@app.route('/set_order_delivered', methods=['POST'])
def set_order_delivered():
    from models.order import Order

    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    order.status = 'Delivered'
    db.session.commit()

    return jsonify({'message': f'Order #{order.id} marked as Delivered'})

#admin side for cancelling orders.
@app.route('/admin/cancel_order', methods=['POST'])
def admin_cancel_order():
    from models.order import Order
    from models.order_item import OrderItem
    from models.menu_item import MenuItem

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)

    if order and order.status.strip().lower() == 'pending':
        order.status = 'Cancelled'

        # Restore stock
        items = OrderItem.query.filter_by(order_id=order.id).all()
        for item in items:
            product = MenuItem.query.get(item.menu_item_id)
            if product:
                product.stock += item.quantity

        db.session.commit()

    return redirect(f'/get_order_details/{order_id}')

#admin side for delivered item.
@app.route('/admin/mark_delivered', methods=['POST'])
def admin_mark_delivered():
    from models.order import Order

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)

    if order and order.status.strip().lower() == 'pending':
        order.status = 'Delivered'
        db.session.commit()

    return redirect(f'/get_order_details/{order_id}')

#gets all orders from admin.
@app.route('/admin/get_orders')
def admin_get_orders():
    from models.order import Order
    if session.get('role') != 'admin':
        return jsonify([])
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return jsonify([{
        'id': o.id,
        'total_amount': o.total_amount
    } for o in orders])

#gets all current users on the database from the admin side
@app.route('/admin/get_users')
def admin_get_users():
    from models.user import User
    if session.get('role') != 'admin':
        return jsonify([])
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'role': u.role
    } for u in users])

#admin dashboard, shows orders, items, categories
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    return render_template('admin/dashboard.html')

#shows product page for admin, with everything we have added
@app.route('/admin/products')
def admin_products():
    from models.menu_item import MenuItem
    from models.food_category import FoodCategory

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    items = MenuItem.query.all()
    products = []

    for item in items:
        category = FoodCategory.query.get(item.category_id)
        products.append({
            'id': item.id,
            'name': item.name,
            'price': item.price,
            'stock': item.stock,
            'image_url': item.image_url,
            'category': category.category_name if category else "Uncategorized"
        })

    return render_template('admin/products.html', products=products)


import os
from werkzeug.utils import secure_filename
from datetime import datetime
#code for adding a product.
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    from models.menu_item import MenuItem
    from models.food_category import FoodCategory

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category_id = int(request.form['category_id'])

        image_file = request.files.get('image')
        image_url = ''
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join('uploads', filename)
            image_file.save(image_path)
            image_url = image_path  # Store relative path

        item = MenuItem(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            image_url=image_url,
            created_at=datetime.now(),
            created_by=session['user_id']
        )

        try:
            db.session.add(item)
            db.session.commit()
            return redirect('/admin/products')
        except Exception as e:
            db.session.rollback()
            return f"Failed to add item: {str(e)}", 500

    # GET request
    categories = FoodCategory.query.all()
    return render_template('admin/add_product.html', categories=categories)

#code for remove a product from the site.
@app.route('/admin/delete_product', methods=['POST'])
def delete_product():
    from models.menu_item import MenuItem

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    product_id = request.form.get('product_id')
    product = MenuItem.query.get(product_id)

    if product:
        db.session.delete(product)
        db.session.commit()

    return redirect('/admin/products')

#shows orders on admin side, can set status of them.
@app.route('/admin/orders')
def admin_orders():
    from models.order import Order

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    orders = Order.query.order_by(Order.order_date.desc()).all()

    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/users')
def admin_users():
    from models.user import User

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    from models.user import User

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    user_id = request.form.get('user_id')
    user = User.query.get(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()

    return redirect('/admin/users')

#food categories part for admin side, can edit add delete, etc.
@app.route('/admin/food_categories', methods=['GET', 'POST'])
def admin_food_categories():
    from models.food_category import FoodCategory

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    error_message = None

    if request.method == 'POST':
        category_name = request.form.get('category_name')
        description = request.form.get('description', '')

        if not category_name.strip():
            error_message = "Category name is required."
        else:
            exists = FoodCategory.query.filter_by(category_name=category_name).first()
            if exists:
                error_message = f"Category '{category_name}' already exists."
            else:
                new_cat = FoodCategory(category_name=category_name.strip(), description=description.strip())
                db.session.add(new_cat)
                db.session.commit()
                return redirect('/admin/food_categories')

    categories = FoodCategory.query.order_by(FoodCategory.id.desc()).all()
    return render_template('admin/food_categories.html', categories=categories, error_message=error_message)

#section for deleting a category of food.
@app.route('/admin/delete_food_category', methods=['POST'])
def delete_food_category():
    from models.food_category import FoodCategory

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    category_id = request.form.get('category_id')
    category = FoodCategory.query.get(category_id)

    if category:
        db.session.delete(category)
        db.session.commit()

    return redirect('/admin/food_categories')

#logs user out.
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)

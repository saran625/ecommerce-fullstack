# ============================================
# COMPLETE E-COMMERCE SYSTEM
# Backend API (Flask/Python)
# ============================================

"""
app.py - Main Backend Application
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import os
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize JWT
jwt = JWTManager(app)

# MongoDB Connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/')
DB_NAME = os.getenv('DB_NAME', 'ecommerce_db')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users_collection = db['users']
products_collection = db['products']
orders_collection = db['orders']
cart_collection = db['cart']
categories_collection = db['categories']

# ============================================
# UTILITY FUNCTIONS
# ============================================

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc:
        doc['_id'] = str(doc['_id'])
        if 'created_at' in doc and isinstance(doc['created_at'], datetime):
            doc['created_at'] = doc['created_at'].isoformat()
        if 'updated_at' in doc and isinstance(doc['updated_at'], datetime):
            doc['updated_at'] = doc['updated_at'].isoformat()
    return doc

def admin_required(fn):
    """Decorator for admin-only routes"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = users_collection.find_one({"_id": ObjectId(current_user_id)})
        if not user or user.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'name']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Check if user exists
        if users_collection.find_one({"email": data['email']}):
            return jsonify({"error": "Email already registered"}), 400
        
        # Create user
        user = {
            "email": data['email'],
            "password": generate_password_hash(data['password']),
            "name": data['name'],
            "phone": data.get('phone', ''),
            "role": "customer",
            "address": {
                "street": data.get('street', ''),
                "city": data.get('city', ''),
                "state": data.get('state', ''),
                "zipcode": data.get('zipcode', ''),
                "country": data.get('country', '')
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = users_collection.insert_one(user)
        
        # Create access token
        access_token = create_access_token(identity=str(result.inserted_id))
        
        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "user_id": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password required"}), 400
        
        user = users_collection.find_one({"email": data['email']})
        
        if not user or not check_password_hash(user['password'], data['password']):
            return jsonify({"error": "Invalid credentials"}), 401
        
        access_token = create_access_token(identity=str(user['_id']))
        
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "id": str(user['_id']),
                "email": user['email'],
                "name": user['name'],
                "role": user['role']
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.pop('password')
        return jsonify({"user": serialize_doc(user)}), 200
    
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================
# PRODUCT ROUTES
# ============================================

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products with pagination and filtering"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 12))
        category = request.args.get('category')
        search = request.args.get('search')
        
        query = {"is_active": True}
        
        if category:
            query['category'] = category
        
        if search:
            query['$or'] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        skip = (page - 1) * limit
        
        products = list(products_collection.find(query).skip(skip).limit(limit))
        total = products_collection.count_documents(query)
        
        return jsonify({
            "products": [serialize_doc(p) for p in products],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }), 200
    
    except Exception as e:
        logger.error(f"Get products error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get single product"""
    try:
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"product": serialize_doc(product)}), 200
    
    except Exception as e:
        logger.error(f"Get product error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
@admin_required
def create_product():
    """Create new product (Admin only)"""
    try:
        data = request.get_json()
        
        product = {
            "name": data['name'],
            "description": data['description'],
            "price": float(data['price']),
            "category": data['category'],
            "stock": int(data['stock']),
            "images": data.get('images', []),
            "specifications": data.get('specifications', {}),
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = products_collection.insert_one(product)
        
        return jsonify({
            "message": "Product created successfully",
            "product_id": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        logger.error(f"Create product error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    """Update product (Admin only)"""
    try:
        data = request.get_json()
        data['updated_at'] = datetime.now()
        
        result = products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": data}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"message": "Product updated successfully"}), 200
    
    except Exception as e:
        logger.error(f"Update product error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================
# CART ROUTES
# ============================================

@app.route('/api/cart', methods=['GET'])
@jwt_required()
def get_cart():
    """Get user's cart"""
    try:
        user_id = get_jwt_identity()
        cart = cart_collection.find_one({"user_id": user_id})
        
        if not cart:
            return jsonify({"cart": {"items": [], "total": 0}}), 200
        
        # Populate product details
        for item in cart['items']:
            product = products_collection.find_one({"_id": ObjectId(item['product_id'])})
            if product:
                item['product_details'] = serialize_doc(product)
        
        return jsonify({"cart": serialize_doc(cart)}), 200
    
    except Exception as e:
        logger.error(f"Get cart error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    """Add item to cart"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        product_id = data['product_id']
        quantity = int(data.get('quantity', 1))
        
        # Verify product exists and has stock
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        if product['stock'] < quantity:
            return jsonify({"error": "Insufficient stock"}), 400
        
        # Get or create cart
        cart = cart_collection.find_one({"user_id": user_id})
        
        if not cart:
            cart = {
                "user_id": user_id,
                "items": [],
                "total": 0,
                "updated_at": datetime.now()
            }
        
        # Check if product already in cart
        existing_item = next((item for item in cart['items'] if item['product_id'] == product_id), None)
        
        if existing_item:
            existing_item['quantity'] += quantity
        else:
            cart['items'].append({
                "product_id": product_id,
                "quantity": quantity,
                "price": product['price']
            })
        
        # Calculate total
        cart['total'] = sum(item['quantity'] * item['price'] for item in cart['items'])
        cart['updated_at'] = datetime.now()
        
        cart_collection.update_one(
            {"user_id": user_id},
            {"$set": cart},
            upsert=True
        )
        
        return jsonify({"message": "Item added to cart", "cart": serialize_doc(cart)}), 200
    
    except Exception as e:
        logger.error(f"Add to cart error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cart/remove/<product_id>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(product_id):
    """Remove item from cart"""
    try:
        user_id = get_jwt_identity()
        
        cart = cart_collection.find_one({"user_id": user_id})
        if not cart:
            return jsonify({"error": "Cart not found"}), 404
        
        cart['items'] = [item for item in cart['items'] if item['product_id'] != product_id]
        cart['total'] = sum(item['quantity'] * item['price'] for item in cart['items'])
        cart['updated_at'] = datetime.now()
        
        cart_collection.update_one(
            {"user_id": user_id},
            {"$set": cart}
        )
        
        return jsonify({"message": "Item removed from cart"}), 200
    
    except Exception as e:
        logger.error(f"Remove from cart error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================
# ORDER ROUTES
# ============================================

@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Create new order"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Get cart
        cart = cart_collection.find_one({"user_id": user_id})
        if not cart or not cart['items']:
            return jsonify({"error": "Cart is empty"}), 400
        
        # Create order
        order = {
            "user_id": user_id,
            "items": cart['items'],
            "total": cart['total'],
            "shipping_address": data['shipping_address'],
            "payment_method": data['payment_method'],
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orders_collection.insert_one(order)
        
        # Update product stock
        for item in cart['items']:
            products_collection.update_one(
                {"_id": ObjectId(item['product_id'])},
                {"$inc": {"stock": -item['quantity']}}
            )
        
        # Clear cart
        cart_collection.delete_one({"user_id": user_id})
        
        return jsonify({
            "message": "Order created successfully",
            "order_id": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        logger.error(f"Create order error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():
    """Get user's orders"""
    try:
        user_id = get_jwt_identity()
        orders = list(orders_collection.find({"user_id": user_id}).sort("created_at", -1))
        
        return jsonify({"orders": [serialize_doc(o) for o in orders]}), 200
    
    except Exception as e:
        logger.error(f"Get orders error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Get single order"""
    try:
        user_id = get_jwt_identity()
        order = orders_collection.find_one({"_id": ObjectId(order_id), "user_id": user_id})
        
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        return jsonify({"order": serialize_doc(order)}), 200
    
    except Exception as e:
        logger.error(f"Get order error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================
# CATEGORIES ROUTES
# ============================================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    try:
        categories = list(categories_collection.find({"is_active": True}))
        return jsonify({"categories": [serialize_doc(c) for c in categories]}), 200
    
    except Exception as e:
        logger.error(f"Get categories error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================
# INITIALIZE SAMPLE DATA
# ============================================

def init_sample_data():
    """Initialize database with sample data"""
    try:
        # Create admin user if not exists
        if users_collection.count_documents({"role": "admin"}) == 0:
            admin = {
                "email": "admin@ecommerce.com",
                "password": generate_password_hash("admin123"),
                "name": "Admin User",
                "role": "admin",
                "created_at": datetime.now()
            }
            users_collection.insert_one(admin)
            logger.info("Admin user created")
        
        # Create categories
        if categories_collection.count_documents({}) == 0:
            categories = [
                {"name": "Electronics", "slug": "electronics", "is_active": True},
                {"name": "Clothing", "slug": "clothing", "is_active": True},
                {"name": "Books", "slug": "books", "is_active": True},
                {"name": "Home & Garden", "slug": "home-garden", "is_active": True}
            ]
            categories_collection.insert_many(categories)
            logger.info("Categories created")
        
        # Create sample products
        if products_collection.count_documents({}) == 0:
            products = [
                {
                    "name": "Wireless Headphones",
                    "description": "Premium wireless headphones with noise cancellation",
                    "price": 99.99,
                    "category": "Electronics",
                    "stock": 50,
                    "images": ["/images/headphones.jpg"],
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Cotton T-Shirt",
                    "description": "Comfortable 100% cotton t-shirt",
                    "price": 19.99,
                    "category": "Clothing",
                    "stock": 100,
                    "images": ["/images/tshirt.jpg"],
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Programming Book",
                    "description": "Complete guide to Python programming",
                    "price": 39.99,
                    "category": "Books",
                    "stock": 30,
                    "images": ["/images/book.jpg"],
                    "is_active": True,
                    "created_at": datetime.now()
                }
            ]
            products_collection.insert_many(products)
            logger.info("Sample products created")
    
    except Exception as e:
        logger.error(f"Init data error: {str(e)}")

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    logger.info("Starting E-commerce Backend API")
    
    # Initialize sample data
    init_sample_data()
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
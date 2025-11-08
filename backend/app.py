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
# MongoDB Connection with better error handling
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/')
DB_NAME = os.getenv('DB_NAME', 'ecommerce_db')

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Test the connection
    client.admin.command('ping')
    logger.info("✅ MongoDB connected successfully")
    
    db = client[DB_NAME]
    
except Exception as e:
    logger.error(f"❌ MongoDB connection failed: {str(e)}")
    # You might want to exit or handle this differently
    raise e

# Collections with retry logic
def get_collection(collection_name):
    """Get collection with connection check"""
    try:
        return db[collection_name]
    except Exception as e:
        logger.error(f"Error accessing collection {collection_name}: {str(e)}")
        raise e

users_collection = get_collection('users')
products_collection = get_collection('products')
orders_collection = get_collection('orders')
cart_collection = get_collection('cart')
categories_collection = get_collection('categories')
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
                {"name": "Smartphones", "slug": "smartphones", "is_active": True},
                {"name": "Laptops", "slug": "laptops", "is_active": True},
                {"name": "Accessories", "slug": "accessories", "is_active": True}
            ]
            categories_collection.insert_many(categories)
            logger.info("Categories created")
        
        # Create mobile products (10 phones with 10% discount)
        if products_collection.count_documents({}) == 0:
            mobile_products = [
                {
                    "name": "iPhone 15 Pro Max",
                    "description": "6.7-inch Super Retina XDR display, Titanium design, A17 Pro chip",
                    "price": 1199.99,
                    "original_price": 1333.32,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 25,
                    "images": ["https://via.placeholder.com/400x300/007ACC/FFFFFF?text=iPhone+15+Pro"],
                    "specifications": {
                        "storage": "256GB",
                        "color": "Natural Titanium",
                        "screen": "6.7 inch",
                        "camera": "48MP Main"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Samsung Galaxy S24 Ultra",
                    "description": "Galaxy AI, Snapdragon 8 Gen 3, 200MP camera",
                    "price": 1299.99,
                    "original_price": 1444.43,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 30,
                    "images": ["https://via.placeholder.com/400x300/FF6B6B/FFFFFF?text=Galaxy+S24+Ultra"],
                    "specifications": {
                        "storage": "512GB",
                        "color": "Titanium Black",
                        "screen": "6.8 inch",
                        "camera": "200MP"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Google Pixel 8 Pro",
                    "description": "Google AI, Tensor G3 chip, Best-in-class camera",
                    "price": 999.99,
                    "original_price": 1111.10,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 20,
                    "images": ["https://via.placeholder.com/400x300/4ECDC4/FFFFFF?text=Pixel+8+Pro"],
                    "specifications": {
                        "storage": "128GB",
                        "color": "Obsidian",
                        "screen": "6.7 inch",
                        "camera": "50MP"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "OnePlus 12",
                    "description": "Snapdragon 8 Gen 3, Hasselblad camera, 100W charging",
                    "price": 799.99,
                    "original_price": 888.88,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 35,
                    "images": ["https://via.placeholder.com/400x300/45B7D1/FFFFFF?text=OnePlus+12"],
                    "specifications": {
                        "storage": "256GB",
                        "color": "Silky Black",
                        "screen": "6.82 inch",
                        "camera": "50MP"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Xiaomi 14 Pro",
                    "description": "Leica camera system, Snapdragon 8 Gen 3, HyperOS",
                    "price": 899.99,
                    "original_price": 999.99,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 28,
                    "images": ["https://via.placeholder.com/400x300/96CEB4/FFFFFF?text=Xiaomi+14+Pro"],
                    "specifications": {
                        "storage": "512GB",
                        "color": "Black",
                        "screen": "6.73 inch",
                        "camera": "50MP Leica"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Nothing Phone 2",
                    "description": "Glyph interface, Snapdragon 8+ Gen 1, Unique design",
                    "price": 599.99,
                    "original_price": 666.66,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 40,
                    "images": ["https://via.placeholder.com/400x300/F7DC6F/FFFFFF?text=Nothing+Phone+2"],
                    "specifications": {
                        "storage": "256GB",
                        "color": "White",
                        "screen": "6.7 inch",
                        "camera": "50MP"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Asus ROG Phone 8",
                    "description": "Gaming smartphone, Snapdragon 8 Gen 3, AirTrigger buttons",
                    "price": 1099.99,
                    "original_price": 1222.21,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 15,
                    "images": ["https://via.placeholder.com/400x300/BB8FCE/FFFFFF?text=ROG+Phone+8"],
                    "specifications": {
                        "storage": "512GB",
                        "color": "Phantom Black",
                        "screen": "6.78 inch",
                        "camera": "50MP"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Vivo X100 Pro",
                    "description": "Zeiss camera, Dimensity 9300, 100W charging",
                    "price": 949.99,
                    "original_price": 1055.54,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 22,
                    "images": ["https://via.placeholder.com/400x300/85C1E9/FFFFFF?text=Vivo+X100+Pro"],
                    "specifications": {
                        "storage": "512GB",
                        "color": "Starry Blue",
                        "screen": "6.78 inch",
                        "camera": "50MP Zeiss"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Oppo Find X7 Ultra",
                    "description": "Dual periscope cameras, Snapdragon 8 Gen 3, 100W charging",
                    "price": 1199.99,
                    "original_price": 1333.32,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 18,
                    "images": ["https://via.placeholder.com/400x300/F8C471/FFFFFF?text=Oppo+X7+Ultra"],
                    "specifications": {
                        "storage": "512GB",
                        "color": "Ocean Blue",
                        "screen": "6.82 inch",
                        "camera": "50MP Dual Periscope"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                },
                {
                    "name": "Realme GT 5 Pro",
                    "description": "Flagship killer, Snapdragon 8 Gen 3, 100W charging",
                    "price": 699.99,
                    "original_price": 777.77,
                    "discount": 10,
                    "category": "Smartphones",
                    "stock": 45,
                    "images": ["https://via.placeholder.com/400x300/82E0AA/FFFFFF?text=Realme+GT+5+Pro"],
                    "specifications": {
                        "storage": "256GB",
                        "color": "Bright Moon",
                        "screen": "6.78 inch",
                        "camera": "50MP Sony"
                    },
                    "is_active": True,
                    "created_at": datetime.now()
                }
            ]
            products_collection.insert_many(mobile_products)
            logger.info("10 Mobile phones added with 10% discount")
    
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
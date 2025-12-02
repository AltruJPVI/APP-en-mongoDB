from flask import Blueprint, request, jsonify, current_app
from app.schemas.products import ProductCreate, ProductResponse
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone


# Create blueprint for products
bp = Blueprint('products', __name__, url_prefix='/api/products')

'''
--PRODUCTS--

POST - create product
GET - view products
GET - view 1 specific product
DELETE - delete product

'''

# ==================== CREATE PRODUCT ====================

@bp.route('', methods=['POST'])
def create_product():
    """
    POST /api/products
    Body: {
        "name": "Wilson Pro Racket",
        "price": 120.50,
        "brand": "Wilson",
        "category": "rackets",
        "gender": "unisex",
        "stock": 50,  // Or use sizes + stocks
        ...
    }
    """
    try:
        # Validate data with Pydantic
        product_data = ProductCreate(**request.json)
        
        # Prepare document for MongoDB
        product_dict = product_data.model_dump(exclude_none=True)
        
        # Add metadata
        product_dict['date'] = datetime.now(timezone.utc)
        product_dict['total_comments'] = 0
        product_dict['average_rating'] = None
        product_dict['total_ratings'] = 0
        
        # Insert into MongoDB
        result = current_app.db.products.insert_one(product_dict)
        
        # Prepare response
        product_dict['_id'] = str(result.inserted_id)
        product_dict['comments'] = []
        
        product_response = ProductResponse(**product_dict)
        
        return jsonify({
            "message": "Product created successfully",
            "product": product_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LIST PRODUCTS (WITH SIMPLIFIED FILTERS) ====================

@bp.route('', methods=['GET'])
def list_products():
    """
    GET /api/products?category=rackets&gender=unisex&price_min=50&price_max=200
                      &brand=Wilson&page=1&limit=20
    
    Available filters:
    - category: rackets, shoes, shirts, etc.
    - gender: male, female, unisex
    - price_min / price_max: price range
    - brand: Wilson, Nike, Adidas, etc.
    - page: page number (default: 1)
    - limit: products per page (default: 20, max: 100)
    """
    try:
        # Build MongoDB filter
        filter_query = {"active": True}  # Only active products
        
        # Filter by category
        category = request.args.get('category')
        if category:
            filter_query['category'] = category
        
        # Filter by gender
        gender = request.args.get('gender')
        if gender:
            filter_query['gender'] = gender
        
        # Filter by brand
        brand = request.args.get('brand')
        if brand:
            filter_query['brand'] = {'$regex': brand, '$options': 'i'}  # Case insensitive
        
        # Filter by price range
        price_min = request.args.get('price_min', type=float)
        price_max = request.args.get('price_max', type=float)
        if price_min is not None or price_max is not None:
            filter_query['price'] = {}
            if price_min is not None:
                filter_query['price']['$gte'] = price_min
            if price_max is not None:
                filter_query['price']['$lte'] = price_max
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # Maximum 100 products per page
        skip = (page - 1) * limit
        
        # Sort by creation date (most recent first)
        products_cursor = current_app.db.products.find(filter_query).sort(
            'creation_date', -1
        ).skip(skip).limit(limit)
        
        # Convert to list
        products = []
        for product in products_cursor:
            product['_id'] = str(product['_id'])
            # Add default fields if they don't exist
            product.setdefault('comments', [])
            product.setdefault('total_comments', 0)
            product.setdefault('average_rating', None)
            product.setdefault('total_ratings', 0)
                
            products.append(ProductResponse(**product).model_dump(exclude_none=True))
        
        # Count total products (for pagination)
        total_products = current_app.db.products.count_documents(filter_query)
        total_pages = (total_products + limit - 1) // limit
        
        return jsonify({
            "products": products,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_products": total_products,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VIEW PRODUCT DETAILS ====================

@bp.route('/<product_id>', methods=['GET'])
def view_product(product_id):
    """
    GET /api/products/:product_id
    View complete details of a product
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(product_id):
            return jsonify({"error": "Invalid product ID"}), 400
        
        # Find product
        product = current_app.db.products.find_one({"_id": ObjectId(product_id)})
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Convert _id to string
        product['_id'] = str(product['_id'])
        
        # Add default fields if they don't exist
        product.setdefault('comments', [])
        product.setdefault('total_comments', 0)
        product.setdefault('average_rating', None)
        product.setdefault('total_ratings', 0)
        
        # Validate with Pydantic
        product_response = ProductResponse(**product)
        
        return jsonify(product_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== DELETE PRODUCT ====================

@bp.route('/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    DELETE /api/products/:product_id?soft=true
    Body: {
        "role": "admin"  // user, company, admin
    }
    
    DEMO: Only admin or company can delete products
    
    Query params:
    - soft: true (default) = logical deletion (mark as inactive)
    - soft: false = physical deletion (permanent)
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(product_id):
            return jsonify({"error": "Invalid product ID"}), 400
        
        # Find product
        product = current_app.db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Get data from body
        data = request.json or {}
        role = data.get('role', 'user')
        
        # ✅ PERMISSION VERIFICATION: Only admin or company can delete
        if role not in ['admin', 'company']:
            return jsonify({"error": "Only admin or company can delete products"}), 403
        
        # Deletion type
        use_soft_delete = request.args.get('soft', 'true').lower() == 'true'
        
        if use_soft_delete:
            # Logical deletion: Only mark as inactive
            current_app.db.products.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": {
                    "active": False,
                    "deletion_date": datetime.now(timezone.utc)
                }}
            )
            message = "Product deactivated successfully"
        else:
            # Physical deletion: Delete permanently
            current_app.db.products.delete_one({"_id": ObjectId(product_id)})
            
            # Also delete its comments
            current_app.db.comments.delete_many({
                "entity_type": "product",
                "entity_id": product_id
            })
            
            message = "Product deleted permanently"
        
        return jsonify({"message": message}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
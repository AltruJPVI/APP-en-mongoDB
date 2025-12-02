from flask import Blueprint, request, jsonify, current_app
from app.schemas.users import UserResponse, UserUpdate, CartItem
from pydantic import ValidationError
from bson import ObjectId

bp = Blueprint('users', __name__, url_prefix='/api/users')

# ==================== PROFILE ====================
"""http operation:

--PROFILE--

GET - view profile 
PUT - update profile

--CART--

GET - view cart
DELETE - remove a product from the cart
POST - add to cart
DELETE - empty cart

""" 

@bp.route('/<user_id>', methods=['GET'])
def get_profile(user_id):
    """
    GET /api/users/:user_id
    Get a user's profile
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user['_id'] = str(user['_id'])
        user.pop('password', None)
        
        user_response = UserResponse(**user)
        
        return jsonify(user_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/<user_id>', methods=['PUT'])
def update_profile(user_id):
    """
    PUT /api/users/:user_id
    Body: {"name": "...", "level": "...", "location": {...}}
    Update profile information
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        update_data = UserUpdate(**request.json)
        
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            return jsonify({"error": "No data to update"}), 400
        
        result = current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        user['_id'] = str(user['_id'])
        user.pop('password', None)
        
        user_response = UserResponse(**user)
        
        return jsonify({
            "message": "profile updated",
            "user": user_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== CART ====================

@bp.route('/<user_id>/cart', methods=['GET'])
def view_cart(user_id):
    """
    GET /api/users/:user_id/cart
    View the user's shopping cart
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        user = current_app.db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"cart": 1}  
        )
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        cart = user.get('cart', [])
        
        total = sum(item['price'] * item['quantity'] for item in cart)
        
        return jsonify({
            "cart": cart,
            "total_items": len(cart),
            "total_price": round(total, 2)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<user_id>/cart', methods=['POST'])
def add_to_cart(user_id):
    """
    POST /api/users/:user_id/cart
    Body: {
        "product_id": "...",
        "name": "Wilson Racket",
        "price": 120.50,
        "quantity": 1,
        "size": "M" (optional)
    }
    Add a product to the cart
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        item_data = CartItem(**request.json)
        
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        cart = user.get('cart', [])
        existing_product_index = None

        for i, item in enumerate(cart):
            if (item['product_id'] == item_data.product_id and 
                item.get('size') == item_data.size):
                existing_product_index = i
                break
        
        if existing_product_index is not None:
            cart[existing_product_index]['quantity'] += item_data.quantity
            message = "Quantity updated in the cart"
        else:
            cart.append(item_data.model_dump(exclude_none=True))
            message = "Product added to the cart"
        
        current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"cart": cart}}
        )
        
        total = sum(item['price'] * item['quantity'] for item in cart)
        
        return jsonify({
            "message": message,
            "cart": cart,
            "total_items": len(cart),
            "total_price": round(total, 2) 
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<user_id>/cart/<product_id>', methods=['DELETE'])
def remove_from_cart(user_id, product_id):
    """
    DELETE /api/users/:user_id/cart/:product_id?size=M
    Remove a product from the cart
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        size = request.args.get('size')
        
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        cart = user.get('cart', [])
        
        new_cart = [
            item for item in cart 
            if not (item['product_id'] == product_id and 
                   item.get('size') == size) 
        ]
        
        if len(cart) == len(new_cart):
            return jsonify({"error": "Product not found in the cart"}), 404
        
        current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"cart": new_cart}}
        )
        
        total = sum(item['price'] * item['quantity'] for item in new_cart)
        
        return jsonify({
            "message": "Product removed from cart",
            "cart": new_cart,
            "total_items": len(new_cart),
            "total_price": round(total, 2) 
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<user_id>/cart', methods=['DELETE'])
def empty_cart(user_id):
    """
    DELETE /api/users/:user_id/cart
    Empty the entire cart
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        result = current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"cart": []}}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "message": "Cart emptied successfully",
            "cart": [],
            "total_items": 0,
            "total_price": 0 
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




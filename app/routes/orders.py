from flask import Blueprint, request, jsonify, current_app
from app.schemas.orders import OrderCreate, OrderResponse
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

# Create blueprint for orders
bp = Blueprint('orders', __name__, url_prefix='/api/orders')

'''
--ORDERS--

POST - create order
GET - view 1 specific order

'''
# ==================== CREATE ORDER (WITH ACID TRANSACTIONS) ====================

@bp.route('', methods=['POST'])
def create_order():
    """
    POST /api/orders
    Body: {
        "user_id": "507f1f77bcf86cd799439011",
        "items": [
            {
                "product_id": "65abc123",
                "name": "Wilson Racket",
                "price": 120.50,
                "quantity": 2,
                "size": "M",  // Optional
                "image": "url.jpg"  // Optional
            }
        ],
        "total": 241.00,
        "shipping_address": {
            "street": "Main Street 123",
            "city": "Madrid",
            "postal_code": "28001",
            "phone": "612345678"
        },
        "payment_method": "card"
    }
    
    IMPORTANT: Uses ACID transactions to guarantee:
    1. Order is created
    2. Product stock is reduced
    3. User's cart is emptied
    If ANY operation fails → Complete ROLLBACK
    """
    try:
        # Validate data with Pydantic
        order_data = OrderCreate(**request.json)
        
        # Validate that the user exists
        if not ObjectId.is_valid(order_data.user_id):
            return jsonify({"error": "Invalid user ID"}), 400
        
        user = current_app.db.users.find_one({"_id": ObjectId(order_data.user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Validate that all products exist and have sufficient stock
        validation = _validate_product_stock(order_data.items)
        if not validation["valid"]:
            return jsonify({"error": validation["message"]}), 400
        
        # ==================== START ACID TRANSACTION ====================
        # Start MongoDB session for transaction
        session = current_app.mongo_client.start_session()
        
        try:
            with session.start_transaction():
                # 1. CREATE ORDER
                order_dict = order_data.model_dump(exclude_none=True)
                order_dict['order_number'] = _generate_order_number()
                order_dict['order_date'] = datetime.now(timezone.utc)
                
                # Insert order (within transaction)
                result = current_app.db.orders.insert_one(order_dict, session=session)
                order_id = result.inserted_id
                
                # 2. REDUCE PRODUCT STOCK
                for item in order_data.items:
                    # Validate product ObjectId
                    if not ObjectId.is_valid(item.product_id):
                        raise Exception(f"Invalid product ID: {item.product_id}")
                    
                    product = current_app.db.products.find_one(
                        {"_id": ObjectId(item.product_id)},
                        session=session
                    )
                    
                    if not product:
                        raise Exception(f"Product not found: {item.name}")
                    
                    # Reduce stock according to type
                    if item.size:
                        # Product with sizes
                        if 'stocks' not in product:
                            raise Exception(f"Product {item.name} has no sizes defined")
                        
                        # Find the size and reduce stock
                        size_found = False
                        for stock_item in product.get('stocks', []):
                            if stock_item['size'] == item.size:
                                new_stock = stock_item['stock'] - item.quantity
                                if new_stock < 0:
                                    raise Exception(
                                        f"Insufficient stock for {item.name} size {item.size}"
                                    )
                                
                                # Update stock for specific size
                                current_app.db.products.update_one(
                                    {
                                        "_id": ObjectId(item.product_id),
                                        "stocks.size": item.size
                                    },
                                    {"$set": {"stocks.$.stock": new_stock}},
                                    session=session
                                )
                                size_found = True
                                break
                        
                        if not size_found:
                            raise Exception(
                                f"Size {item.size} not found for {item.name}"
                            )
                    else:
                        # Product with simple stock
                        current_stock = product.get('stock', 0)
                        new_stock = current_stock - item.quantity
                        
                        if new_stock < 0:
                            raise Exception(f"Insufficient stock for {item.name}")
                        
                        # Update simple stock
                        current_app.db.products.update_one(
                            {"_id": ObjectId(item.product_id)},
                            {"$set": {"stock": new_stock}},
                            session=session
                        )
                
                # 3. EMPTY USER'S CART
                current_app.db.users.update_one(
                    {"_id": ObjectId(order_data.user_id)},
                    {"$set": {"cart": []}},
                    session=session
                )
                
                # If we get here, everything OK → Automatic COMMIT when exiting the with
                
        except Exception as e:
            # If anything fails → Automatic ROLLBACK
            raise e
        finally:
            session.end_session()
        
        # ==================== END TRANSACTION ====================
        
        # Get the created order to return
        order = current_app.db.orders.find_one({"_id": order_id})
        order['_id'] = str(order['_id'])
        
        order_response = OrderResponse(**order)
        
        return jsonify({
            "message": "Order created successfully",
            "order": order_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ==================== VIEW ORDER DETAILS ====================

@bp.route('/<order_id>', methods=['GET'])
def view_order(order_id):
    """
    GET /api/orders/:order_id

    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(order_id):
            return jsonify({"error": "Invalid order ID"}), 400
        
        # Search for order
        order = current_app.db.orders.find_one({"_id": ObjectId(order_id)})
        
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        order['_id'] = str(order['_id'])
        
        order_response = OrderResponse(**order)
        
        return jsonify(order_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== HELPER FUNCTIONS ====================

def _validate_product_stock(items):
    """
    Validate that all products exist and have sufficient stock
    BEFORE starting the transaction
    """
    for item in items:
        # Validate ObjectId
        if not ObjectId.is_valid(item.product_id):
            return {
                "valid": False,
                "message": f"Invalid product ID: {item.product_id}"
            }
        
        # Search for product
        product = current_app.db.products.find_one({"_id": ObjectId(item.product_id)})
        
        if not product:
            return {
                "valid": False,
                "message": f"Product not found: {item.name}"
            }
        
        # Verify that it's active
        if not product.get('active', True):
            return {
                "valid": False,
                "message": f"Product {item.name} is no longer available"
            }
        
        # Verify stock according to type
        if item.size:
            # Product with sizes
            if 'stocks' not in product:
                return {
                    "valid": False,
                    "message": f"Product {item.name} has no sizes defined"
                }
            
            size_found = False
            for stock_item in product.get('stocks', []):
                if stock_item['size'] == item.size:
                    if stock_item['stock'] < item.quantity:
                        return {
                            "valid": False,
                            "message": f"Insufficient stock for {item.name} size {item.size}. Available: {stock_item['stock']}"
                        }
                    size_found = True
                    break
            
            if not size_found:
                return {
                    "valid": False,
                    "message": f"Size {item.size} not available for {item.name}"
                }
        else:
            # Product with simple stock
            current_stock = product.get('stock', 0)
            if current_stock < item.quantity:
                return {
                    "valid": False,
                    "message": f"Insufficient stock for {item.name}. Available: {current_stock}"
                }
    
    return {"valid": True, "message": ""}


def _generate_order_number():
    """
    Generate unique order number
    Format: ORD-YYYY-NNNNNN
    Example: ORD-2025-000123
    """
    year = datetime.now().year
    
    # Count orders from current year
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    orders_year = current_app.db.orders.count_documents({
        "order_date": {"$gte": year_start}
    })
    
    # Increment counter
    number = orders_year + 1
    
    # Format: ORD-2025-000123
    order_number = f"ORD-{year}-{number:06d}"
    
    return order_number
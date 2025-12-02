from flask import Blueprint, request, jsonify, current_app
from app.schemas.comments import CommentCreate, CommentResponse,EntityType,LastComment
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone


# Create blueprint for comments
bp = Blueprint('comments', __name__, url_prefix='/api/comments')


"""HTTP operations:

--COMMENTS--

POST - create comment 
GET - view 1 specific comment
DELETE - delete comment

POST - give like

Useful functions
""" 

@bp.route('', methods=['POST'])
def create_comment():
    """
    POST /api/comments
    Body: {
        "entity_type": "product",  // "product", "event", "post"
        "entity_id": "507f1f77bcf86cd799439011",
        "user_id": "60d5ec49f1b2c8b1f8e4e1a1",
        "user_name": "John Doe",
        "text": "Excellent product!",
        "rating": 5,  // Optional (1-5), only for products
        "reply_to": "..."  // Optional, parent comment ID
    }
    
    TODO: Add @require_auth and get user_id/user_name from token
    """
    try:
        comment_data = CommentCreate(**request.json)
        # Verify that the entity exists
        entity_collection = _get_collection_by_type(comment_data.entity_type)
        
        if not ObjectId.is_valid(comment_data.entity_id):
            return jsonify({"error": "Invalid entity ID"}), 400

        entity = entity_collection.find_one({"_id": ObjectId(comment_data.entity_id)})
        if not entity:
            return jsonify({"error": f"{comment_data.entity_type.capitalize()} not found"}), 404
        
        # If it's a reply, verify that the parent comment exists
        if comment_data.reply_to:
            if not ObjectId.is_valid(comment_data.reply_to):
                return jsonify({"error": "Invalid parent comment ID"}), 400
            
            parent_comment = current_app.db.comments.find_one({"_id": ObjectId(comment_data.reply_to)})
            if not parent_comment:
                return jsonify({"error": "Parent comment not found"}), 404
        
        # Prepare document for MongoDB
        comment_dict = comment_data.model_dump(exclude_none=True)
        comment_dict['date'] = datetime.now(timezone.utc)
        comment_dict['likes'] = 0
        
        # Insert into MongoDB
        result = current_app.db.comments.insert_one(comment_dict)

        # Update comment counter in the entity
        entity_collection.update_one(
            {"_id": ObjectId(comment_data.entity_id)},
            {"$inc": {"total_comments": 1}}
        )
        
        # If the comment has a rating (products), recalculate average
        if comment_data.rating and comment_data.entity_type == EntityType.product:
            _recalculate_product_rating(comment_data.entity_id)
        
        # Update recent comments of the entity
        _update_recent_comments(
            comment_data.entity_type, 
            comment_data.entity_id
        )
        
        # Prepare response
        comment_dict['_id'] = str(result.inserted_id)
        comment_response = CommentResponse(**comment_dict)
        
        return jsonify({
            "message": "Comment created successfully",
            "comment": comment_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VIEW COMMENT ====================

@bp.route('/<comment_id>', methods=['GET'])
def view_comment(comment_id):
    """
    GET /api/comments/:comment_id
    View a specific comment
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "Invalid comment ID"}), 400
        
        # Search for comment
        comment = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        # Convert _id to string
        comment['_id'] = str(comment['_id'])
        
        comment_response = CommentResponse(**comment)
        
        return jsonify(comment_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== DELETE COMMENT ====================

@bp.route('/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """
    DELETE /api/comments/:comment_id
    Body: {
        "user_id": "507f...",  // ID of the user making the request
        "role": "user"  // user, company, admin
    }
    
    Only the author or an admin can delete
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "Invalid comment ID"}), 400
        
        # Search for comment
        comment = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        # Get data from body
        data = request.json or {}
        request_user_id = data.get('user_id')
        role = data.get('role', 'user')
        
        if not request_user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # ✅ PERMISSION VERIFICATION: Only the author or admin can delete
        is_author = comment['user_id'] == request_user_id
        is_admin = role == 'admin'
        
        if not (is_author or is_admin):
            return jsonify({"error": "Only the author or an admin can delete this comment"}), 403
        
        # Save info before deleting
        entity_type = comment['entity_type']
        entity_id = comment['entity_id']
        has_rating = comment.get('rating') is not None
        
        # Delete comment
        current_app.db.comments.delete_one({"_id": ObjectId(comment_id)})
        
        # Decrement counter in the entity
        entity_collection = _get_collection_by_type(entity_type)
        entity_collection.update_one(
            {"_id": ObjectId(entity_id)},
            {"$inc": {"total_comments": -1}}
        )
        
        # If it had a rating, recalculate average
        if has_rating and entity_type == 'product':
            _recalculate_product_rating(entity_id)
        
        # Update recent comments
        _update_recent_comments(entity_type, entity_id)
        
        return jsonify({"message": "Comment deleted successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ==================== GIVE/REMOVE LIKE ====================

@bp.route('/<comment_id>/like', methods=['POST'])
def toggle_like(comment_id):
    """
    POST /api/comments/:comment_id/like
    Body: {"user_id": "..."}
    
    Give or remove like from a comment (toggle)
    TODO: Get user_id from token
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "Invalid comment ID"}), 400
        
        # TODO: Get from token
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # Search for comment
        comment = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        
        # Check if the user already liked it
        # For this we need an array of users who liked
        # We'll use a separate collection or a field in the comment
        
        # Option: Use a 'liked_by_users' array in the comment
        liked_by_users = comment.get('liked_by_users', [])
        
        if user_id in liked_by_users:
            # Remove like
            current_app.db.comments.update_one(
                {"_id": ObjectId(comment_id)},
                {
                    "$pull": {"liked_by_users": user_id},
                    "$inc": {"likes": -1}
                }
            )
            message = "Like removed"
            new_likes = comment['likes'] - 1
        else:
            # Give like
            current_app.db.comments.update_one(
                {"_id": ObjectId(comment_id)},
                {
                    "$addToSet": {"liked_by_users": user_id},
                    "$inc": {"likes": 1}
                }
            )
            message = "Like added"
            new_likes = comment['likes'] + 1
        
        return jsonify({
            "message": message,
            "likes": new_likes
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== HELPER FUNCTIONS ====================

def _get_collection_by_type(entity_type: str):
    """Get MongoDB collection based on entity type"""
    collections = {
        'product': current_app.db.products,
        'post': current_app.db.posts
    }
    return collections.get(entity_type)


def _recalculate_product_rating(product_id: str):
    """Recalculate the average rating of a product"""
    try:
        # Aggregate all comments with rating for the product
        pipeline = [
            {
                "$match": {
                    "entity_type": "product",
                    "entity_id": product_id,
                    "rating": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "average": {"$avg": "$rating"},
                    "total": {"$sum": 1}
                }
            }
        ]
        
        result = list(current_app.db.comments.aggregate(pipeline))
        
        if result:
            average = round(result[0]['average'], 2)
            total = result[0]['total']
        else:
            average = None
            total = 0
        
        # Update product
        current_app.db.products.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "average_rating": average,
                    "total_ratings": total
                }
            }
        )
    except Exception as e:
        print(f"Error recalculating rating: {e}")

def _update_recent_comments(entity_type: str, entity_id: str):
    """Update the cache of recent comments in the entity"""
    try:
        # Get the 5 most recent comments (only main ones)
        comments_cursor = current_app.db.comments.find(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "reply_to": None  # Only main comments
            }
        ).sort("date", -1).limit(5)
        
        # Convert to RecentComment using Pydantic
        recent_comments = []
        for comment in comments_cursor:
            comment['_id'] = str(comment['_id'])
            
            # ✅ Use Pydantic schema to validate and structure
            try:
                recent_comment = LastComment(**comment)
                recent_comments.append(
                    recent_comment.model_dump(exclude_none=True)
                )
            except ValidationError as e:
                # If there's any comment with invalid data, we skip it
                print(f"Invalid comment: {e}")
                continue
        
        # Update in the entity
        entity_collection = _get_collection_by_type(entity_type)
        
        entity_collection.update_one(
            {"_id": ObjectId(entity_id)},
            {"$set": {"comments": recent_comments}}
        )
        
    except Exception as e:
        print(f"Error updating recent comments: {e}")
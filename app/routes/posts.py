from flask import Blueprint, request, jsonify, current_app
from app.schemas.posts import PostCreate, PostResponse, PostUpdate
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

# Create blueprint for posts
bp = Blueprint('posts', __name__, url_prefix='/api/posts')

'''
--POSTS--

POST - create post 
GET - view posts
PUT - update post
DELETE - delete post

POST - give like post

'''

# ==================== CREATE POST ====================

@bp.route('', methods=['POST'])
def create_post():
    """
    POST /api/posts
    Body: {
        "author_id": "507f1f77bcf86cd799439011",
        "author_name": "John Doe",
        "type": "discussion",  // "discussion" or "article"
        "category": "technical",
        "title": "How to improve backhand?",
        "content": "I've been practicing for a while...",
        "summary": "Brief description...",  // Optional
        "images": [...],  // Optional
        "videos": [...]  // Optional
    }
    """
    try:
        # Validate data with Pydantic
        post_data = PostCreate(**request.json)
        
        # Prepare document for MongoDB
        post_dict = post_data.model_dump(exclude_none=True)
        post_dict['date'] = datetime.now(timezone.utc)
        post_dict['views'] = 0
        post_dict['likes'] = 0
        post_dict['comments'] = []
        post_dict['total_comments'] = 0
        
        # Insert into MongoDB
        result = current_app.db.posts.insert_one(post_dict)
        
        # Prepare response
        post_dict['_id'] = str(result.inserted_id)
        post_response = PostResponse(**post_dict)
        
        return jsonify({
            "message": "Post created successfully",
            "post": post_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VIEW POST DETAILS ====================

@bp.route('/<post_id>', methods=['GET'])
def view_post(post_id):
    """
    GET /api/posts/:post_id
    View complete details of a post and increment view counter
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "Invalid post ID"}), 400
        
        # Find post and increment views
        post = current_app.db.posts.find_one_and_update(
            {"_id": ObjectId(post_id)},
            {"$inc": {"views": 1}},
            return_document=True  # Returns the updated document
        )
        
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Convert _id to string
        post['_id'] = str(post['_id'])
        
        # Add default fields if they don't exist
        post.setdefault('comments', [])
        post.setdefault('total_comments', 0)
        post.setdefault('views', 1)  # Already incremented above
        post.setdefault('likes', 0)
        
        # Validate with Pydantic
        post_response = PostResponse(**post)
        
        return jsonify(post_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== UPDATE POST ====================

@bp.route('/<post_id>', methods=['PUT'])
def update_post(post_id):
    """
    PUT /api/posts/:post_id
    Body: {
        "user_id": "507f...",  // ID of the user making the request
        "role": "user",  // user, company, admin
        "title": "Updated title",
        "content": "Updated content",
        ...
    }
    
    DEMO: Only the author or an admin can update
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "Invalid post ID"}), 400
        
        # Find post first
        post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Get data from body
        data = request.json
        request_user_id = data.get('user_id')
        role = data.get('role', 'user')
        
        if not request_user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # ✅ PERMISSION VERIFICATION: Only the author or admin can update
        is_author = post['author_id'] == request_user_id
        is_admin = role == 'admin'
        
        if not (is_author or is_admin):
            return jsonify({"error": "Only the author or an admin can update this post"}), 403
        
        # Remove verification fields from update
        data_copy = data.copy()
        data_copy.pop('user_id', None)
        data_copy.pop('role', None)
        
        # Validate data with Pydantic
        update_data = PostUpdate(**data_copy)
        
        # Prepare update (only non-None fields)
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            return jsonify({"error": "No data to update"}), 400
        
        # Add last modification date
        update_dict['modification_date'] = datetime.now(timezone.utc)
        
        # Update in MongoDB
        current_app.db.posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_dict}
        )
        
        # Get updated post
        updated_post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        updated_post['_id'] = str(updated_post['_id'])
        
        # Add default fields
        updated_post.setdefault('comments', [])
        updated_post.setdefault('total_comments', 0)
        updated_post.setdefault('views', 0)
        updated_post.setdefault('likes', 0)
        
        post_response = PostResponse(**updated_post)
        
        return jsonify({
            "message": "Post updated successfully",
            "post": post_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Invalid data", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== DELETE POST ====================

@bp.route('/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    """
    DELETE /api/posts/:post_id
    Body: {
        "user_id": "507f...",  // ID of the user making the request
        "role": "user"  // user, company, admin
    }
    
    DEMO: Only the author or an admin can delete
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "Invalid post ID"}), 400
        
        # Find post
        post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Get data from body
        data = request.json or {}
        request_user_id = data.get('user_id')
        role = data.get('role', 'user')
        
        if not request_user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # ✅ PERMISSION VERIFICATION: Only the author or admin can delete
        is_author = post['author_id'] == request_user_id
        is_admin = role == 'admin'
        
        if not (is_author or is_admin):
            return jsonify({"error": "Only the author or an admin can delete this post"}), 403
        
        # Delete post
        current_app.db.posts.delete_one({"_id": ObjectId(post_id)})
        
        # Optional: Also delete all comments from the post
        current_app.db.comments.delete_many({
            "entity_type": "post",
            "entity_id": post_id
        })
        
        return jsonify({"message": "Post deleted successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== GIVE/REMOVE LIKE ====================

@bp.route('/<post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """
    POST /api/posts/:post_id/like
    Body: {"user_id": "..."}
    
    Give or remove like from a post (toggle)
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "Invalid post ID"}), 400
        
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # Find post
        post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Check if the user already liked it
        liked_by_users = post.get('liked_by_users', [])
        
        if user_id in liked_by_users:
            # Remove like
            current_app.db.posts.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$pull": {"liked_by_users": user_id},
                    "$inc": {"likes": -1}
                }
            )
            message = "Like removed"
            new_likes = post.get('likes', 0) - 1
        else:
            # Give like
            current_app.db.posts.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$addToSet": {"liked_by_users": user_id},
                    "$inc": {"likes": 1}
                }
            )
            message = "Like added"
            new_likes = post.get('likes', 0) + 1
        
        return jsonify({
            "message": message,
            "likes": new_likes
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
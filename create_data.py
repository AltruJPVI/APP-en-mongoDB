import pymongo
from faker import Faker
import bcrypt
from datetime import datetime, timedelta, timezone
import random
from bson import ObjectId
import json
import os

# Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')
BATCH_SIZE = 1000

fake = Faker('es_ES')

def insert_batch(collection, documents):
    """Insert in batches"""
    total = len(documents)
    for i in range(0, total, BATCH_SIZE):
        batch = documents[i:i+BATCH_SIZE]
        collection.insert_many(batch, ordered=False)
        print(f"  ✓ {min(i+BATCH_SIZE, total)}/{total}")

# =============================================================================
# USERS
# =============================================================================
def create_users(db, num):
    print(f"\n[1/4] Creating {num} users...")
    
    # Fixed admin and companies
    users = [
        {
            "_id": ObjectId(),
            "name": "Main Admin",
            "email": "admin@tennisstore.com",
            "password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
            "role": "admin",
            "level": "advanced",
            "date": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "name": "Wilson Store",
            "email": "wilson@store.com",
            "password": bcrypt.hashpw(b"wilson123", bcrypt.gensalt()).decode(),
            "role": "company",
            "level": "advanced",
            "date": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "name": "Babolat Official",
            "email": "babolat@store.com",
            "password": bcrypt.hashpw(b"babolat123", bcrypt.gensalt()).decode(),
            "role": "company",
            "level": "advanced",
            "date": datetime.now(timezone.utc)
        }
    ]
    
    # Users with Faker
    levels = ["beginner", "intermediate", "advanced"]
    password_hash = bcrypt.hashpw(b"user123", bcrypt.gensalt()).decode()
    
    for _ in range(num):
        users.append({
            "_id": ObjectId(),
            "name": fake.name(),
            "email": fake.email(),
            "password": password_hash,
            "role": "user",
            "level": random.choice(levels),
            "location": {
                "city": fake.city(),
                "postal_code": fake.postcode()
            } if random.choice([True,False,False]) else None,
            "date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 365))
        })
    
    insert_batch(db.users, users)
    return users

# =============================================================================
# PRODUCTS
# =============================================================================
def get_products(db):
    with open("products.json",'r',encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n[2/4] Getting products...")
    for d in data:
        d['date']=datetime.now(timezone.utc)
        d['gender']="unisex"
        db.products.insert_one(d)
    products=list(db.products.find())
    print(f"  ✓ {len(products)} products found")
    return products

# =============================================================================
# POSTS
# =============================================================================
def create_posts(db, users, num):
    print(f"\n[3/4] Creating {num} posts...")
    
    normal_users = [u for u in users if u['role'] == 'user']
    categories = ["equipment", "technique", "training", "matches", "clubs", 
                  "general", "tips", "nutrition", "news", "tournaments"]
    types = ["discussion", "article"]
    
    posts = []
    for _ in range(num):
        author = random.choice(normal_users)
        posts.append({
            "_id": ObjectId(),
            "author_id": str(author["_id"]),
            "author_name": author["name"],
            "type": random.choice(types),
            "category": random.choice(categories),
            "title": fake.sentence(nb_words=8).replace('.', '?'),
            "content": fake.paragraph(nb_sentences=5),
            "summary": fake.sentence(nb_words=10) if random.choice([True,False,False]) else None,
            "date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 180)),
            "views": random.randint(0, 500),
            "likes": random.randint(0, 50),
            "comments": [],
            "total_comments": 0
        })
    
    insert_batch(db.posts, posts)

    return posts

# =============================================================================
# COMMENTS
# =============================================================================
def create_comments(db, users, products, posts, num):
    print(f"\n[4/4] Creating {num} comments...")
    
    normal_users = [u for u in users if u['role'] == 'user']
    comments = []
    
    # 40% on products, 60% on posts
    num_products = int(num * 0.4) if products else 0
    num_posts = num - num_products
    
    # Comments on products
    for _ in range(num_products):
        product = random.choice(products)
        author = random.choice(normal_users)
        comments.append({
            "_id": ObjectId(),
            "entity_type": "product",
            "entity_id": str(product["_id"]),
            "user_id": str(author["_id"]),
            "user_name": author["name"],
            "text": fake.sentence(nb_words=random.randint(5, 15)),
            "rating": random.randint(3, 5),
            "date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90)),
            "likes": random.randint(0, 20)
        })
    
    # Comments on posts
    for _ in range(num_posts):
        post = random.choice(posts)
        author = random.choice(normal_users)
        comments.append({
            "_id": ObjectId(),
            "entity_type": "post",
            "entity_id": str(post["_id"]),
            "user_id": str(author["_id"]),
            "user_name": author["name"],
            "text": fake.paragraph(nb_sentences=random.randint(2, 4)),
            "date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90)),
            "likes": random.randint(0, 15)
        })
    
    insert_batch(db.comments, comments)
    
    # Update counters and comment cache
    print("  Updating counters and comment cache...")
    
    # PRODUCTS: counters + cache of last 5 comments
    for product in products:
        product_comments = [c for c in comments if c["entity_type"] == "product" and c["entity_id"] == str(product["_id"])]
        count = len(product_comments)
        
        if count > 0:
            # Calculate ratings
            ratings = [c["rating"] for c in product_comments if "rating" in c]
            average = round(sum(ratings) / len(ratings), 2) if ratings else None
            
            # Get last 5 comments (sorted by date descending)
            recent_comments = sorted(product_comments, key=lambda x: x["date"], reverse=True)[:5]
            
            # Format for cache (remove internal ObjectId _id)
            cache = []
            for c in recent_comments:
                cache.append({
                    "_id": str(c["_id"]),
                    "user_id": c["user_id"],
                    "user_name": c["user_name"],
                    "text": c["text"],
                    "date": c["date"],
                    "likes": c["likes"],
                    "rating": c.get("rating")
                })
            
            # Update product
            update_data = {
                "total_comments": count,
                "comments": cache  # Recent comments cache
            }
            if average:
                update_data["average_rating"] = average
                update_data["total_ratings"] = len(ratings)
            
            db.products.update_one(
                {"_id": product["_id"]},
                {"$set": update_data}
            )
    
    # POSTS: counters + cache of last 5 comments
    for post in posts:
        post_comments = [c for c in comments if c["entity_type"] == "post" and c["entity_id"] == str(post["_id"])]
        count = len(post_comments)
        
        if count > 0:
            # Get last 5 comments (sorted by date descending)
            recent_comments = sorted(post_comments, key=lambda x: x["date"], reverse=True)[:5]
            
            # Format for cache
            cache = []
            for c in recent_comments:
                cache.append({
                    "_id": str(c["_id"]),
                    "user_id": c["user_id"],
                    "user_name": c["user_name"],
                    "text": c["text"],
                    "date": c["date"],
                    "likes": c["likes"]
                })
            
            # Update post
            db.posts.update_one(
                {"_id": post["_id"]},
                {"$set": {
                    "total_comments": count,
                    "comments": cache  # Recent comments cache
                }}
            )
    
    print("  ✓ Counters and cache updated")

# =============================================================================
# MAIN
# =============================================================================
def main():
    users, posts, comments = 50_000, 2_000, 100_000
    print(f"\n{'='*60}")
    print(f"SEED DATABASE")
    print(f"{'='*60}")
    print(f"MongoDB: {MONGO_URI}")
    print(f"DB: {DB_NAME}")
    print(f"\nUsers: {users:,}")
    print(f"Posts: {posts:,}")
    print(f"Comments: {comments:,}")
    
    # Connect
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  

        db = client[DB_NAME]
        #db.dropDatabase()
        print("\n✓ Connected to MongoDB")

        db.create_collection('products') 
        db.create_collection('users')
        db.create_collection('posts')   
        db.create_collection('orders') 
        db.create_collection('comments') 
        

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return
    
    start = datetime.now()
    
    # Execute
    users_list = create_users(db, users)
    products = get_products(db)
    created_posts = create_posts(db, users_list, posts)
    create_comments(db, users_list, products, created_posts, comments)
    
    duration = (datetime.now() - start).total_seconds()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✓ COMPLETED IN {duration:.1f}s")
    print(f"{'='*60}")
    print(f"Users: {len(users_list)}")
    print(f"Products: {len(products)}")
    print(f"Posts: {len(created_posts)}")
    print(f"Comments: {comments}")

if __name__ == "__main__":
    main()

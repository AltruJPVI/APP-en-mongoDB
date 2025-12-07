import pymongo
from bson import json_util 
import os
from datetime import datetime

# Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')

def load_collection(db, collection_name, filename):

    print(f"\nLoading {collection_name}...")
    with open(filename, 'r', encoding='utf-8') as f:
        data = json_util.loads(f.read())
    
    if data:
        db[collection_name].insert_many(data)
        print(f"{len(data):,} documents inserted")
    else:
        print(f"No data found in {filename}")

def main():
    print(f"LOAD DATABASE FROM JSON FILES")
    
    print(f"MongoDB: {MONGO_URI}")
    print(f"DB: {DB_NAME}")
    
    # Connect
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[DB_NAME]
        print("\n✓ Connected to MongoDB")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return
    
    start = datetime.now()
    
    # Load all collections
    load_collection(db, 'users', 'data/users.json')
    load_collection(db, 'products', 'data/products.json')
    load_collection(db, 'posts', 'data/posts.json')
    load_collection(db, 'comments', 'data/comments.json')
    
    duration = (datetime.now() - start).total_seconds()
    
    print(f"COMPLETED IN {duration:.1f}s")

if __name__ == "__main__":
    main()

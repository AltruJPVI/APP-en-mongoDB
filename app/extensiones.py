import os
from pymongo import MongoClient

mongo_client = None
db = None

def init_db():
    global mongo_client, db
    
    # Lee directamente las variables del docker-compose
    mongo_uri = os.getenv('MONGO_URI')
    db_name = os.getenv('MONGO_DB_NAME')
    
    try:
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client[db_name]
        
        # Testear conexión
        mongo_client.admin.command('ping')
        print(f"✅ Conectado a MongoDB: {db_name}")
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")
        raise
    
    return db

import os
from dotenv import load_dotenv
from pymongo import MongoClient
#from flask_cors import CORS

load_dotenv()

mongo_client = None
db = None
#cors = CORS()

def init_db():

    global mongo_client, db
    
    # Leer del .env
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
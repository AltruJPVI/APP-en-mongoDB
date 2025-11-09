import pymongo
from faker import Faker
import bcrypt
from datetime import datetime, timedelta, timezone
import random
from bson import ObjectId
import json
import os

# Configuración
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')
BATCH_SIZE = 1000

fake = Faker('es_ES')

def insert_batch(collection, documents):
    """Insertar en batches"""
    total = len(documents)
    for i in range(0, total, BATCH_SIZE):
        batch = documents[i:i+BATCH_SIZE]
        collection.insert_many(batch, ordered=False)
        print(f"  ✓ {min(i+BATCH_SIZE, total)}/{total}")

# =============================================================================
# USUARIOS
# =============================================================================
def crear_usuarios(db, num):
    print(f"\n[1/4] Creando {num} usuarios...")
    
    # Admin y empresas fijos
    usuarios = [
        {
            "_id": ObjectId(),
            "nombre": "Admin Principal",
            "email": "admin@tiendatenis.com",
            "password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
            "clase": "admin",
            "nivel": "avanzado",
            "fecha_registro": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "nombre": "Wilson Store",
            "email": "wilson@tienda.com",
            "password": bcrypt.hashpw(b"wilson123", bcrypt.gensalt()).decode(),
            "clase": "empresa",
            "nivel": "avanzado",
            "fecha_registro": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId(),
            "nombre": "Babolat Official",
            "email": "babolat@tienda.com",
            "password": bcrypt.hashpw(b"babolat123", bcrypt.gensalt()).decode(),
            "clase": "empresa",
            "nivel": "avanzado",
            "fecha_registro": datetime.now(timezone.utc)
        }
    ]
    
    # Usuarios con Faker
    niveles = ["principiante", "intermedio", "avanzado"]
    password_hash = bcrypt.hashpw(b"user123", bcrypt.gensalt()).decode()
    
    for _ in range(num):
        usuarios.append({
            "_id": ObjectId(),
            "nombre": fake.name(),
            "email": fake.email(),
            "password": password_hash,
            "clase": "user",
            "nivel": random.choice(niveles),
            "ubicacion": {
                "ciudad": fake.city(),
                "codigo_postal": fake.postcode()
            } if random.choice([True,False,False]) else None,
            "fecha_registro": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 365))
        })
    
    insert_batch(db.users, usuarios)
    return usuarios

# =============================================================================
# PRODUCTOS
# =============================================================================
def obtener_productos(db):
    with open("productos.json",'r',encoding='utf-8') as f:
        datos = json.load(f)
    print(f"\n[2/4] Obteniendo productos...")
    db.products.insert_many(datos)
    productos=list(db.products.find())
    print(f"  ✓ {len(productos)} productos encontrados")
    return productos

# =============================================================================
# POSTS
# =============================================================================
def crear_posts(db, usuarios, num):
    print(f"\n[3/4] Creando {num} posts...")
    
    users_normales = [u for u in usuarios if u['clase'] == 'user']
    categorias = ["equipamiento", "tecnica", "entrenamientos", "partidos", "clubes", 
                  "general", "consejos", "nutricion", "noticias", "torneos"]
    tipos = ["discusion", "articulo"]
    
    posts = []
    for _ in range(num):
        autor = random.choice(users_normales)
        posts.append({
            "_id": ObjectId(),
            "autor_id": str(autor["_id"]),
            "autor_nombre": autor["nombre"],
            "tipo": random.choice(tipos),
            "categoria": random.choice(categorias),
            "titulo": fake.sentence(nb_words=8).replace('.', '?'),
            "contenido": fake.paragraph(nb_sentences=5),
            "resumen": fake.sentence(nb_words=10) if random.choice([True,False,False]) else None,
            "fecha_creacion": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 180)),
            "vistas": random.randint(0, 500),
            "likes": random.randint(0, 50),
            "comentarios": [],
            "total_comentarios": 0
        })
    
    insert_batch(db.posts, posts)

    return posts

# =============================================================================
# COMENTARIOS
# =============================================================================
def crear_comentarios(db, usuarios, productos, posts, num):
    print(f"\n[4/4] Creando {num} comentarios...")
    
    users_normales = [u for u in usuarios if u['clase'] == 'user']
    comentarios = []
    
    # 40% en productos, 60% en posts
    num_productos = int(num * 0.4) if productos else 0
    num_posts = num - num_productos
    
    # Comentarios en productos
    for _ in range(num_productos):
        producto = random.choice(productos)
        autor = random.choice(users_normales)
        comentarios.append({
            "_id": ObjectId(),
            "entidad_tipo": "producto",
            "entidad_id": str(producto["_id"]),
            "usuario_id": str(autor["_id"]),
            "usuario_nombre": autor["nombre"],
            "texto": fake.sentence(nb_words=random.randint(5, 15)),
            "valoracion": random.randint(3, 5),
            "fecha": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90)),
            "likes": random.randint(0, 20)
        })
    
    # Comentarios en posts
    for _ in range(num_posts):
        post = random.choice(posts)
        autor = random.choice(users_normales)
        comentarios.append({
            "_id": ObjectId(),
            "entidad_tipo": "post",
            "entidad_id": str(post["_id"]),
            "usuario_id": str(autor["_id"]),
            "usuario_nombre": autor["nombre"],
            "texto": fake.paragraph(nb_sentences=random.randint(2, 4)),
            "fecha": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90)),
            "likes": random.randint(0, 15)
        })
    
    insert_batch(db.comments, comentarios)
    
    # Actualizar contadores y cache de comentarios
    print("  Actualizando contadores y cache de comentarios...")
    
    # PRODUCTOS: contadores + cache de últimos 5 comentarios
    for producto in productos:
        comentarios_producto = [c for c in comentarios if c["entidad_tipo"] == "producto" and c["entidad_id"] == str(producto["_id"])]
        count = len(comentarios_producto)
        
        if count > 0:
            # Calcular valoraciones
            valoraciones = [c["valoracion"] for c in comentarios_producto if "valoracion" in c]
            promedio = round(sum(valoraciones) / len(valoraciones), 2) if valoraciones else None
            
            # Obtener últimos 5 comentarios (ordenados por fecha descendente)
            comentarios_recientes = sorted(comentarios_producto, key=lambda x: x["fecha"], reverse=True)[:5]
            
            # Formatear para el cache (quitar _id interno de ObjectId)
            cache = []
            for c in comentarios_recientes:
                cache.append({
                    "_id": str(c["_id"]),
                    "usuario_id": c["usuario_id"],
                    "usuario_nombre": c["usuario_nombre"],
                    "texto": c["texto"],
                    "fecha": c["fecha"],
                    "likes": c["likes"],
                    "valoracion": c.get("valoracion")
                })
            
            # Actualizar producto
            update_data = {
                "total_comentarios": count,
                "comentarios": cache  # Cache de comentarios recientes
            }
            if promedio:
                update_data["valoracion_promedio"] = promedio
                update_data["total_valoraciones"] = len(valoraciones)
            
            db.products.update_one(
                {"_id": producto["_id"]},
                {"$set": update_data}
            )
    
    # POSTS: contadores + cache de últimos 5 comentarios
    for post in posts:
        comentarios_post = [c for c in comentarios if c["entidad_tipo"] == "post" and c["entidad_id"] == str(post["_id"])]
        count = len(comentarios_post)
        
        if count > 0:
            # Obtener últimos 5 comentarios (ordenados por fecha descendente)
            comentarios_recientes = sorted(comentarios_post, key=lambda x: x["fecha"], reverse=True)[:5]
            
            # Formatear para el cache
            cache = []
            for c in comentarios_recientes:
                cache.append({
                    "_id": str(c["_id"]),
                    "usuario_id": c["usuario_id"],
                    "usuario_nombre": c["usuario_nombre"],
                    "texto": c["texto"],
                    "fecha": c["fecha"],
                    "likes": c["likes"]
                })
            
            # Actualizar post
            db.posts.update_one(
                {"_id": post["_id"]},
                {"$set": {
                    "total_comentarios": count,
                    "comentarios_recientes": cache  # Cache de comentarios recientes
                }}
            )
    
    print("  ✓ Contadores y cache actualizados")

# =============================================================================
# MAIN
# =============================================================================
def main():
    users,posts,coments=50_000,2_000,100_000
    print(f"\n{'='*60}")
    print(f"🌱 SEED DATABASE")
    print(f"{'='*60}")
    print(f"MongoDB: {MONGO_URI}")
    print(f"BD: {DB_NAME}")
    print(f"\nUsuarios: {users:,}")
    print(f"Posts: {posts:,}")
    print(f"Comentarios: {coments:,}")
    
    # Conectar
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  

        db = client[DB_NAME]
        #db.dropDatabase()
        print("\n✓ Conectado a MongoDB")

        db.create_collection('products') 
        db.create_collection('users')
        db.create_collection('posts')   
        db.create_collection('orders') 
        db.create_collection('comments') 
        

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return
    
    start = datetime.now()
    
    # Ejecutar
    usuarios = crear_usuarios(db, users)
    productos = obtener_productos(db)
    posts_creados = crear_posts(db, usuarios, posts)
    crear_comentarios(db, usuarios, productos, posts_creados, coments)
    
    duration = (datetime.now() - start).total_seconds()
    
    # Resumen
    print(f"\n{'='*60}")
    print(f"✓ COMPLETADO EN {duration:.1f}s")
    print(f"{'='*60}")
    print(f"👤 Usuarios: {len(usuarios)}")
    print(f"📦 Productos: {len(productos)}")
    print(f"📝 Posts: {len(posts_creados)}")
    print(f"💬 Comentarios: {coments}")

if __name__ == "__main__":
    main()

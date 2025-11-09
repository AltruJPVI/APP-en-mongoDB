from flask import Blueprint, request, jsonify, current_app
from app.schemas.post import PostCreate, PostResponse, PostUpdate
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

# Crear blueprint para posts
bp = Blueprint('posts', __name__, url_prefix='/api/posts')

'''
--POSTS--

POST - crear post 
GET - ver posts
GET - ver 1 post concreto
PUT - actualizar post
DELETE - borrar post

POST - dar like post
GET - ver cuantos post hay de cada categoria
'''

# ==================== CREAR POST ====================

@bp.route('', methods=['POST'])
def crear_post():
    """
    POST /api/posts
    Body: {
        "autor_id": "507f1f77bcf86cd799439011",
        "autor_nombre": "Juan Pérez",
        "tipo": "discusion",  // "discusion" o "articulo"
        "categoria": "tecnica",
        "titulo": "¿Cómo mejorar el revés?",
        "contenido": "Llevo tiempo practicando...",
        "resumen": "Breve descripción...",  // Opcional
        "imagenes": [...],  // Opcional
        "videos": [...]  // Opcional
    }
    """
    try:
        # Validar datos con Pydantic
        post_data = PostCreate(**request.json)
        
        # Preparar documento para MongoDB
        post_dict = post_data.model_dump(exclude_none=True)
        post_dict['fecha_creacion'] = datetime.now(timezone.utc)
        post_dict['vistas'] = 0
        post_dict['likes'] = 0
        post_dict['comentarios'] = []
        post_dict['total_comentarios'] = 0
        
        # Insertar en MongoDB
        result = current_app.db.posts.insert_one(post_dict)
        
        # Preparar respuesta
        post_dict['_id'] = str(result.inserted_id)
        post_response = PostResponse(**post_dict)
        
        return jsonify({
            "message": "Post creado exitosamente",
            "post": post_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LISTAR POSTS (CON FILTROS SIMPLIFICADOS) ====================

@bp.route('', methods=['GET'])
def listar_posts():
    """
    GET /api/posts?categoria=tecnica&autor_id=xxx&order=desc&page=1&limit=20
    
    Filtros disponibles:
    - categoria: equipamiento, tecnica, entrenamientos, etc.
    - autor_id: posts de un autor específico
    - order: asc, desc (default: desc - más recientes primero)
    - page: número de página (default: 1)
    - limit: posts por página (default: 20, max: 100)
    """
    try:
        # Construir filtro de MongoDB
        filtro = {}
        
        # Filtro por categoría
        categoria = request.args.get('categoria')
        if categoria:
            filtro['categoria'] = categoria
        
        # Filtro por autor
        autor_id = request.args.get('autor_id')
        if autor_id:
            filtro['autor_id'] = autor_id
        
        # Paginación
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)
        skip = (page - 1) * limit
        
        # Ordenamiento (solo por fecha)
        order = request.args.get('order', 'desc')
        sort_direction = 1 if order == 'asc' else -1
        
        # Ejecutar query con paginación
        posts_cursor = current_app.db.posts.find(filtro).sort(
            'fecha_creacion', sort_direction
        ).skip(skip).limit(limit)
        
        # Convertir a lista
        posts = []
        for post in posts_cursor:
            post['_id'] = str(post['_id'])
            # Agregar campos por defecto si no existen
            post.setdefault('comentarios', [])
            post.setdefault('total_comentarios', 0)
            post.setdefault('vistas', 0)
            post.setdefault('likes', 0)
                
            posts.append(PostResponse(**post).model_dump(exclude_none=True))
        
        # Contar total de posts (para paginación)
        total_posts = current_app.db.posts.count_documents(filtro)
        total_pages = (total_posts + limit - 1) // limit
        
        return jsonify({
            "posts": posts,
            "paginacion": {
                "page": page,
                "limit": limit,
                "total_posts": total_posts,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VER DETALLE DE POST ====================

@bp.route('/<post_id>', methods=['GET'])
def ver_post(post_id):
    """
    GET /api/posts/:post_id
    Ver detalle completo de un post e incrementar contador de vistas
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "ID de post inválido"}), 400
        
        # Buscar post e incrementar vistas
        post = current_app.db.posts.find_one_and_update(
            {"_id": ObjectId(post_id)},
            {"$inc": {"vistas": 1}},
            return_document=True  # Devuelve el documento actualizado
        )
        
        if not post:
            return jsonify({"error": "Post no encontrado"}), 404
        
        # Convertir _id a string
        post['_id'] = str(post['_id'])
        
        # Agregar campos por defecto si no existen
        post.setdefault('comentarios', [])
        post.setdefault('total_comentarios', 0)
        post.setdefault('vistas', 1)  # Ya se incrementó arriba
        post.setdefault('likes', 0)
        
        # Validar con Pydantic
        post_response = PostResponse(**post)
        
        return jsonify(post_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ACTUALIZAR POST ====================

@bp.route('/<post_id>', methods=['PUT'])
def actualizar_post(post_id):
    """
    PUT /api/posts/:post_id
    Body: {
        "usuario_id": "507f...",  // ID del usuario que hace la petición
        "clase": "user",  // user, empresa, admin
        "titulo": "Título actualizado",
        "contenido": "Contenido actualizado",
        ...
    }
    
    DEMO: Solo el autor o un admin pueden actualizar
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "ID de post inválido"}), 400
        
        # Buscar post primero
        post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return jsonify({"error": "Post no encontrado"}), 404
        
        # Obtener datos del body
        data = request.json
        usuario_id_peticion = data.get('usuario_id')
        clase = data.get('clase', 'user')
        
        if not usuario_id_peticion:
            return jsonify({"error": "usuario_id es requerido"}), 400
        
        # ✅ VERIFICACIÓN DE PERMISOS: Solo el autor o admin pueden actualizar
        es_autor = post['autor_id'] == usuario_id_peticion
        es_admin = clase == 'admin'
        
        if not (es_autor or es_admin):
            return jsonify({"error": "Solo el autor o un admin pueden actualizar este post"}), 403
        
        # Remover campos de verificación del update
        data_copy = data.copy()
        data_copy.pop('usuario_id', None)
        data_copy.pop('clase', None)
        
        # Validar datos con Pydantic
        update_data = PostUpdate(**data_copy)
        
        # Preparar actualización (solo campos no None)
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            return jsonify({"error": "No hay datos para actualizar"}), 400
        
        # Agregar fecha de última modificación
        update_dict['fecha_modificacion'] = datetime.now(timezone.utc)
        
        # Actualizar en MongoDB
        current_app.db.posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_dict}
        )
        
        # Obtener post actualizado
        post_actualizado = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        post_actualizado['_id'] = str(post_actualizado['_id'])
        
        # Agregar campos por defecto
        post_actualizado.setdefault('comentarios', [])
        post_actualizado.setdefault('total_comentarios', 0)
        post_actualizado.setdefault('vistas', 0)
        post_actualizado.setdefault('likes', 0)
        
        post_response = PostResponse(**post_actualizado)
        
        return jsonify({
            "message": "Post actualizado exitosamente",
            "post": post_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ELIMINAR POST ====================

@bp.route('/<post_id>', methods=['DELETE'])
def eliminar_post(post_id):
    """
    DELETE /api/posts/:post_id
    Body: {
        "usuario_id": "507f...",  // ID del usuario que hace la petición
        "clase": "user"  // user, empresa, admin
    }
    
    DEMO: Solo el autor o un admin pueden eliminar
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "ID de post inválido"}), 400
        
        # Buscar post
        post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return jsonify({"error": "Post no encontrado"}), 404
        
        # Obtener datos del body
        data = request.json or {}
        usuario_id_peticion = data.get('usuario_id')
        clase = data.get('clase', 'user')
        
        if not usuario_id_peticion:
            return jsonify({"error": "usuario_id es requerido"}), 400
        
        # ✅ VERIFICACIÓN DE PERMISOS: Solo el autor o admin pueden eliminar
        es_autor = post['autor_id'] == usuario_id_peticion
        es_admin = clase == 'admin'
        
        if not (es_autor or es_admin):
            return jsonify({"error": "Solo el autor o un admin pueden eliminar este post"}), 403
        
        # Eliminar post
        current_app.db.posts.delete_one({"_id": ObjectId(post_id)})
        
        # Opcional: También eliminar todos los comentarios del post
        current_app.db.comments.delete_many({
            "entidad_tipo": "post",
            "entidad_id": post_id
        })
        
        return jsonify({"message": "Post eliminado exitosamente"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== DAR/QUITAR LIKE ====================

@bp.route('/<post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """
    POST /api/posts/:post_id/like
    Body: {"usuario_id": "..."}
    
    Dar o quitar like a un post (toggle)
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(post_id):
            return jsonify({"error": "ID de post inválido"}), 400
        
        usuario_id = request.json.get('usuario_id')
        if not usuario_id:
            return jsonify({"error": "usuario_id es requerido"}), 400
        
        # Buscar post
        post = current_app.db.posts.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            return jsonify({"error": "Post no encontrado"}), 404
        
        # Verificar si el usuario ya dio like
        usuarios_like = post.get('usuarios_like', [])
        
        if usuario_id in usuarios_like:
            # Quitar like
            current_app.db.posts.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$pull": {"usuarios_like": usuario_id},
                    "$inc": {"likes": -1}
                }
            )
            mensaje = "Like eliminado"
            nuevo_likes = post.get('likes', 0) - 1
        else:
            # Dar like
            current_app.db.posts.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$addToSet": {"usuarios_like": usuario_id},
                    "$inc": {"likes": 1}
                }
            )
            mensaje = "Like agregado"
            nuevo_likes = post.get('likes', 0) + 1
        
        return jsonify({
            "message": mensaje,
            "likes": nuevo_likes
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LISTAR CATEGORÍAS ====================

@bp.route('/categorias', methods=['GET'])
def listar_categorias():
    """
    GET /api/posts/categorias
    Listar todas las categorías con cantidad de posts
    """
    try:
        # Agregación para contar posts por categoría
        pipeline = [
            {"$group": {
                "_id": "$categoria",
                "cantidad": {"$sum": 1}
            }},
            {"$sort": {"cantidad": -1}}
        ]
        
        categorias = list(current_app.db.posts.aggregate(pipeline))
        
        # Formatear respuesta
        resultado = [
            {"categoria": cat["_id"], "cantidad": cat["cantidad"]}
            for cat in categorias
        ]
        
        return jsonify({"categorias": resultado}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
from flask import Blueprint, request, jsonify, current_app
from app.schemas.comentarios import CommentCreate, CommentResponse, CommentUpdate, TipoEntidad,ComentarioReciente
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

# Crear blueprint para comentarios
bp = Blueprint('comentarios', __name__, url_prefix='/api/comentarios')


"""operacion http:

--COMENTARIOS--

POST - crear comentario 
GET - ver comentarios con caché de 5 coments
GET - ver 1 comentario concreto
PUT - actualizar comentario
DELETE - borrar comentario

POST - dar like
GET - ver respuestas a un comentario

Funciones útiles
""" 

@bp.route('', methods=['POST'])
def crear_comentario():
    """
    POST /api/comentarios
    Body: {
        "entidad_tipo": "producto",  // "producto", "evento", "post"
        "entidad_id": "507f1f77bcf86cd799439011",
        "usuario_id": "60d5ec49f1b2c8b1f8e4e1a1",
        "usuario_nombre": "Juan Pérez",
        "texto": "Excelente producto!",
        "valoracion": 5,  // Opcional (1-5), solo para productos
        "respuesta_a": "..."  // Opcional, ID del comentario padre
    }
    
    TODO: Agregar @require_auth y obtener usuario_id/usuario_nombre del token
    """
    try:
        comment_data = CommentCreate(**request.json)
        # Verificar que la entidad existe
        entidad_collection = _get_collection_by_tipo(comment_data.entidad_tipo)
        
        if not ObjectId.is_valid(comment_data.entidad_id):
            return jsonify({"error": "ID de entidad inválido"}), 400

        entidad = entidad_collection.find_one({"_id": ObjectId(comment_data.entidad_id)})
        if not entidad:
            return jsonify({"error": f"{comment_data.entidad_tipo.capitalize()} no encontrado"}), 404
        # Si es una respuesta, verificar que el comentario padre existe
        if comment_data.respuesta_a:
            if not ObjectId.is_valid(comment_data.respuesta_a):
                return jsonify({"error": "ID de comentario padre inválido"}), 400
            
            comentario_padre = current_app.db.comments.find_one({"_id": ObjectId(comment_data.respuesta_a)})
            if not comentario_padre:
                return jsonify({"error": "Comentario padre no encontrado"}), 404
        # Preparar documento para MongoDB
        comment_dict = comment_data.model_dump(exclude_none=True)
        comment_dict['fecha'] = datetime.now(timezone.utc)
        comment_dict['likes'] = 0
        
        # Insertar en MongoDB
        result = current_app.db.comments.insert_one(comment_dict)

        # Actualizar contador de comentarios en la entidad
        entidad_collection.update_one(
            {"_id": ObjectId(comment_data.entidad_id)},
            {"$inc": {"total_comentarios": 1}}
        )
        # Si el comentario tiene valoración (productos), recalcular promedio
        if comment_data.valoracion and comment_data.entidad_tipo == TipoEntidad.producto:
            _recalcular_valoracion_producto(comment_data.entidad_id)
        
        # Actualizar comentarios recientes de la entidad
        _actualizar_comentarios_recientes(
            comment_data.entidad_tipo, 
            comment_data.entidad_id
        )
        
        # Preparar respuesta
        comment_dict['_id'] = str(result.inserted_id)
        comment_response = CommentResponse(**comment_dict)
        
        return jsonify({
            "message": "Comentario creado exitosamente",
            "comentario": comment_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('', methods=['GET'])
def listar_comentarios():
    """
    GET /api/comentarios?entidad_tipo=producto&entidad_id=xxx&page=1&limit=20
    
    Parámetros:
    - entidad_tipo: producto, evento, post (requerido)
    - entidad_id: ID de la entidad (requerido)
    - respuesta_a: null (solo principales) o ID (solo respuestas)
    - page: número de página (default: 1)
    - limit: comentarios por página (default: 20, max: 100)
    - sort: fecha, likes (default: fecha)
    - order: asc, desc (default: desc - más recientes primero)
    """
    try:
        # Obtener parámetros
        entidad_tipo = request.args.get('entidad_tipo')
        entidad_id = request.args.get('entidad_id')
        
        if not entidad_tipo or not entidad_id:
            return jsonify({"error": "Debes especificar entidad_tipo y entidad_id"}), 400
        
        # Validar entidad_tipo
        if entidad_tipo not in ['producto', 'post']:
            return jsonify({"error": "entidad_tipo inválido"}), 400
        
        # Validar ObjectId
        if not ObjectId.is_valid(entidad_id):
            return jsonify({"error": "ID de entidad inválido"}), 400
        
        # Construir filtro
        filtro = {
            "entidad_tipo": entidad_tipo,
            "entidad_id": entidad_id
        }
        
        # Filtrar por respuesta_a (comentarios principales o respuestas)
        respuesta_a = request.args.get('respuesta_a')
        if respuesta_a == 'null':
            # Solo comentarios principales (no respuestas)
            filtro['respuesta_a'] = None
        elif respuesta_a:
            # Solo respuestas a un comentario específico
            if not ObjectId.is_valid(respuesta_a):
                return jsonify({"error": "ID de comentario padre inválido"}), 400
            filtro['respuesta_a'] = respuesta_a
        
        # Paginación
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)
        skip = (page - 1) * limit
        
        # Ordenamiento
        sort_by = request.args.get('sort', 'fecha')
        order = request.args.get('order', 'desc')
        sort_direction = 1 if order == 'asc' else -1
        
        sort_fields = {
            'fecha': 'fecha',
            'likes': 'likes'
        }
        sort_field = sort_fields.get(sort_by, 'fecha')
        
        # Ejecutar query
        comentarios_cursor = current_app.db.comments.find(filtro).sort(
            sort_field, sort_direction
        ).skip(skip).limit(limit)
        
        # Convertir a lista
        comentarios = []
        for comentario in comentarios_cursor:
            comentario['_id'] = str(comentario['_id'])
            comentarios.append(CommentResponse(**comentario).model_dump(exclude_none=True))
        
        # Contar total
        total_comentarios = current_app.db.comments.count_documents(filtro)
        total_pages = (total_comentarios + limit - 1) // limit
        
        return jsonify({
            "comentarios": comentarios,
            "paginacion": {
                "page": page,
                "limit": limit,
                "total_comentarios": total_comentarios,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== VER COMENTARIO ====================

@bp.route('/<comment_id>', methods=['GET'])
def ver_comentario(comment_id):
    """
    GET /api/comentarios/:comment_id
    Ver un comentario específico
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "ID de comentario inválido"}), 400
        
        # Buscar comentario
        comentario = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        if not comentario:
            return jsonify({"error": "Comentario no encontrado"}), 404
        
        # Convertir _id a string
        comentario['_id'] = str(comentario['_id'])
        
        comment_response = CommentResponse(**comentario)
        
        return jsonify(comment_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ACTUALIZAR COMENTARIO ====================

@bp.route('/<comment_id>', methods=['PUT'])
def actualizar_comentario(comment_id):
    """
    PUT /api/comentarios/:comment_id
    Body: {
        "texto": "Texto actualizado",
        "valoracion": 4
    }
    
    NOTA: Solo el autor del comentario puede actualizarlo
    TODO: Verificar que current_user.id == comentario.usuario_id
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "ID de comentario inválido"}), 400
        
        # Validar datos
        update_data = CommentUpdate(**request.json)
        
        # Preparar actualización
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            return jsonify({"error": "No hay datos para actualizar"}), 400
        
        # TODO: Verificar que el usuario actual es el autor
        # comentario = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        # if comentario['usuario_id'] != current_user.id:
        #     return jsonify({"error": "No puedes editar comentarios de otros"}), 403
        
        # Agregar fecha de edición
        update_dict['fecha_edicion'] = datetime.now(timezone.utc)
        
        # Actualizar en MongoDB
        result = current_app.db.comments.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Comentario no encontrado"}), 404
        
        # Obtener comentario actualizado
        comentario = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        # Si se actualizó la valoración, recalcular promedio del producto
        if 'valoracion' in update_dict and comentario['entidad_tipo'] == 'producto':
            _recalcular_valoracion_producto(comentario['entidad_id'])
        
        # Actualizar comentarios recientes
        _actualizar_comentarios_recientes(
            comentario['entidad_tipo'],
            comentario['entidad_id']
        )
        
        comentario['_id'] = str(comentario['_id'])
        comment_response = CommentResponse(**comentario)
        
        return jsonify({
            "message": "Comentario actualizado exitosamente",
            "comentario": comment_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ELIMINAR COMENTARIO ====================

@bp.route('/<comment_id>', methods=['DELETE'])
def eliminar_comentario(comment_id):
    """
    DELETE /api/comentarios/:comment_id
    Body: {
        "usuario_id": "507f...",  // ID del usuario que hace la petición
        "clase": "user"  // user, empresa, admin
    }
    
        Solo el autor o un admin pueden eliminar
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "ID de comentario inválido"}), 400
        
        # Buscar comentario
        comentario = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        if not comentario:
            return jsonify({"error": "Comentario no encontrado"}), 404
        
        # Obtener datos del body
        data = request.json or {}
        usuario_id_peticion = data.get('usuario_id')
        clase = data.get('clase', 'user')
        
        if not usuario_id_peticion:
            return jsonify({"error": "usuario_id es requerido"}), 400
        
        # ✅ VERIFICACIÓN DE PERMISOS: Solo el autor o admin pueden eliminar
        es_autor = comentario['usuario_id'] == usuario_id_peticion
        es_admin = clase == 'admin'
        
        if not (es_autor or es_admin):
            return jsonify({"error": "Solo el autor o un admin pueden eliminar este comentario"}), 403
        
        # Guardar info antes de eliminar
        entidad_tipo = comentario['entidad_tipo']
        entidad_id = comentario['entidad_id']
        tiene_valoracion = comentario.get('valoracion') is not None
        
        # Eliminar comentario
        current_app.db.comments.delete_one({"_id": ObjectId(comment_id)})
        
        # Decrementar contador en la entidad
        entidad_collection = _get_collection_by_tipo(entidad_tipo)
        entidad_collection.update_one(
            {"_id": ObjectId(entidad_id)},
            {"$inc": {"total_comentarios": -1}}
        )
        
        # Si tenía valoración, recalcular promedio
        if tiene_valoracion and entidad_tipo == 'producto':
            _recalcular_valoracion_producto(entidad_id)
        
        # Actualizar comentarios recientes
        _actualizar_comentarios_recientes(entidad_tipo, entidad_id)
        
        return jsonify({"message": "Comentario eliminado exitosamente"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ==================== DAR/QUITAR LIKE ====================

@bp.route('/<comment_id>/like', methods=['POST'])
def toggle_like(comment_id):
    """
    POST /api/comentarios/:comment_id/like
    Body: {"usuario_id": "..."}
    
    Dar o quitar like a un comentario (toggle)
    TODO: Obtener usuario_id del token
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "ID de comentario inválido"}), 400
        
        # TODO: Obtener del token
        usuario_id = request.json.get('usuario_id')
        if not usuario_id:
            return jsonify({"error": "usuario_id es requerido"}), 400
        
        # Buscar comentario
        comentario = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        
        if not comentario:
            return jsonify({"error": "Comentario no encontrado"}), 404
        
        # Verificar si el usuario ya dio like
        # Para esto necesitamos un array de usuarios que dieron like
        # Vamos a usar una colección separada o un campo en el comentario
        
        # Opción: Usar un array 'usuarios_like' en el comentario
        usuarios_like = comentario.get('usuarios_like', [])
        
        if usuario_id in usuarios_like:
            # Quitar like
            current_app.db.comments.update_one(
                {"_id": ObjectId(comment_id)},
                {
                    "$pull": {"usuarios_like": usuario_id},
                    "$inc": {"likes": -1}
                }
            )
            mensaje = "Like eliminado"
            nuevo_likes = comentario['likes'] - 1
        else:
            # Dar like
            current_app.db.comments.update_one(
                {"_id": ObjectId(comment_id)},
                {
                    "$addToSet": {"usuarios_like": usuario_id},
                    "$inc": {"likes": 1}
                }
            )
            mensaje = "Like agregado"
            nuevo_likes = comentario['likes'] + 1
        
        return jsonify({
            "message": mensaje,
            "likes": nuevo_likes
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VER RESPUESTAS DE UN COMENTARIO ====================

@bp.route('/<comment_id>/respuestas', methods=['GET'])
def ver_respuestas(comment_id):
    """
    GET /api/comentarios/:comment_id/respuestas
    Ver todas las respuestas a un comentario
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(comment_id):
            return jsonify({"error": "ID de comentario inválido"}), 400
        
        # Verificar que el comentario padre existe
        comentario_padre = current_app.db.comments.find_one({"_id": ObjectId(comment_id)})
        if not comentario_padre:
            return jsonify({"error": "Comentario no encontrado"}), 404
        
        # Buscar respuestas
        respuestas_cursor = current_app.db.comments.find(
            {"respuesta_a": comment_id}
        ).sort("fecha", 1)  # Ascendente (más antiguas primero)
        
        respuestas = []
        for respuesta in respuestas_cursor:
            respuesta['_id'] = str(respuesta['_id'])
            respuestas.append(CommentResponse(**respuesta).model_dump(exclude_none=True))
        
        return jsonify({
            "respuestas": respuestas,
            "total_respuestas": len(respuestas)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== FUNCIONES AUXILIARES ====================

def _get_collection_by_tipo(entidad_tipo: str):
    """Obtener la colección de MongoDB según el tipo de entidad"""
    collections = {
        'producto': current_app.db.products,
        'post': current_app.db.posts
    }
    return collections.get(entidad_tipo)


def _recalcular_valoracion_producto(producto_id: str):
    """Recalcular la valoración promedio de un producto"""
    try:
        # Agregar todos los comentarios con valoración del producto
        pipeline = [
            {
                "$match": {
                    "entidad_tipo": "producto",
                    "entidad_id": producto_id,
                    "valoracion": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "promedio": {"$avg": "$valoracion"},
                    "total": {"$sum": 1}
                }
            }
        ]
        
        resultado = list(current_app.db.comments.aggregate(pipeline))
        
        if resultado:
            promedio = round(resultado[0]['promedio'], 2)
            total = resultado[0]['total']
        else:
            promedio = None
            total = 0
        
        # Actualizar producto
        current_app.db.products.update_one(
            {"_id": ObjectId(producto_id)},
            {
                "$set": {
                    "valoracion_promedio": promedio,
                    "total_valoraciones": total
                }
            }
        )
    except Exception as e:
        print(f"Error recalculando valoración: {e}")

def _actualizar_comentarios_recientes(entidad_tipo: str, entidad_id: str):
    """Actualizar el cache de comentarios recientes en la entidad"""
    try:
        # Obtener los 5 comentarios más recientes (solo principales)
        comentarios_cursor = current_app.db.comments.find(
            {
                "entidad_tipo": entidad_tipo,
                "entidad_id": entidad_id,
                "respuesta_a": None  # Solo comentarios principales
            }
        ).sort("fecha", -1).limit(5)
        
        # Convertir a ComentarioReciente usando Pydantic
        comentarios_recientes = []
        for comentario in comentarios_cursor:
            comentario['_id'] = str(comentario['_id'])
            
            # ✅ Usar el schema de Pydantic para validar y estructurar
            try:
                comentario_reciente = ComentarioReciente(**comentario)
                comentarios_recientes.append(
                    comentario_reciente.model_dump(exclude_none=True)
                )
            except ValidationError as e:
                # Si hay algún comentario con datos inválidos, lo saltamos
                print(f"Comentario inválido: {e}")
                continue
        
        # Actualizar en la entidad
        entidad_collection = _get_collection_by_tipo(entidad_tipo)
        
        entidad_collection.update_one(
            {"_id": ObjectId(entidad_id)},
            {"$set": {"comentarios": comentarios_recientes}}
        )
        
    except Exception as e:
        print(f"Error actualizando comentarios recientes: {e}")

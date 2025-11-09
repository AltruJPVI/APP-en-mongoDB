from flask import Blueprint, request, jsonify, current_app
from app.schemas.usuarios import UserResponse, UserUpdate, ItemCarrito
from pydantic import ValidationError
from bson import ObjectId

bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')

# ==================== PERFIL ====================


"""operacion http:

--PEFIL--

GET - ver perfil 
PUT - actualizar perfil

--CARRITO--

GET - ver carrito
DELETE - eliminar un producto del carrito
POST - añadir al carrito
DELETE - vaciar carrito

""" 

@bp.route('/<user_id>', methods=['GET'])
def get_perfil(user_id):
    """
    GET /api/usuarios/:user_id
    Obtener perfil de un usuario
    """
    try:
        # Validar ObjectId, verificacion extra para dar un error más refinado
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # Buscar usuario
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Convertir _id a string y eliminar password
        user['_id'] = str(user['_id'])
        user.pop('password', None)
        
        # Validar con Pydantic
        user_response = UserResponse(**user)
        
        return jsonify(user_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/<user_id>', methods=['PUT'])
def actualizar_perfil(user_id):
    """
    PUT /api/usuarios/:user_id
    Body: {"nombre": "...", "nivel": "...", "ubicacion": {...}}
    Actualizar información del perfil
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # Validar datos con Pydantic
        update_data = UserUpdate(**request.json)
        
        # Preparar actualización (solo campos no None)
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            return jsonify({"error": "No hay datos para actualizar"}), 400
        
        # Actualizar en MongoDB
        result = current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Obtener usuario actualizado
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        user['_id'] = str(user['_id'])
        user.pop('password', None)
        
        user_response = UserResponse(**user)
        
        return jsonify({
            "message": "Perfil actualizado exitosamente",
            "user": user_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== CARRITO ====================

@bp.route('/<user_id>/carrito', methods=['GET'])
def ver_carrito(user_id):
    """
    GET /api/usuarios/:user_id/carrito
    Ver el carrito de compras del usuario
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # Buscar usuario
        user = current_app.db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"carrito": 1}  # Solo traer el campo carrito
        )
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        carrito = user.get('carrito', [])
        
        # Calcular total
        total = sum(item['precio'] * item['cantidad'] for item in carrito)
        
        return jsonify({
            "carrito": carrito,
            "total_items": len(carrito),
            "total_precio": round(total, 2)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<user_id>/carrito', methods=['POST'])
def agregar_al_carrito(user_id):
    """
    POST /api/usuarios/:user_id/carrito
    Body: {
        "id_producto": "...",
        "nombre": "Raqueta Wilson",
        "precio": 120.50,
        "cantidad": 1,
        "talla": "M" (opcional)
    }
    Agregar un producto al carrito
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # Validar item con Pydantic
        item_data = ItemCarrito(**request.json)
        
        # Buscar si el producto ya está en el carrito
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        carrito = user.get('carrito', [])
        
        # Buscar si el producto ya existe (mismo id_producto y talla)
        producto_existente = None
        for i, item in enumerate(carrito):
            if (item['id_producto'] == item_data.id_producto and 
                item.get('talla') == item_data.talla):
                producto_existente = i
                break
        
        if producto_existente is not None:
            # Si existe, incrementar cantidad
            carrito[producto_existente]['cantidad'] += item_data.cantidad
            mensaje = "Cantidad actualizada en el carrito"
        else:
            # Si no existe, agregar nuevo item
            carrito.append(item_data.model_dump(exclude_none=True))
            mensaje = "Producto agregado al carrito"
        
        # Actualizar carrito en MongoDB
        current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"carrito": carrito}}
        )
        
        # Calcular nuevo total
        total = sum(item['precio'] * item['cantidad'] for item in carrito)
        
        return jsonify({
            "message": mensaje,
            "carrito": carrito,
            "total_items": len(carrito),
            "total_precio": round(total, 2)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<user_id>/carrito/<id_producto>', methods=['DELETE'])
def eliminar_del_carrito(user_id, id_producto):
    """
    DELETE /api/usuarios/:user_id/carrito/:id_producto?talla=M
    Eliminar un producto del carrito
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # Obtener talla de query params (opcional)
        talla = request.args.get('talla')
        
        # Buscar usuario
        user = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        carrito = user.get('carrito', [])
        
        # Filtrar el producto a eliminar
        carrito_nuevo = [
            item for item in carrito 
            if not (item['id_producto'] == id_producto and 
                   item.get('talla') == talla)
        ]
        
        if len(carrito) == len(carrito_nuevo):
            return jsonify({"error": "Producto no encontrado en el carrito"}), 404
        
        # Actualizar en MongoDB
        current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"carrito": carrito_nuevo}}
        )
        
        # Calcular nuevo total
        total = sum(item['precio'] * item['cantidad'] for item in carrito_nuevo)
        
        return jsonify({
            "message": "Producto eliminado del carrito",
            "carrito": carrito_nuevo,
            "total_items": len(carrito_nuevo),
            "total_precio": round(total, 2)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<user_id>/carrito', methods=['DELETE'])
def vaciar_carrito(user_id):
    """
    DELETE /api/usuarios/:user_id/carrito
    Vaciar todo el carrito
    """
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # Actualizar en MongoDB
        result = current_app.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"carrito": []}}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        return jsonify({
            "message": "Carrito vaciado exitosamente",
            "carrito": [],
            "total_items": 0,
            "total_precio": 0
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




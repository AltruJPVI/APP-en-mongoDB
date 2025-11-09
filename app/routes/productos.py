from flask import Blueprint, request, jsonify, current_app
from app.schemas.productos import ProductCreate, ProductResponse, ProductUpdate
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

# Crear blueprint para productos
bp = Blueprint('productos', __name__, url_prefix='/api/productos')

'''
--PRODUCTOS--

POST - crear producto
GET - ver productos
GET - ver 1 producto concreto
PUT - actualizar producto
DELETE - borrar producto

Get - ver cuantos productos hay de cada marca
GET - ver cuantos productos hay de cada categoria
'''


# ==================== CREAR PRODUCTO ====================

@bp.route('', methods=['POST'])
def crear_producto():
    """
    POST /api/productos
    Body: {
        "nombre": "Raqueta Wilson Pro",
        "precio": 120.50,
        "marca": "Wilson",
        "categoria": "raquetas",
        "genero": "unisex",
        "stock": 50,  // O usar tallas + stocks
        ...
    }
    """
    try:
        # Validar datos con Pydantic
        product_data = ProductCreate(**request.json)
        
        # Preparar documento para MongoDB
        product_dict = product_data.model_dump(exclude_none=True)
        
        # Agregar metadatos
        product_dict['fecha_creacion'] = datetime.now(timezone.utc)
        product_dict['total_comentarios'] = 0
        product_dict['valoracion_promedio'] = None
        product_dict['total_valoraciones'] = 0
        
        # Insertar en MongoDB
        result = current_app.db.products.insert_one(product_dict)
        
        # Preparar respuesta
        product_dict['_id'] = str(result.inserted_id)
        product_dict['comentarios'] = []
        
        product_response = ProductResponse(**product_dict)
        
        return jsonify({
            "message": "Producto creado exitosamente",
            "producto": product_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LISTAR PRODUCTOS (CON FILTROS SIMPLIFICADOS) ====================

@bp.route('', methods=['GET'])
def listar_productos():
    """
    GET /api/productos?categoria=raquetas&genero=unisex&precio_min=50&precio_max=200
                        &marca=Wilson&page=1&limit=20
    
    Filtros disponibles:
    - categoria: raquetas, zapatillas, camisetas, etc.
    - genero: hombre, mujer, unisex
    - precio_min / precio_max: rango de precios
    - marca: Wilson, Nike, Adidas, etc.
    - page: número de página (default: 1)
    - limit: productos por página (default: 20, max: 100)
    """
    try:
        # Construir filtro de MongoDB
        filtro = {"activo": True}  # Solo productos activos
        
        # Filtro por categoría
        categoria = request.args.get('categoria')
        if categoria:
            filtro['categoria'] = categoria
        
        # Filtro por género
        genero = request.args.get('genero')
        if genero:
            filtro['genero'] = genero
        
        # Filtro por marca
        marca = request.args.get('marca')
        if marca:
            filtro['marca'] = {'$regex': marca, '$options': 'i'}  # Case insensitive
        
        # Filtro por rango de precios
        precio_min = request.args.get('precio_min', type=float)
        precio_max = request.args.get('precio_max', type=float)
        if precio_min is not None or precio_max is not None:
            filtro['precio'] = {}
            if precio_min is not None:
                filtro['precio']['$gte'] = precio_min
            if precio_max is not None:
                filtro['precio']['$lte'] = precio_max
        
        # Paginación
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # Máximo 100 productos por página
        skip = (page - 1) * limit
        
        # Ordenar por fecha de creación (más recientes primero)
        productos_cursor = current_app.db.products.find(filtro).sort(
            'fecha_creacion', -1
        ).skip(skip).limit(limit)
        
        # Convertir a lista
        productos = []
        for producto in productos_cursor:
            producto['_id'] = str(producto['_id'])
            # Agregar campos por defecto si no existen
            producto.setdefault('comentarios', [])
            producto.setdefault('total_comentarios', 0)
            producto.setdefault('valoracion_promedio', None)
            producto.setdefault('total_valoraciones', 0)
                
            productos.append(ProductResponse(**producto).model_dump(exclude_none=True))
        
        # Contar total de productos (para paginación)
        total_productos = current_app.db.products.count_documents(filtro)
        total_pages = (total_productos + limit - 1) // limit
        
        return jsonify({
            "productos": productos,
            "paginacion": {
                "page": page,
                "limit": limit,
                "total_productos": total_productos,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VER DETALLE DE PRODUCTO ====================

@bp.route('/<product_id>', methods=['GET'])
def ver_producto(product_id):
    """
    GET /api/productos/:product_id
    Ver detalle completo de un producto
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(product_id):
            return jsonify({"error": "ID de producto inválido"}), 400
        
        # Buscar producto
        producto = current_app.db.products.find_one({"_id": ObjectId(product_id)})
        
        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404
        
        # Convertir _id a string
        producto['_id'] = str(producto['_id'])
        
        # Agregar campos por defecto si no existen
        producto.setdefault('comentarios', [])
        producto.setdefault('total_comentarios', 0)
        producto.setdefault('valoracion_promedio', None)
        producto.setdefault('total_valoraciones', 0)
        
        # Validar con Pydantic
        product_response = ProductResponse(**producto)
        
        return jsonify(product_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ACTUALIZAR PRODUCTO ====================

@bp.route('/<product_id>', methods=['PUT'])
def actualizar_producto(product_id):
    """
    PUT /api/productos/:product_id
    Body: {
        "clase": "admin",  // user, empresa, admin
        "precio": 150.00,
        "stock": 30,
        "activo": false,
        ...
    }
    
    DEMO: Solo admin o empresa pueden actualizar productos
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(product_id):
            return jsonify({"error": "ID de producto inválido"}), 400
        
        # Buscar producto primero
        producto = current_app.db.products.find_one({"_id": ObjectId(product_id)})
        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404
        
        # Obtener datos del body
        data = request.json
        clase = data.get('clase', 'user')
        
        # ✅ VERIFICACIÓN DE PERMISOS: Solo admin o empresa pueden actualizar
        if clase not in ['admin', 'empresa']:
            return jsonify({"error": "Solo admin o empresa pueden actualizar productos"}), 403
        
        # Remover clase del update
        data_copy = data.copy()
        data_copy.pop('clase', None)
        
        # Validar datos con Pydantic
        update_data = ProductUpdate(**data_copy)
        
        # Preparar actualización (solo campos no None)
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            return jsonify({"error": "No hay datos para actualizar"}), 400
        
        # Agregar fecha de última modificación
        update_dict['fecha_modificacion'] = datetime.now(timezone.utc)
        
        # Actualizar en MongoDB
        current_app.db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_dict}
        )
        
        # Obtener producto actualizado
        producto_actualizado = current_app.db.products.find_one({"_id": ObjectId(product_id)})
        producto_actualizado['_id'] = str(producto_actualizado['_id'])
        
        # Agregar campos por defecto
        producto_actualizado.setdefault('comentarios', [])
        producto_actualizado.setdefault('total_comentarios', 0)
        producto_actualizado.setdefault('valoracion_promedio', None)
        producto_actualizado.setdefault('total_valoraciones', 0)
        
        product_response = ProductResponse(**producto_actualizado)
        
        return jsonify({
            "message": "Producto actualizado exitosamente",
            "producto": product_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ELIMINAR PRODUCTO ====================

@bp.route('/<product_id>', methods=['DELETE'])
def eliminar_producto(product_id):
    """
    DELETE /api/productos/:product_id?soft=true
    Body: {
        "clase": "admin"  // user, empresa, admin
    }
    
    DEMO: Solo admin o empresa pueden eliminar productos
    
    Query params:
    - soft: true (default) = eliminación lógica (marca como inactivo)
    - soft: false = eliminación física (permanente)
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(product_id):
            return jsonify({"error": "ID de producto inválido"}), 400
        
        # Buscar producto
        producto = current_app.db.products.find_one({"_id": ObjectId(product_id)})
        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404
        
        # Obtener datos del body
        data = request.json or {}
        clase = data.get('clase', 'user')
        
        # ✅ VERIFICACIÓN DE PERMISOS: Solo admin o empresa pueden eliminar
        if clase not in ['admin', 'empresa']:
            return jsonify({"error": "Solo admin o empresa pueden eliminar productos"}), 403
        
        # Tipo de eliminación
        usar_eliminacion_logica = request.args.get('soft', 'true').lower() == 'true'
        
        if usar_eliminacion_logica:
            # Eliminación lógica: Solo marcar como inactivo
            current_app.db.products.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": {
                    "activo": False,
                    "fecha_eliminacion": datetime.now(timezone.utc)
                }}
            )
            mensaje = "Producto desactivado exitosamente"
        else:
            # Eliminación física: Borrar permanentemente
            current_app.db.products.delete_one({"_id": ObjectId(product_id)})
            
            # También eliminar sus comentarios
            current_app.db.comments.delete_many({
                "entidad_tipo": "producto",
                "entidad_id": product_id
            })
            
            mensaje = "Producto eliminado permanentemente"
        
        return jsonify({"message": mensaje}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ENDPOINTS ADICIONALES ÚTILES ====================

@bp.route('/categorias', methods=['GET'])
def listar_categorias():
    """
    GET /api/productos/categorias
    Listar todas las categorías disponibles con cantidad de productos
    """
    try:
        # Agregación para contar productos por categoría
        pipeline = [
            {"$match": {"activo": True}},
            {"$group": {
                "_id": "$categoria",
                "cantidad": {"$sum": 1}
            }},
            {"$sort": {"cantidad": -1}}
        ]
        
        categorias = list(current_app.db.products.aggregate(pipeline))
        
        # Formatear respuesta
        resultado = [
            {"categoria": cat["_id"], "cantidad": cat["cantidad"]}
            for cat in categorias
        ]
        
        return jsonify({"categorias": resultado}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/marcas', methods=['GET'])
def listar_marcas():
    """
    GET /api/productos/marcas
    Listar todas las marcas disponibles
    """
    try:
        # Obtener marcas únicas
        marcas = current_app.db.products.distinct("marca", {"activo": True})
        marcas_ordenadas = sorted(marcas)
        
        return jsonify({"marcas": marcas_ordenadas}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

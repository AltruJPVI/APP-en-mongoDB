from flask import Blueprint, request, jsonify, current_app
from app.schemas.pedidos import OrderCreate, OrderResponse
from pydantic import ValidationError
from bson import ObjectId
from datetime import datetime, timezone

# Crear blueprint para pedidos
bp = Blueprint('pedidos', __name__, url_prefix='/api/pedidos')

'''
--PEDIDOS--

POST - crear pedido
GET - ver pedidos de un usuario
GET - ver 1 pedido concreto
GET - ver todos los pedidos
'''
# ==================== CREAR PEDIDO (CON TRANSACCIONES ACID) ====================

@bp.route('', methods=['POST'])
def crear_pedido():
    """
    POST /api/pedidos
    Body: {
        "user_id": "507f1f77bcf86cd799439011",
        "items": [
            {
                "id_producto": "65abc123",
                "nombre": "Raqueta Wilson",
                "precio": 120.50,
                "cantidad": 2,
                "talla": "M",  // Opcional
                "imagen": "url.jpg"  // Opcional
            }
        ],
        "total": 241.00,
        "direccion_envio": {
            "calle": "Calle Mayor 123",
            "ciudad": "Madrid",
            "codigo_postal": "28001",
            "telefono": "612345678"
        },
        "metodo_pago": "tarjeta"
    }
    
    IMPORTANTE: Usa transacciones ACID para garantizar:
    1. Se crea el pedido
    2. Se reduce el stock de productos
    3. Se vacía el carrito del usuario
    Si CUALQUIER operación falla → ROLLBACK completo
    """
    try:
        # Validar datos con Pydantic
        order_data = OrderCreate(**request.json)
        
        # Validar que el usuario existe
        if not ObjectId.is_valid(order_data.user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        user = current_app.db.users.find_one({"_id": ObjectId(order_data.user_id)})
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Validar que todos los productos existen y hay stock suficiente
        validacion = _validar_stock_productos(order_data.items)
        if not validacion["valido"]:
            return jsonify({"error": validacion["mensaje"]}), 400
        
        # ==================== INICIO DE TRANSACCIÓN ACID ====================
        # Iniciar sesión de MongoDB para transacción
        session = current_app.mongo_client.start_session()
        
        try:
            with session.start_transaction():
                # 1. CREAR PEDIDO
                order_dict = order_data.model_dump(exclude_none=True)
                order_dict['numero_pedido'] = _generar_numero_pedido()
                order_dict['fecha_pedido'] = datetime.now(timezone.utc)
                
                # Insertar pedido (dentro de la transacción)
                result = current_app.db.orders.insert_one(order_dict, session=session)
                order_id = result.inserted_id
                
                # 2. REDUCIR STOCK DE PRODUCTOS
                for item in order_data.items:
                    # Validar ObjectId del producto
                    if not ObjectId.is_valid(item.id_producto):
                        raise Exception(f"ID de producto inválido: {item.id_producto}")
                    
                    producto = current_app.db.products.find_one(
                        {"_id": ObjectId(item.id_producto)},
                        session=session
                    )
                    
                    if not producto:
                        raise Exception(f"Producto no encontrado: {item.nombre}")
                    
                    # Reducir stock según el tipo
                    if item.talla:
                        # Producto con tallas
                        if 'stocks' not in producto:
                            raise Exception(f"Producto {item.nombre} no tiene tallas definidas")
                        
                        # Buscar la talla y reducir stock
                        talla_encontrada = False
                        for stock_item in producto.get('stocks', []):
                            if stock_item['talla'] == item.talla:
                                nuevo_stock = stock_item['stock'] - item.cantidad
                                if nuevo_stock < 0:
                                    raise Exception(
                                        f"Stock insuficiente para {item.nombre} talla {item.talla}"
                                    )
                                
                                # Actualizar stock de la talla específica
                                current_app.db.products.update_one(
                                    {
                                        "_id": ObjectId(item.id_producto),
                                        "stocks.talla": item.talla
                                    },
                                    {"$set": {"stocks.$.stock": nuevo_stock}},
                                    session=session
                                )
                                talla_encontrada = True
                                break
                        
                        if not talla_encontrada:
                            raise Exception(
                                f"Talla {item.talla} no encontrada para {item.nombre}"
                            )
                    else:
                        # Producto con stock simple
                        stock_actual = producto.get('stock', 0)
                        nuevo_stock = stock_actual - item.cantidad
                        
                        if nuevo_stock < 0:
                            raise Exception(f"Stock insuficiente para {item.nombre}")
                        
                        # Actualizar stock simple
                        current_app.db.products.update_one(
                            {"_id": ObjectId(item.id_producto)},
                            {"$set": {"stock": nuevo_stock}},
                            session=session
                        )
                
                # 3. VACIAR CARRITO DEL USUARIO
                current_app.db.users.update_one(
                    {"_id": ObjectId(order_data.user_id)},
                    {"$set": {"carrito": []}},
                    session=session
                )
                
                # Si llegamos aquí, todo OK → COMMIT automático al salir del with
                
        except Exception as e:
            # Si algo falla → ROLLBACK automático
            raise e
        finally:
            session.end_session()
        
        # ==================== FIN DE TRANSACCIÓN ====================
        
        # Obtener el pedido creado para devolver
        pedido = current_app.db.orders.find_one({"_id": order_id})
        pedido['_id'] = str(pedido['_id'])
        
        order_response = OrderResponse(**pedido)
        
        return jsonify({
            "message": "Pedido creado exitosamente",
            "pedido": order_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LISTAR PEDIDOS DE UN USUARIO ====================

@bp.route('/usuario/<user_id>', methods=['GET'])
def listar_pedidos_usuario(user_id):
    """
    GET /api/pedidos/usuario/:user_id?page=1&limit=20
    Body: {
        "usuario_id_peticion": "507f...",  // ID del usuario que hace la petición
        "clase": "user"  // user, empresa, admin
    }
    
    DEMO: Solo el propio usuario o admin pueden ver sus pedidos
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(user_id):
            return jsonify({"error": "ID de usuario inválido"}), 400
        
        # ✅ VERIFICACIÓN DE PERMISOS (desde body)
        data = request.json or {}
        usuario_id_peticion = data.get('usuario_id_peticion')
        clase = data.get('clase', 'user')
        
        if not usuario_id_peticion:
            return jsonify({"error": "usuario_id_peticion es requerido"}), 400
        
        # Verificar: es el propio usuario O es admin
        es_propio_usuario = user_id == usuario_id_peticion
        es_admin = clase == 'admin'
        
        if not (es_propio_usuario or es_admin):
            return jsonify({"error": "Solo puedes ver tus propios pedidos"}), 403
        
        # Paginación (sigue en query params)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)
        skip = (page - 1) * limit
        
        # Buscar pedidos del usuario (más recientes primero)
        pedidos_cursor = current_app.db.orders.find(
            {"user_id": user_id}
        ).sort("fecha_pedido", -1).skip(skip).limit(limit)
        
        pedidos = []
        for pedido in pedidos_cursor:
            pedido['_id'] = str(pedido['_id'])
            pedidos.append(OrderResponse(**pedido).model_dump(exclude_none=True))
        
        # Contar total
        total_pedidos = current_app.db.orders.count_documents({"user_id": user_id})
        total_pages = (total_pedidos + limit - 1) // limit
        
        return jsonify({
            "pedidos": pedidos,
            "paginacion": {
                "page": page,
                "limit": limit,
                "total_pedidos": total_pedidos,
                "total_pages": total_pages
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== VER DETALLE DE PEDIDO ====================

@bp.route('/<order_id>', methods=['GET'])
def ver_pedido(order_id):
    """
    GET /api/pedidos/:order_id
    Body: {
        "usuario_id": "507f...",  // ID del usuario que hace la petición
        "clase": "user"  // user, empresa, admin
    }
    
    DEMO: Solo el dueño del pedido o admin pueden verlo
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(order_id):
            return jsonify({"error": "ID de pedido inválido"}), 400
        
        # Buscar pedido
        pedido = current_app.db.orders.find_one({"_id": ObjectId(order_id)})
        
        if not pedido:
            return jsonify({"error": "Pedido no encontrado"}), 404
        
        # ✅ VERIFICACIÓN DE PERMISOS (desde body)
        data = request.json or {}
        usuario_id_peticion = data.get('usuario_id')
        clase = data.get('clase', 'user')
        
        if not usuario_id_peticion:
            return jsonify({"error": "usuario_id es requerido"}), 400
        
        # Verificar: es el dueño del pedido O es admin
        es_dueño = pedido['user_id'] == usuario_id_peticion
        es_admin = clase == 'admin'
        
        if not (es_dueño or es_admin):
            return jsonify({"error": "No tienes permisos para ver este pedido"}), 403
        
        # Convertir _id a string
        pedido['_id'] = str(pedido['_id'])
        
        order_response = OrderResponse(**pedido)
        
        return jsonify(order_response.model_dump(exclude_none=True)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== LISTAR TODOS LOS PEDIDOS (ADMIN) ====================

@bp.route('', methods=['GET'])
def listar_todos_pedidos():
    """
    GET /api/pedidos?page=1&limit=20&fecha_desde=2025-01-01&metodo_pago=tarjeta
    Body: {
        "clase": "admin"  // Debe ser admin
    }
    
    Listar todos los pedidos (solo admin)
    
    Filtros en query params:
    - fecha_desde / fecha_hasta: rango de fechas
    - metodo_pago: tarjeta, paypal, transferencia
    - user_id: pedidos de un usuario específico
    - numero_pedido: buscar por número de pedido
    
    DEMO: Solo admin puede listar todos los pedidos
    """
    try:
        # ✅ VERIFICACIÓN DE PERMISOS: Solo admin (desde body)
        data = request.json or {}
        clase = data.get('clase', 'user')
        
        if clase != 'admin':
            return jsonify({"error": "Solo admin puede listar todos los pedidos"}), 403
        
        # Construir filtro
        filtro = {}
        
        # Filtro por usuario
        user_id = request.args.get('user_id')
        if user_id:
            filtro['user_id'] = user_id
        
        # Filtro por método de pago
        metodo_pago = request.args.get('metodo_pago')
        if metodo_pago:
            filtro['metodo_pago'] = metodo_pago
        
        # Filtro por número de pedido
        numero_pedido = request.args.get('numero_pedido')
        if numero_pedido:
            filtro['numero_pedido'] = {'$regex': numero_pedido, '$options': 'i'}
        
        # Filtro por rango de fechas
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        if fecha_desde or fecha_hasta:
            filtro['fecha_pedido'] = {}
            if fecha_desde:
                try:
                    fecha_desde_dt = datetime.fromisoformat(fecha_desde.replace('Z', '+00:00'))
                    filtro['fecha_pedido']['$gte'] = fecha_desde_dt
                except ValueError:
                    return jsonify({"error": "Formato de fecha_desde inválido (usa ISO: 2025-01-01)"}), 400
            if fecha_hasta:
                try:
                    fecha_hasta_dt = datetime.fromisoformat(fecha_hasta.replace('Z', '+00:00'))
                    filtro['fecha_pedido']['$lte'] = fecha_hasta_dt
                except ValueError:
                    return jsonify({"error": "Formato de fecha_hasta inválido (usa ISO: 2025-01-01)"}), 400
        
        # Paginación
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)
        skip = (page - 1) * limit
        
        # Buscar pedidos
        pedidos_cursor = current_app.db.orders.find(filtro).sort(
            "fecha_pedido", -1
        ).skip(skip).limit(limit)
        
        pedidos = []
        for pedido in pedidos_cursor:
            pedido['_id'] = str(pedido['_id'])
            pedidos.append(OrderResponse(**pedido).model_dump(exclude_none=True))
        
        # Contar total
        total_pedidos = current_app.db.orders.count_documents(filtro)
        total_pages = (total_pedidos + limit - 1) // limit
        
        return jsonify({
            "pedidos": pedidos,
            "paginacion": {
                "page": page,
                "limit": limit,
                "total_pedidos": total_pedidos,
                "total_pages": total_pages
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== FUNCIONES AUXILIARES ====================

def _validar_stock_productos(items):
    """
    Validar que todos los productos existen y tienen stock suficiente
    ANTES de iniciar la transacción
    """
    for item in items:
        # Validar ObjectId
        if not ObjectId.is_valid(item.id_producto):
            return {
                "valido": False,
                "mensaje": f"ID de producto inválido: {item.id_producto}"
            }
        
        # Buscar producto
        producto = current_app.db.products.find_one({"_id": ObjectId(item.id_producto)})
        
        if not producto:
            return {
                "valido": False,
                "mensaje": f"Producto no encontrado: {item.nombre}"
            }
        
        # Verificar que esté activo
        if not producto.get('activo', True):
            return {
                "valido": False,
                "mensaje": f"El producto {item.nombre} ya no está disponible"
            }
        
        # Verificar stock según tipo
        if item.talla:
            # Producto con tallas
            if 'stocks' not in producto:
                return {
                    "valido": False,
                    "mensaje": f"El producto {item.nombre} no tiene tallas definidas"
                }
            
            talla_encontrada = False
            for stock_item in producto.get('stocks', []):
                if stock_item['talla'] == item.talla:
                    if stock_item['stock'] < item.cantidad:
                        return {
                            "valido": False,
                            "mensaje": f"Stock insuficiente para {item.nombre} talla {item.talla}. Disponible: {stock_item['stock']}"
                        }
                    talla_encontrada = True
                    break
            
            if not talla_encontrada:
                return {
                    "valido": False,
                    "mensaje": f"Talla {item.talla} no disponible para {item.nombre}"
                }
        else:
            # Producto con stock simple
            stock_actual = producto.get('stock', 0)
            if stock_actual < item.cantidad:
                return {
                    "valido": False,
                    "mensaje": f"Stock insuficiente para {item.nombre}. Disponible: {stock_actual}"
                }
    
    return {"valido": True, "mensaje": ""}


def _generar_numero_pedido():
    """
    Generar número de pedido único
    Formato: PED-YYYY-NNNNNN
    Ejemplo: PED-2025-000123
    """
    year = datetime.now().year
    
    # Contar pedidos del año actual
    inicio_año = datetime(year, 1, 1, tzinfo=timezone.utc)
    pedidos_año = current_app.db.orders.count_documents({
        "fecha_pedido": {"$gte": inicio_año}
    })
    
    # Incrementar contador
    numero = pedidos_año + 1
    
    # Formatear: PED-2025-000123
    numero_pedido = f"PED-{year}-{numero:06d}"
    
    return numero_pedido

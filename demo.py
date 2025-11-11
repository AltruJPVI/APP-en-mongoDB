"""
Demo automática - Flujo de compra completo
===========================================
Registra usuario → Login → Ver productos → Carrito → Pedido
"""

import requests
import time
import sys
from typing import Optional, Dict, Any, List

API = "http://api:5000/api"


def print_step(msg):
    """Imprime un paso del proceso con formato destacado"""
    print(f"\n{'='*70}\n{msg}\n{'='*70}")

def print_ok(msg):
    """Imprime mensaje de éxito"""
    print(f"✅ {msg}")

def print_error(msg):
    """Imprime mensaje de error"""
    print(f"❌ {msg}")

def print_warning(msg):
    """Imprime mensaje de advertencia"""
    print(f"⚠️  {msg}")

def print_info(msg):
    """Imprime mensaje informativo"""
    print(f"ℹ️  {msg}")

# ============================================================================
# UTILIDADES DE VALIDACIÓN Y MANEJO DE ERRORES
# ============================================================================

def validar_respuesta(response: requests.Response, operacion: str) -> Optional[Dict[Any, Any]]:
    """Valida una respuesta HTTP y devuelve el JSON o None si hay error"""
    try:
        if response.status_code in [200, 201]:
            return response.json()
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('error', 'Error desconocido')
            print_error(f"Error en {operacion}: {error_msg}")
            if 'details' in error_data:
                print(f"   Detalles: {error_data['details']}")
            return None
    except requests.exceptions.JSONDecodeError:
        print_error(f"Error en {operacion}: Respuesta inválida del servidor")
        return None
    except Exception as e:
        print_error(f"Error inesperado en {operacion}: {str(e)}")
        return None

def hacer_peticion(method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
    """Hace una petición HTTP con manejo de errores"""
    try:
        url = f"{API}{endpoint}"
        response = requests.request(method, url, timeout=10, **kwargs)
        return response
    except requests.exceptions.Timeout:
        print_error("Timeout: El servidor no responde")
        return None
    except requests.exceptions.ConnectionError:
        print_error("Error de conexión: No se puede conectar con el servidor")
        print_info("Asegúrate de que los contenedores estén ejecutándose (docker-compose up)")
        return None
    except Exception as e:
        print_error(f"Error inesperado: {str(e)}")
        return None

def input_seguro(prompt: str, opciones: Optional[List[str]] = None, default: str = "") -> str:
    """Input con validación y opción de salir"""
    while True:
        try:
            valor = input(prompt).strip()
            
            # Permitir salir en cualquier momento
            if valor.lower() in ['salir', 'exit', 'quit']:
                print_info("Saliendo de la demo...")
                sys.exit(0)
            
            # Si está vacío y hay default
            if not valor and default:
                return default
            
            # Si hay opciones válidas
            if opciones and valor.lower() not in [o.lower() for o in opciones]:
                print_warning(f"Opción inválida. Elige entre: {', '.join(opciones)}")
                continue
            
            return valor
        except KeyboardInterrupt:
            print_info("\n\nDemo interrumpida por el usuario")
            sys.exit(0)
        except EOFError:
            print_error("\nError de entrada")
            sys.exit(1)

def input_numero(prompt: str, min_val: int = 1, max_val: Optional[int] = None) -> int:
    """Input numérico con validación"""
    while True:
        valor = input_seguro(prompt)
        
        if not valor.isdigit():
            print_warning("Debes introducir un número")
            continue
        
        num = int(valor)
        
        if num < min_val:
            print_warning(f"El número debe ser mayor o igual a {min_val}")
            continue
        
        if max_val and num > max_val:
            print_warning(f"El número debe ser menor o igual a {max_val}")
            continue
        
        return num

# ============================================================================
# UTILIDADES DE PRODUCTOS Y STOCK
# ============================================================================

def mostrar_stock_producto(producto: Dict[Any, Any]) -> str:
    """Devuelve una representación del stock del producto"""
    if 'stocks' in producto and producto['stocks']:
        # Producto con tallas
        tallas_disponibles = [
            f"{s['talla']}({s['stock']})" 
            for s in producto['stocks'] 
            if s['stock'] > 0
        ]
        if tallas_disponibles:
            return f"Tallas: {', '.join(tallas_disponibles)}"
        else:
            return "Sin stock"
    else:
        # Producto sin tallas
        stock = producto.get('stock', 0)
        return f"Stock: {stock}" if stock > 0 else "Sin stock"

def tiene_stock(producto: Dict[Any, Any], talla: Optional[str] = None) -> bool:
    """Verifica si un producto tiene stock disponible"""
    if 'stocks' in producto and producto['stocks']:
        if talla:
            for s in producto['stocks']:
                if s['talla'] == talla and s['stock'] > 0:
                    return True
            return False
        else:
            return any(s['stock'] > 0 for s in producto['stocks'])
    else:
        return producto.get('stock', 0) > 0

def obtener_stock_disponible(producto: Dict[Any, Any], talla: Optional[str] = None) -> int:
    """Obtiene la cantidad de stock disponible"""
    if 'stocks' in producto and producto['stocks']:
        if talla:
            for s in producto['stocks']:
                if s['talla'] == talla:
                    return s['stock']
            return 0
        else:
            return sum(s['stock'] for s in producto['stocks'])
    else:
        return producto.get('stock', 0)

def seleccionar_talla(producto: Dict[Any, Any]) -> Optional[str]:
    """Permite al usuario seleccionar una talla si el producto las tiene"""
    if 'stocks' not in producto or not producto['stocks']:
        return None
    
    print(f"\n👕 Tallas disponibles para '{producto['nombre']}':")
    tallas_con_stock = [s for s in producto['stocks'] if s['stock'] > 0]
    
    if not tallas_con_stock:
        print_error("No hay tallas con stock disponible")
        return None
    
    for i, stock_item in enumerate(tallas_con_stock, 1):
        print(f"   {i}. Talla {stock_item['talla']} - Stock: {stock_item['stock']}")
    
    while True:
        seleccion = input_seguro("\n¿Qué talla quieres? (número): ")
        
        if not seleccion.isdigit() or not (1 <= int(seleccion) <= len(tallas_con_stock)):
            print_warning(f"Selecciona un número entre 1 y {len(tallas_con_stock)}")
            continue
        
        idx = int(seleccion) - 1
        return tallas_con_stock[idx]['talla']

def mostrar_carrito(user_id: str) -> Optional[List[Dict[Any, Any]]]:
    """Muestra el contenido actual del carrito"""
    response = hacer_peticion('GET', f"/usuarios/{user_id}/carrito")
    
    if not response:
        return None
    
    data = validar_respuesta(response, "obtener carrito")
    if not data:
        return None
    
    items = data.get('carrito', [])
    total = data.get('total_precio', 0)
    
    if not items:
        print_info("Tu carrito está vacío")
        return []
    
    print(f"\n🛒 Carrito actual ({len(items)} items):")
    for i, item in enumerate(items, 1):
        talla_str = f" - Talla: {item['talla']}" if item.get('talla') else ""
        subtotal = item['precio'] * item['cantidad']
        print(f"   {i}. {item['nombre']}{talla_str}")
        print(f"      {item['cantidad']}x €{item['precio']:.2f} = €{subtotal:.2f}")
    print(f"\n   💰 Total: €{total:.2f}")
    
    return items

# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================

def main():
    print_step("🎾 DEMO INTERACTIVA - TIENDA TENIS SOCIAL")
    print("\n👋 ¡Bienvenido! Esta demo te guiará por el proceso de compra completo.")
    print("💡 Tip: Puedes escribir 'salir' en cualquier momento para terminar\n")
    
    # ==========================================================================
    # 1. REGISTRO O LOGIN
    # ==========================================================================
    
    print("¿Qué quieres hacer?")
    print("1. Registrarme como nuevo usuario")
    print("2. Hacer login con usuario existente")
    
    opcion = input_seguro("\nElige opción (1/2): ", opciones=['1', '2'])
    
    user_id = None
    user_nombre = None
    
    if opcion == "1":
        # REGISTRO
        print_step("1️⃣  REGISTRO DE NUEVO USUARIO")
        
        nombre = input_seguro("Nombre: ")
        email = input_seguro("Email: ")
        password = input_seguro("Contraseña (min 4 caracteres): ")
        
        if len(password) < 4:
            print_error("La contraseña debe tener al menos 4 caracteres")
            return
        
        print("\nNivel de juego:")
        print("  1. principiante")
        print("  2. intermedio")
        print("  3. avanzado")
        
        nivel_opcion = input_seguro("Elige (1/2/3): ", opciones=['1', '2', '3'])
        niveles = {"1": "principiante", "2": "intermedio", "3": "avanzado"}
        nivel = niveles[nivel_opcion]
        
        response = hacer_peticion('POST', "/auth/register", json={
            "nombre": nombre,
            "email": email,
            "password": password,
            "clase": "user",
            "nivel": nivel
        })
        
        if not response:
            print_error("No se pudo conectar con el servidor")
            return
        
        data = validar_respuesta(response, "registro")
        if not data:
            return
        
        user = data.get('user', {})
        user_id = user.get('id')
        user_nombre = user.get('nombre')
        
        print_ok(f"Usuario registrado: {user_nombre} (ID: {user_id})")
        
    else:
        # LOGIN
        print_step("1️⃣  LOGIN")
        
        email = input_seguro("Email: ")
        password = input_seguro("Contraseña: ")
        
        response = hacer_peticion('POST', "/auth/login", json={
            "email": email,
            "password": password
        })
        
        if not response:
            print_error("No se pudo conectar con el servidor")
            return
        
        data = validar_respuesta(response, "login")
        if not data:
            return
        
        user = data.get('user', {})
        user_id = user.get('id')
        user_nombre = user.get('nombre')
        
        print_ok(f"Bienvenido de nuevo: {user_nombre}")
    
    if not user_id:
        print_error("No se pudo obtener el ID de usuario")
        return
    
    time.sleep(1)
    
    # ==========================================================================
    # 2. VER PRODUCTOS
    # ==========================================================================
    
    print_step("2️⃣  CATÁLOGO DE PRODUCTOS")
    
    limite = input_numero("¿Cuántos productos quieres ver? (5-20): ", min_val=5, max_val=20)
    
    response = hacer_peticion('GET', f"/productos?limit={limite}")
    
    if not response:
        print_error("No se pudieron obtener los productos")
        return
    
    data = validar_respuesta(response, "obtener productos")
    if not data:
        return
    
    productos = data.get('productos', [])
    
    if not productos:
        print_error("No hay productos disponibles")
        return
    
    print_ok(f"Mostrando {len(productos)} productos:\n")
    
    for i, p in enumerate(productos, 1):
        stock_info = mostrar_stock_producto(p)
        disponible = "✅" if tiene_stock(p) else "❌"
        print(f"{i:2}. {disponible} {p['nombre'][:40]:40} - €{p['precio']:>7.2f}")
        print(f"     {stock_info}")
    
    time.sleep(1)
    
    # ==========================================================================
    # 3. AGREGAR AL CARRITO
    # ==========================================================================
    
    print_step("3️⃣  AGREGAR AL CARRITO")
    
    carrito_items = []
    
    while True:
        # Mostrar carrito actual si tiene items
        items_actuales = mostrar_carrito(user_id)
        
        print("\n¿Qué quieres hacer?")
        print("1. Agregar producto al carrito")
        print("2. Continuar con el pedido")
        print("3. Salir")
        
        accion = input_seguro("\nElige opción (1/2/3): ", opciones=['1', '2', '3'])
        
        if accion == '3':
            print_info("Demo cancelada")
            return
        
        if accion == '2':
            if not items_actuales:
                print_warning("Tu carrito está vacío. Agrega al menos un producto.")
                continue
            break
        
        # Agregar producto
        print("\n📦 Selecciona un producto:")
        seleccion = input_numero(
            f"Número del producto (1-{len(productos)}) o 0 para volver: ",
            min_val=0,
            max_val=len(productos)
        )
        
        if seleccion == 0:
            continue
        
        idx = seleccion - 1
        producto = productos[idx]
        
        # Verificar stock
        if not tiene_stock(producto):
            print_error(f"'{producto['nombre']}' no tiene stock disponible")
            continue
        
        print(f"\n✅ Producto: {producto['nombre']}")
        print(f"   Precio: €{producto['precio']:.2f}")
        
        # Seleccionar talla si aplica
        talla = None
        if 'stocks' in producto and producto['stocks']:
            talla = seleccionar_talla(producto)
            if not talla:
                continue
            stock_disponible = obtener_stock_disponible(producto, talla)
        else:
            stock_disponible = obtener_stock_disponible(producto)
        
        # Seleccionar cantidad
        print(f"\n📊 Stock disponible: {stock_disponible}")
        cantidad = input_numero(
            f"¿Cuántas unidades quieres? (1-{min(stock_disponible, 10)}): ",
            min_val=1,
            max_val=min(stock_disponible, 10)
        )
        
        # Agregar al carrito
        item_carrito = {
            "id_producto": producto['id'],
            "nombre": producto['nombre'],
            "precio": producto['precio'],
            "cantidad": cantidad
        }
        
        if talla:
            item_carrito["talla"] = talla
        
        response = hacer_peticion('POST', f"/usuarios/{user_id}/carrito", json=item_carrito)
        
        if not response:
            print_error("No se pudo agregar al carrito")
            continue
        
        data = validar_respuesta(response, "agregar al carrito")
        if not data:
            continue
        
        talla_str = f" (Talla: {talla})" if talla else ""
        print_ok(f"Agregado: {producto['nombre']}{talla_str} x{cantidad}")
        
        continuar = input_seguro("\n¿Seguir comprando? (s/n): ", opciones=['s', 'n', 'si', 'no'])
        if continuar.lower() in ['n', 'no']:
            break
    
    # Mostrar carrito final
    time.sleep(0.5)
    items_carrito = mostrar_carrito(user_id)
    
    if not items_carrito:
        print_error("El carrito está vacío. Demo finalizada.")
        return
    
    time.sleep(1)
    
    # ==========================================================================
    # 4. CREAR PEDIDO
    # ==========================================================================
    
    print_step("4️⃣  CONFIRMAR PEDIDO")
    
    confirmar = input_seguro("\n¿Crear pedido con estos productos? (s/n): ", opciones=['s', 'n', 'si', 'no'])
    
    if confirmar.lower() in ['n', 'no']:
        print_info("Pedido cancelado")
        return
    
    # Dirección de envío
    print("\n📍 Dirección de envío:")
    usar_default = input_seguro("¿Usar dirección por defecto? (s/n): ", opciones=['s', 'n', 'si', 'no'])
    
    if usar_default.lower() in ['s', 'si']:
        calle = "Calle Demo 123"
        ciudad = "Madrid"
        codigo_postal = "28001"
        telefono = "612345678"
        print(f"   {calle}, {ciudad}, {codigo_postal}")
        print(f"   Tel: {telefono}")
    else:
        calle = input_seguro("Calle: ")
        ciudad = input_seguro("Ciudad: ")
        codigo_postal = input_seguro("Código postal: ")
        telefono = input_seguro("Teléfono: ")
    
    # Método de pago
    print("\n💳 Método de pago:")
    print("  1. tarjeta")
    print("  2. paypal")
    print("  3. transferencia")
    
    metodo_opcion = input_seguro("Elige (1/2/3): ", opciones=['1', '2', '3'])
    metodos = {"1": "tarjeta", "2": "paypal", "3": "transferencia"}
    metodo_pago = metodos[metodo_opcion]
    
    # Obtener información de stock ANTES de crear el pedido
    productos_seguimiento = {}
    for item in items_carrito:
        response = hacer_peticion('GET', f"/productos/{item['id_producto']}")
        if response:
            data = validar_respuesta(response, "obtener producto")
            if data:
                productos_seguimiento[item['id_producto']] = {
                    'nombre': data['nombre'],
                    'stock_antes': obtener_stock_disponible(data, item.get('talla')),
                    'talla': item.get('talla'),
                    'cantidad_pedida': item['cantidad']
                }
    
    # Calcular total
    total = sum(item['precio'] * item['cantidad'] for item in items_carrito)
    
    print(f"\n⚡ Creando pedido por valor de €{total:.2f}...")
    
    # Crear pedido con transacción ACID
    response = hacer_peticion('POST', "/pedidos", json={
        "user_id": user_id,
        "items": [
            {
                "id_producto": item['id_producto'],
                "nombre": item['nombre'],
                "precio": item['precio'],
                "cantidad": item['cantidad'],
                "talla": item.get('talla')
            } for item in items_carrito
        ],
        "total": total,
        "direccion_envio": {
            "calle": calle,
            "ciudad": ciudad,
            "codigo_postal": codigo_postal,
            "telefono": telefono
        },
        "metodo_pago": metodo_pago
    })
    
    if not response:
        print_error("No se pudo crear el pedido")
        return
    
    data = validar_respuesta(response, "crear pedido")
    if not data:
        return
    
    pedido = data.get('pedido', {})
    print_ok(f"Pedido creado: {pedido['numero_pedido']}")
    
    # Verificar stock DESPUÉS del pedido
    time.sleep(0.5)
    print("\n📊 Verificación de stock tras la transacción ACID:")
    
    for producto_id, info in productos_seguimiento.items():
        response = hacer_peticion('GET', f"/productos/{producto_id}")
        if response:
            data = validar_respuesta(response, "verificar stock")
            if data:
                stock_despues = obtener_stock_disponible(data, info['talla'])
                reduccion = info['stock_antes'] - stock_despues
                
                talla_str = f" (Talla {info['talla']})" if info['talla'] else ""
                print(f"\n   • {info['nombre']}{talla_str}")
                print(f"     Stock antes:  {info['stock_antes']} unidades")
                print(f"     Stock después: {stock_despues} unidades")
                print(f"     Reducción:    -{reduccion} unidades ✅")
    
    # Verificar carrito vaciado
    time.sleep(0.5)
    response = hacer_peticion('GET', f"/usuarios/{user_id}/carrito")
    if response:
        data = validar_respuesta(response, "verificar carrito")
        if data:
            items_final = data.get('carrito', [])
            if len(items_final) == 0:
                print_ok("Carrito vaciado automáticamente ✅")
            else:
                print_warning(f"El carrito aún tiene {len(items_final)} items")
    
    # ==========================================================================
    # 5. RESUMEN FINAL
    # ==========================================================================
    
    print_step("✅ PEDIDO COMPLETADO CON ÉXITO")
    
    print(f"""
🎉 ¡Felicidades {user_nombre}! Tu pedido se ha procesado correctamente.

📦 Resumen del pedido:
   Número de pedido: {pedido['numero_pedido']}
   Total: €{pedido['total']:.2f}
   Productos: {len(items_carrito)} items
   Método de pago: {pedido['metodo_pago']}
   
📍 Envío a:
   {calle}
   {ciudad}, {codigo_postal}
   Tel: {telefono}

🔐 Transacción ACID completada:
   ✅ Pedido creado en la base de datos
   ✅ Stock de productos reducido correctamente
   ✅ Carrito del usuario vaciado
   
💡 ¿Qué pasó detrás de escena?
   MongoDB ejecutó una transacción ACID que garantiza que TODAS
   estas operaciones se completen o NINGUNA. Si cualquier paso
   falla, se hace rollback automático de todos los cambios.
   
🎾 ¡Gracias por probar la demo! Disfruta del tenis.
""")

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_info("\n\nDemo interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        print_error(f"Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

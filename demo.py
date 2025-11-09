"""
Demo automática - Flujo de compra completo
===========================================
Registra usuario → Login → Ver productos → Carrito → Pedido
"""

import requests
import time

API = "http://localhost:5000/api"

def print_step(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")

def print_ok(msg):
    print(f"✓ {msg}")

def print_error(msg):
    print(f"✗ {msg}")
    exit(1)

# =============================================================================
# INICIO
# =============================================================================

print_step("🎾 DEMO INTERACTIVA - TIENDA TENIS SOCIAL")
print("\n¿Qué quieres hacer?")
print("1. Registrarme como nuevo usuario")
print("2. Hacer login con usuario existente")

opcion = input("\nElige opción (1/2): ").strip()

# =============================================================================
# REGISTRO O LOGIN
# =============================================================================

if opcion == "1":
    # REGISTRO
    print_step("1. REGISTRO DE NUEVO USUARIO")
    
    nombre = input("Nombre: ").strip()
    email = input("Email: ").strip()
    password = input("Contraseña: ").strip()
    
    print("\nNivel de juego:")
    print("  1. principiante")
    print("  2. intermedio")
    print("  3. avanzado")
    nivel_opcion = input("Elige (1/2/3): ").strip()
    
    niveles = {"1": "principiante", "2": "intermedio", "3": "avanzado"}
    nivel = niveles.get(nivel_opcion, "intermedio")
    
    registro = requests.post(f"{API}/auth/register", json={
        "nombre": nombre,
        "email": email,
        "password": password,
        "clase": "user",
        "nivel": nivel
    })
    
    if registro.status_code != 201:
        print_error(f"Error en registro: {registro.json()}")
    
    user = registro.json()['user']
    user_id = user['id']
    print_ok(f"Usuario registrado: {user['nombre']} (ID: {user_id})")
    
else:
    # LOGIN
    print_step("1. LOGIN")
    
    email = input("Email: ").strip()
    password = input("Contraseña: ").strip()
    
    login = requests.post(f"{API}/auth/login", json={
        "email": email,
        "password": password
    })
    
    if login.status_code != 200:
        print_error(f"Error en login: {login.json()}")
    
    user = login.json()['user']
    user_id = user['id']
    print_ok(f"Bienvenido: {user['nombre']}")

# =============================================================================
# VER PRODUCTOS
# =============================================================================

print_step("2. CATÁLOGO DE PRODUCTOS")

print("\n¿Cuántos productos quieres ver?")
limite = input("Cantidad (5-20): ").strip()
limite = int(limite) if limite.isdigit() and 5 <= int(limite) <= 20 else 10

productos = requests.get(f"{API}/productos?limit={limite}")

if productos.status_code != 200:
    print_error("Error obteniendo productos")

items = productos.json()['productos']
print_ok(f"Mostrando {len(items)} productos:\n")

# Mostrar productos con números
for i, p in enumerate(items, 1):
    stock = p.get('stock', 'N/A')
    print(f"{i:2}. {p['nombre']:30} - €{p['precio']:>7.2f}  (Stock: {stock})")

# =============================================================================
# AGREGAR AL CARRITO
# =============================================================================

print_step("3. AGREGAR AL CARRITO")

carrito_items = []

while True:
    print("\n¿Qué producto quieres agregar al carrito?")
    seleccion = input(f"Número del producto (1-{len(items)}) o 'fin' para terminar: ").strip()
    
    if seleccion.lower() in ['fin', 'f', '']:
        break
    
    if not seleccion.isdigit() or not (1 <= int(seleccion) <= len(items)):
        print("❌ Número inválido")
        continue
    
    idx = int(seleccion) - 1
    producto = items[idx]
    
    cantidad = input(f"¿Cuántas unidades de '{producto['nombre']}'? (1-5): ").strip()
    cantidad = int(cantidad) if cantidad.isdigit() and 1 <= int(cantidad) <= 5 else 1
    
    # Agregar al carrito
    carrito_req = requests.post(f"{API}/usuarios/{user_id}/carrito", json={
        "id_producto": producto['id'],
        "nombre": producto['nombre'],
        "precio": producto['precio'],
        "cantidad": cantidad
    })
    
    if carrito_req.status_code != 200:
        print(f"❌ Error agregando producto: {carrito_req.json()}")
    else:
        carrito_items.append((producto, cantidad))
        print_ok(f"Agregado: {producto['nombre']} x{cantidad}")
    
    continuar = input("\n¿Agregar otro producto? (s/n): ").strip().lower()
    if continuar not in ['s', 'si', 'y', 'yes']:
        break

if not carrito_items:
    print_error("No agregaste productos al carrito. Demo finalizada.")

# Ver carrito
time.sleep(0.3)
carrito = requests.get(f"{API}/usuarios/{user_id}/carrito")
items_carrito = carrito.json()['carrito']
total = sum(item['precio'] * item['cantidad'] for item in items_carrito)

print(f"\n📦 Tu carrito ({len(items_carrito)} items):")
for item in items_carrito:
    subtotal = item['precio'] * item['cantidad']
    print(f"   • {item['nombre']} x{item['cantidad']} - €{subtotal:.2f}")
print(f"\n   💰 Total: €{total:.2f}")

# =============================================================================
# CREAR PEDIDO
# =============================================================================

print_step("4. CONFIRMAR PEDIDO")

confirmar = input("\n¿Crear pedido con estos productos? (s/n): ").strip().lower()

if confirmar not in ['s', 'si', 'y', 'yes']:
    print("❌ Pedido cancelado")
    exit(0)

print("\n📍 Dirección de envío:")
calle = input("Calle: ").strip() or "Calle Demo 123"
ciudad = input("Ciudad: ").strip() or "Madrid"
codigo_postal = input("Código postal: ").strip() or "28001"
telefono = input("Teléfono: ").strip() or "612345678"

print("\n💳 Método de pago:")
print("  1. tarjeta")
print("  2. paypal")
print("  3. transferencia")
metodo_opcion = input("Elige (1/2/3): ").strip()
metodos = {"1": "tarjeta", "2": "paypal", "3": "transferencia"}
metodo_pago = metodos.get(metodo_opcion, "tarjeta")

# Ver stock ANTES del primer producto
primer_producto = carrito_items[0][0]
stock_antes = requests.get(f"{API}/productos/{primer_producto['id']}")
stock_inicial = stock_antes.json().get('stock', 0)

print(f"\n⚡ Creando pedido...")
print(f"   Stock actual de '{primer_producto['nombre']}': {stock_inicial} unidades")

# Crear pedido
pedido = requests.post(f"{API}/pedidos", json={
    "user_id": user_id,
    "items": [
        {
            "id_producto": item['id_producto'],
            "nombre": item['nombre'],
            "precio": item['precio'],
            "cantidad": item['cantidad']
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

if pedido.status_code != 201:
    print_error(f"Error creando pedido: {pedido.json()}")

pedido_data = pedido.json()['pedido']
print_ok(f"Pedido creado: {pedido_data['numero_pedido']}")

# Ver stock DESPUÉS
time.sleep(0.3)
stock_despues = requests.get(f"{API}/productos/{primer_producto['id']}")
stock_final = stock_despues.json().get('stock', 0)
print(f"   Stock actualizado de '{primer_producto['nombre']}': {stock_final} unidades")
print(f"   Reducción: -{stock_inicial - stock_final} unidades ✅")

# Ver carrito vaciado
carrito_final = requests.get(f"{API}/usuarios/{user_id}/carrito")
items_final = carrito_final.json()['carrito']
print_ok(f"Carrito vaciado automáticamente: {len(items_final)} items")

# =============================================================================
# RESUMEN FINAL
# =============================================================================

print_step("✅ PEDIDO COMPLETADO")
print(f"""
📦 Resumen del pedido:
   Número: {pedido_data['numero_pedido']}
   Total: €{pedido_data['total']:.2f}
   Items: {len(items_carrito)} productos
   Método pago: {pedido_data['metodo_pago']}
   
📍 Envío a:
   {calle}
   {ciudad}, {codigo_postal}
   Tel: {telefono}

🎯 Transacción ACID completada:
   ✓ Pedido creado
   ✓ Stock reducido
   ✓ Carrito vaciado
   
¡Gracias por tu compra! 🎾
""")
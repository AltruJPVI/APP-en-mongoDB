# Tennis Social Store - MongoDB + Flask

REST API for an online tennis store with social features (posts, comments, events).

## 🎯 Key Features

### **Functionalities**
- 🛒 **E-commerce:** Products, cart, orders with ACID transactions
- 💬 **Social:** Posts, comments, like system
- 👥 **Users:** Registration, login, profiles (user, company, admin)
- 🔒 **Permissions:** Role-based system with verification on each endpoint

### **Technologies**
- **Backend:** Flask + Python
- **Database:** MongoDB
- **Validation:** Pydantic
- **Testing:** Postman

---

## 🗄️ Why MongoDB?

### **1. Flexible Schema**
```python
# Products with or without sizes - same model
{
  "nombre": "Racket",
  "stock": 10  # Simple stock
}

{
  "nombre": "Shoes",
  "tallas": ["39", "40", "41"],
  "stocks": [
    {"talla": "39", "stock": 5},
    {"talla": "40", "stock": 8}
  ]
}
```

### **2. Smart Denormalization**
```python
# Cache of recent comments (avoids joins)
{
  "nombre": "Wilson Racket",
  "comentarios": [  # Last 5 comments
    {"usuario": "Juan", "texto": "Excellent", "valoracion": 5}
  ],
  "total_comentarios": 127
}
```

### **3. Embedded Documents**
```python
# Order with all historical info
{
  "numero_pedido": "ORD-2025-000123",
  "items": [
    {"nombre": "Wilson Racket", "precio": 129.99, "cantidad": 2}
  ],
  "direccion_envio": {...}
}
```

### **4. Aggregation Pipeline**
```python
# Statistics in one query
db.products.aggregate([
  {"$group": {"_id": "$categoria", "total": {"$sum": 1}}},
  {"$sort": {"total": -1}}
])
```

---

## ⚛️ ACID Transactions in MongoDB

### **What are they?**
Guarantee that multiple operations execute **completely or not at all**:
- **A**tomicity: All or nothing
- **C**onsistency: Data always valid
- **I**solation: Transactions don't interfere with each other
- **D**urability: Changes are persistent

### **Example: Create order**
```python
with session.start_transaction():
    # 1. Create order
    db.orders.insert_one(order)
    
    # 2. Reduce stock
    db.products.update_one(
        {"_id": product_id},
        {"$inc": {"stock": -quantity}}
    )
    
    # 3. Empty cart
    db.users.update_one(
        {"_id": user_id},
        {"$set": {"carrito": []}}
    )
    
    # If ANY operation fails → automatic ROLLBACK
```

### **Requirement: Replica Set**
ACID transactions in MongoDB **require a Replica Set** (even if it's just 1 node).

#### **What is a Replica Set?**
Set of MongoDB servers that maintain the same data:
- **Primary:** Receives writes
- **Secondary:** Read-only replicas
- **Arbiter:** Only votes (no data)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Primary   │ ───> │  Secondary  │ ───> │  Secondary  │
│   (write)   │      │   (read)    │      │   (read)    │
└─────────────┘      └─────────────┘      └─────────────┘
```

#### **Advantages:**
- ✅ **High availability:** If primary fails, a new one is elected automatically
- ✅ **ACID transactions:** Only work with replica sets
- ✅ **Backups:** Real-time replicas
- ✅ **Read scalability:** Distribute queries



---

## 📊 MongoDB Features Implemented

| Feature | Implemented |
|---------|--------------|
| Pydantic Schema | ✅ |
| Operators ($set, $inc, $pull, $push) | ✅ |
| Aggregation Pipeline | ✅ |
| ACID Transactions | ✅ |
| Denormalization (comment cache) | ✅ |
| Pagination (skip/limit) | ✅ |
| Complex Filters | ✅ |
| Replica Set | ✅ |


---

## 🚀 Run
download the .zip and go to the that directory in the console
```bash

docker-compose up -d                  # run containers
docker-compose ps                #see if all containers runs
curl http://localhost:5000       #try this endoint to see if flask works
docker-compose logs -f api       #see the histoy of the app
python crear_datos.py     # BD
python demo_flow.py                   # Demo


#Run mongoDB
docker exec -it tienda_tenis mongosh -u admin -p 123456




install mongoDB for VS Code if you want to try to query 

```

---

## 📈 Test Data

- **Users:** 50,003 (1 admin, 2 companies, 50,000 users)
- **Posts:** 2,000
- **Comments:** 100,000
- **Cache:** Last 5 comments per entity

---

## 🔐 Roles and Permissions

| Action | user | company | admin |
|--------|------|---------|-------|
| View products | ✅ | ✅ | ✅ |
| Create product | ❌ | ✅ | ✅ |
| Create post | ✅ | ✅ | ✅ |
| Delete own post | ✅ | ✅ | ✅ |
| Delete any post | ❌ | ❌ | ✅ |
| View all orders | ❌ | ❌ | ✅ |

---

## 📝 Main Endpoints

```
--USUARIOS--

POST - registrar usuario
POST - logearse 

GET - ver perfil 
PUT - actualizar perfil

GET - ver carrito
DELETE - eliminar un producto del carrito
POST - añadir al carrito
DELETE - vaciar carrito

--COMENTARIOS--

POST - crear comentario 
GET - ver comentarios con caché de 5 coments
GET - ver 1 comentario concreto
PUT - actualizar comentario
DELETE - borrar comentario

POST - dar like
GET - ver respuestas a un comentario


--PEDIDOS--

POST - crear pedido
GET - ver pedidos de un usuario
GET - ver 1 pedido concreto
GET - ver todos los pedidos

--POSTS--

POST - crear post 
GET - ver posts
GET - ver 1 post concreto
PUT - actualizar post
DELETE - borrar post

POST - dar like post
GET - ver cuantos post hay de cada categoria

--PRODUCTOS--

POST - crear producto
GET - ver productos
GET - ver 1 producto concreto
PUT - actualizar producto
DELETE - borrar producto

Get - ver cuantos productos hay de cada marca
GET - ver cuantos productos hay de cada categoria

```

---

**Stack:** Python 3.x + Flask + MongoDB + Pydantic

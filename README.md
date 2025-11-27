# Tennis Social Store - MongoDB + Flask

REST API for an online tennis store with social features (posts, comments, events).

## Key Features

### **Functionalities**
- **E-commerce:** Products, cart, orders with ACID transactions
- **Social:** Posts, comments, like system
- **Users:** Registration, login, profiles (user, company, admin)
- **Permissions:** Role-based system with verification on each endpoint

### **Technologies**
- **Backend:** Flask + Python
- **Database:** MongoDB
- **Validation:** Pydantic
- **Testing:** Postman

---

## Why MongoDB?

### **1. Flexible Schema**
```python
# Products with or without sizes - same model
{
  "name": "Racket",
  "stock": 10  # Simple stock
}

{
  "name": "Shoes",
  "sizes": ["39", "40", "41"],
  "stocks": [
    {"size": "39", "stock": 5},
    {"size": "40", "stock": 8}
  ]
}
```

### **2. Smart Denormalization**
```python
# Cache of recent comments (avoids joins)
{
  "name": "Wilson Racket",
  "comments": [  # Last 5 comments
    {"users": "Juan", "text": "Excellent", "grade": 5}
  ],
  "total_comments": 127
}
```

### **3. Embedded Documents**
```python
# Order with all historical info
{
  "order_number": "ORD-2025-000123",
  "items": [
    {"name": "Wilson Racket", "price": 129.99, "amount": 2}
  ],
  "order_direction": {...}
}
```

### **4. Aggregation Pipeline**
```python
# Statistics in one query
db.products.aggregate([
  {"$group": {"_id": "$category", "total": {"$sum": 1}}},
  {"$sort": {"total": -1}}
])
```

---

## ACID Transactions in MongoDB

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
- **High availability:** If primary fails, a new one is elected automatically
- **ACID transactions:** Only work with replica sets
- **Backups:** Real-time replicas
- **Read scalability:** Distribute queries



---

## MongoDB Features Implemented

| Feature | 
|---------|
| Pydantic Schema |
| Operators ($set, $inc, $pull, $push) |
| Aggregation Pipeline | 
| ACID Transactions | 
| Denormalization (comment cache) | 
| Pagination (skip/limit) |
| Complex Filters | 
| Replica Set | 


---

##  Run
download the .zip and go to the that directory in the console
```bash

docker-compose up -d                  # run containers
docker-compose ps                #see if all containers runs
curl http://localhost:5000       #try this endoint to see if flask works
docker-compose logs -f api       #see the histoy of the app

docker-compose exec api python crear_datos.py #create and insert data

docker-compose exec mongo mongosh -u admin -p 123456 # Run mongo's terminal for querying
write exit to shut down mongo's terminal

Use the postam collection to try a basic pipeline to make posts, comments and orders 

aditionally you can install mongoDB for VS Code if you want to try to query instead of using mongosh 

```

---

## Test Data

- **Users:** 50,003 (1 admin, 2 companies, 50,000 users)
- **Posts:** 2,000
- **Comments:** 100,000
- **Cache:** Last 5 comments per entity

---

## Main Endpoints

```
--USERS--

POST - create user
POST - login 

GET - vee profile 
PUT - update profile

GET - see cart
DELETE - delete a product from cart
POST - add to cart
DELETE - clean cart

--COMMENTS--

POST - create comments
GET - see comemnts with a cachee of 5 comments
GET - see 1 concrete comment 
PUT - update  comment
DELETE - delete comment

POST - give like
GET - see comment responses


--Orders--

POST - create order
GET - see a user's order
GET - see 1 concrete order 
GET - see all orders

--POSTS--

POST - create post 
GET - see posts
GET - see 1 concrete post 
PUT - update post
DELETE - delete post

POST - give a like to a post
GET - see hoe many posts in each category

--PRODUCTS--

POST - create products
GET - see products
GET - see 1 concrete product
PUT - update product
DELETE - delete product

Get - see how many products in each brand
GET - see how many products in each category

```

---

**Stack:** Python 3.x + Flask + MongoDB + Pydantic

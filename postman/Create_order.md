# STEP BY STEP endpoints in Postman - Orders 
To create a body, in Postman after you write the URL endpoint, choose 'body'->'raw'->JSON and paste it there

---

## USER
### Create user
```
    POST http://localhost:5000/api/auth/register

    Body: { 
        "nombre": "name",
        "email": "name@email.com",
        "password": "1234"
    }

    additionally you can add:

    "clase": user by default but also admin or empresa
    "nivel": intermedio by default, you can also be principiante or avanzado
    "direcion": {
            "calle": "Calle Mayor 123",
            "ciudad": "Madrid",
            "codigo_postal": "28001",
            "telefono": "612345678"
        } //optional
```
### Login once you have a user
```
    POST http://localhost:5000/api/auth/login

    Body: {
        "email": "name@email.com",
        "password": "1234"
    }
```
---
## PRODUCTS
### See available products
```
    GET http://localhost:5000/api/productos?categoria=raquetas&genero=unisex
    
    Available filters:
    - categoria: raquetas, zapatillas, camisetas, etc.
    - genero: hombre, mujer, unisex
    - precio_min / precio_max: price range
    - marca: Wilson, Nike, Adidas, etc.
    - page: page number (default: 1)
    - limit: products per page (default: 20, max: 100)
```
### See product details
```
    GET http://localhost:5000/api/productos/product_id //copy the id you got in PRODUCTS response
```
#### Check the stock available for this product
---
## CART
### Add a product to your cart
```
    POST http://localhost:5000/api/usuarios/user_id/carrito //copy the id you got in USER response

    Body: {
        "id_producto": "", //copy the id you got in PRODUCTS response
        "nombre": "Raqueta Wilson",
        "precio": 120.50,
        "cantidad": 1,
    }

    additinonally you can use:

    "talla": "M"  // if the product have sizes

```
#### You can repeat this process with another product to add more items to your cart

### See your cart
```
    GET http://localhost:5000/api/usuarios/user_id/carrito //copy the id you got in USER response
```
#### Alternative: you can also see your complete user profile which includes the cart
```
    GET http://localhost:5000/api/usuarios/user_id //copy the id you got in USER response
```
---
## ORDERS
### Create an order
```
    POST http://localhost:5000/api/pedidos
    Body: {
        "user_id": "", //copy the id you got in USER response
        "items": [
            //copy here ALL items from your cart
            {
                "id_producto": "",
                "nombre": "Raqueta Wilson", 
                "precio": 120.50,
                "cantidad": 2,
            }
        ],
        "total": 241.00,

        "direccion_envio": { //copy your direction if you had it
            "calle": "Calle Mayor 123",
            "ciudad": "Madrid",
            "codigo_postal": "28001",
            "telefono": "612345678"
        },
        "metodo_pago": "tarjeta"
    }
    
    ACID transactions guarantee:
    1. Order is created
    2. Product stock is reduced
    3. User cart is emptied
    If any operation fails → ROLLBACK
```
### See your order
```
    GET http://localhost:5000/api/pedidos/usuario/user_id?page=1&limit=20 //copy the id you got in USER response

```
### Check your cart again
```
    GET http://localhost:5000/api/usuarios/user_id/carrito //copy the id you got in USER response
```
#### Your cart should now be empty after completing the order

### Verify the product stock has decreased
```
    GET http://localhost:5000/api/productos/product_id //copy the id you got in PRODUCTS response
```
#### Compare the current stock with the stock you saw before creating the order

---
## If you want to try more, go to app/routes and enter the .py file you want. There you will see all the documentation about more endpoints.
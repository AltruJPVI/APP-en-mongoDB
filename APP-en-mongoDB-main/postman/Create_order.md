# STEP BY STEP endpoints in Postman - Orders 
To create a body, in Postman after you write the URL endpoint, choose 'body'->'raw'->JSON and paste it there

---

## USER
### Create user
```
    POST http://localhost:5000/api/auth/register

    Body: { 
        "name": "John Doe",
        "email": "john.doe@email.com",
        "password": "1234"
    }

    additionally you can add:

    "role": user by default but also admin or company
    "level": intermediate by default, you can also be beginner or advanced
    "address": {
            "street": "Main Street 123",
            "city": "Madrid",
            "postal_code": "28001",
            "phone": "612345678"
        } //optional
```
### Login once you have a user
```
    POST http://localhost:5000/api/auth/login

    Body: {
        "email": "john.doe@email.com",
        "password": "1234"
    }
```
---
## PRODUCTS
### See available products
```
    GET http://localhost:5000/api/products?category=rackets&gender=unisex
    
    Available filters:
    - category: rackets, shoes, shirts, etc.
    - gender: male, female, unisex
    - price_min / price_max: price range
    - brand: Wilson, Nike, Adidas, etc.
    - page: page number (default: 1)
    - limit: products per page (default: 20, max: 100)
```
### See product details
```
    GET http://localhost:5000/api/products/product_id //copy the id you got in PRODUCTS response
```
#### Check the stock available for this product
---
## CART
### Add a product to your cart
```
    POST http://localhost:5000/api/users/user_id/cart //copy the id you got in USER response

    Body: {
        "product_id": "", //copy the id you got in PRODUCTS response
        "name": "Wilson Racket",
        "price": 120.50,
        "quantity": 1,
    }

    additionally you can use:

    "size": "M"  // if the product has sizes
```
#### You can repeat this process with another product to add more items to your cart

### See your cart
```
    GET http://localhost:5000/api/users/user_id/cart //copy the id you got in USER response
```
#### Alternative: you can also see your complete user profile which includes the cart
```
    GET http://localhost:5000/api/users/user_id //copy the id you got in USER response
```
---
## ORDERS
### Create an order
```
    POST http://localhost:5000/api/orders
    Body: {
        "user_id": "", //copy the id you got in USER response
        "items": [
            //copy here ALL items from your cart
            {
                "product_id": "",
                "name": "Wilson Racket", 
                "price": 120.50,
                "quantity": 2,
            }
        ],
        "total": 241.00,

        "shipping_address": { //copy your address if you had it
            "street": "Main Street 123",
            "city": "Madrid",
            "postal_code": "28001",
            "phone": "612345678"
        },
        "payment_method": "card"
    }
    
    ACID transactions guarantee:
    1. Order is created
    2. Product stock is reduced
    3. User cart is emptied
    If any operation fails → ROLLBACK
```
### See your order
```
GET http://localhost:5000/api/orders/order_id //copy the id you got in the ORDER response
```
### Check your cart again
```
    GET http://localhost:5000/api/users/user_id/cart //copy the id you got in USER response
```
#### Your cart should now be empty after completing the order

### Verify the product stock has decreased
```
    GET http://localhost:5000/api/products/product_id //copy the id you got in PRODUCTS response
```
#### Compare the current stock with the stock you saw before creating the order

---
## If you want to try more, go to app/routes and enter the .py file you want. There you will see all the documentation about more endpoints.
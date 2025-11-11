# STEP BY STEP endpoints in Postman

To create a body, in Postman after you write the URL endopint, choose 'body'->'raw'->JSON and paste it there
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
# POSTS
### Create a post

```
    POST  http://localhost:5000/api/posts

    Body: {
        "autor_id": "",//here copy the id you got in USER response
        "autor_nombre": "name",
        "tipo": "discusion",  // "discusion" or "articulo"
        "categoria": "tecnica",
        "titulo": "¿Cómo mejorar el revés?",
        "contenido": "Llevo tiempo practicando pero soy muy malo. ¿Qué hago?"
    }

    additionaly you can add:

    "resumen": "",  // a brief summary

you can choose one of these for "categoria": tecnica,entrenamientos, partidos, clubes, general, consejos, nutricion, noticias, torneos, equipamiento
```

### Uptate your post

```
    PUT  http://localhost:5000/api/post_id //copy the id you got in POST response

    Body: {
        "usuario_id": "",  //copy the id you got in USER response
        "titulo": "Ya he mejorado mi revés",
        "categoria":"partidos",
        "contenido": "Ya he mejorado mucho. Mañana voy al tenis de 8 a 10 ¿Quién se viene?"
    }
```
### See your updated post

```
    GET  http://localhost:5000/api/post_id //copy the id you got in POST response

```
### Give youself a like 

```
    POST  http://localhost:5000/api/posts/post_id/like //copy the id you got in POST response

    Body: {"usuario_id": "" } //copy the id you got in USER response

```
#### If you visit again your post, you will see that 'likes' equal 1. Also visits grow each time you interact with the post
---
# COMMENTS

### Create a comment on your post
```
    POST http://localhost:5000/api/comentarios
    Body: {
        "entidad_tipo": "post",  // "producto","post"
        "entidad_id": "",//copy the id you got in POST response
        "usuario_id": "",//copy the id you got in USER response
        "usuario_nombre": "name",
        "texto": "As no one answers, I myself, will play the tenis match with my self"
    }

    additionaly you can add:

    "valoracion": 5,  // only for products
    "respuesta_a": "..."  // If you are answering another comment write its id
```
#### You can now see the post again and see how it changed

### See the comment you made
```
GET /api/comentarios/comment_id //copy the id you got in COMMENT response
```

### See all comments in your entity (post or product) by filters
```
GET  http://localhost:5000/api/comentarios?entidad_tipo=post&entidad_id=xxx
//copy the id you got in POST response

    Optional filters:

    - respuesta_a: null if anwers to comments
    - page: page number(default: 1)
    - limit: by page (default: 20, max: 100)
    - sort: date, likes (default: date)
    - order: asc, desc (default: desc - new fist)
```

## If you want to try more, go to app/routes and enter the .py file you want. There you will see all the documentation about more endpoints.

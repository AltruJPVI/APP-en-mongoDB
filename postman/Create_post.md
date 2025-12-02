# STEP BY STEP endpoints in Postman - POSTS

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
# POSTS
### Create a post
```
    POST  http://localhost:5000/api/posts

    Body: {
        "author_id": "",//here copy the id you got in USER response
        "author_name": "John Doe",
        "type": "discussion",  // "discussion" or "article"
        "category": "technical",
        "title": "How to improve backhand?",
        "content": "I've been practicing for a while but I'm still struggling. What should I do?"
    }

    additionally you can add:

    "summary": "",  // a brief summary

you can choose one of these for "category": technical, training, matches, clubs, general, tips, nutrition, news, tournaments, equipment
```

### Update your post
```
    PUT  http://localhost:5000/api/posts/post_id //copy the id you got in POST response

    Body: {
        "user_id": "",  //copy the id you got in USER response
        "title": "I've improved my backhand",
        "category":"matches",
        "content": "I've improved a lot. Tomorrow I'm going to play tennis from 8 to 10. Who wants to join?"
    }
```
### See your updated post
```
    GET  http://localhost:5000/api/posts/post_id //copy the id you got in POST response
```
### Give yourself a like 
```
    POST  http://localhost:5000/api/posts/post_id/like //copy the id you got in POST response

    Body: {"user_id": "" } //copy the id you got in USER response
```
#### If you visit your post again, you will see that 'likes' equals 1. Also, views grow each time you interact with the post
---
# COMMENTS

### Create a comment on your post
```
    POST http://localhost:5000/api/comments
    Body: {
        "entity_type": "post",  // "product","post"
        "entity_id": "",//copy the id you got in POST response
        "user_id": "",//copy the id you got in USER response
        "user_name": "John Doe",
        "text": "As no one answers, I myself, will play the tennis match with myself"
    }

    additionally you can add:

    "rating": 5,  // only for products
    "reply_to": "..."  // If you are answering another comment write its id
```
#### You can now see the post again and see how it changed

### See the comment you made
```
GET /api/comments/comment_id //copy the id you got in COMMENT response
```


## If you want to try more, go to app/routes and enter the .py file you want. There you will see all the documentation about more endpoints.
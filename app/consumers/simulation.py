import requests
import random
import json



posts = [
    # Good posts (title, content, category)
    (
        "First Wilson racket - Tips for beginners?",
        "I just bought my first Wilson racket and I'm super excited to start playing! I'm a complete beginner and would love some advice. What should I focus on first? Any drills you recommend?",
        "equipment"
    ),
    (
        "My serve has improved after 3 months!",
        "I've been practicing my serve technique consistently for 3 months and I can finally see real progress. My accuracy has doubled! For anyone struggling, don't give up - consistency is key. Keep practicing!",
        "technique"
    ),
    (
        "Clay court shoes under 100€?",
        "I'm looking for good quality shoes for clay courts. My budget is around 100€. I've been playing on hard courts until now but my club has clay courts. Any recommendations? Comfort is important for me.",
        "equipment"
    ),
    (
        "How to prevent tennis elbow?",
        "I've been experiencing some discomfort in my elbow lately. Does anyone have tips to avoid tennis elbow injuries? Should I change my grip or technique? Any exercises that help? Thanks in advance!",
        "tips"
    ),
    (
        "Yesterday's Federer-Nadal match was incredible",
        "Let's talk about yesterday's epic Federer-Nadal match! That third set was absolutely insane. What did you think about Nadal's strategy in the final games? Amazing level from both players.",
        "matches"
    ),

    # Bad posts (title, content, category)
    (
        "If you can't serve, you're an idiot",
        "You're an idiot if you can't do a basic serve. It's the easiest thing in tennis. I don't understand how people mess this up. Just embarrassing honestly.",
        "technique"
    ),
    (
        "Cheap racket players are losers",
        "People who play with cheap rackets are losers. If you can't afford a decent racket, maybe tennis isn't for you. Go play ping pong or something. This sport requires investment.",
        "equipment"
    ),
    (
        "User2345 is completely clueless",
        "Shut up user2345, you're stupid, you have no idea about tennis. Stop giving advice when you clearly don't know what you're talking about. You're making everyone dumber.",
        "general"
    ),
    (
        "Beginners ruin this sport",
        "All beginners suck at this sport. If you're a beginner at my club you better leave before embarrassing yourself. We don't have time to teach basic skills. Learn elsewhere or quit.",
        "tips"
    ),
    (
        "This community is full of incompetents",
        "What a disgusting community, full of incompetents. Anyone here who actually knows about tennis? Or is everyone just pretending? The advice I see here is pathetic. Total waste of time.",
        "general"
    ),
]

user={
    "name": "Juan Velado",
    "email": "juan20@email.com",
    "password": "12345678",
    "level": "intermediate"
}
url_register = "http://localhost:5000/api/auth/register" 
url_post= "http://localhost:5000/api/posts" 

create_user= requests.post(url_register, json=user).json()
print(f"user created:\n\n -{create_user['user']['name']}\n -{create_user['user']['email']}\n -{create_user['user']['level']}")

print('\nstarts posting...\n')

for i in range(len(posts)-1,-1,-1):

    n=random.randint(0,i)
    body= {
        "author_id": create_user['user']['id'],
        "author_name": create_user['user']['name'],
        "type": "discussion",
        "category": posts[n][2],
        "title": posts[n][0],
        "content": posts[n][1]
    }
    print(f"title: {posts[n][0]}\n\n{posts[n][1]}")
    create_post= requests.post(url_post, json=body).json()
    posts.pop(n)
    input('\npress enter to continue posting\n')
    print('------------------------------------------------')




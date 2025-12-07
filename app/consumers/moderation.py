from detoxify import Detoxify
from confluent_kafka import Consumer, KafkaError, KafkaException
from datetime import datetime,timezone
from bson import ObjectId
import json
import time
from app.extensions import init_db

# Modelo IA
print("Loading Detoxify model...")
model = Detoxify('original-small')
print("Model loaded successfully!")

# MongoDB
print("Connecting to MongoDB...")
db, mongo_client = init_db()

# Configuración del consumidor Kafka
conf = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'moderation-consumer',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True
}

print("Creating Kafka consumer...")
consumer = Consumer(conf)
consumer.subscribe(['posts-created'])
print(" Subscribed to topic: posts-created")
print("\n Moderation Consumer Started - Waiting for messages...")

try:
    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                print(f' Topic not available yet, waiting...')
                time.sleep(5)
                continue
            else:
                print(f' Kafka error: {msg.error()}')
                raise KafkaException(msg.error())
        else:
            # Procesar mensaje
            event = json.loads(msg.value().decode('utf-8'))
            print(f"post received, title: {event['title']}")

            results = model.predict(event['content'])
            warnings = {}

            # results es un diccionario, no una lista de tuplas
            for category, rate in results.items():
                if rate > 0.6:
                    warnings[category] = float(rate)

            if warnings:
                print(f" Toxic post detected: {list(warnings.keys())}\n")
                db.posts.update_one(
                    {'_id': ObjectId(event['post_id'])},
                    {'$set': {
                        'status': 'flagged',
                        'visible': False,
                        'causes': warnings,
                        'moderation_date': datetime.now(timezone.utc)}
                    }
                )
            else:
                print(f" Post approved\n")
                db.posts.update_one(
                    {'_id': ObjectId(event['post_id'])},
                    {'$set': {
                        'status': 'approved',
                        'visible': True,
                        'moderation_date': datetime.now(timezone.utc)}
                    }
                )

except KeyboardInterrupt:
    print("\nShutting down consumer...")
    
finally:
    consumer.close()
    print("Consumer closed")
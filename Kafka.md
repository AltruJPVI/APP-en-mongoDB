# **Real-Time Post Moderation Pipeline using Kafka + MongoDB**  
## **Complete Documentation**


## **1. Use Case Overview**

Our application is a **tennis shop and community platform**, where users can publish posts such as tips, match comments, technique questions, or general discussions.  
To make the platform safe and prevent toxic behavior, we implemented a **real-time post moderation system** using:

- **Apache Kafka (KRaft mode)** for event streaming  
- **MongoDB** as the NoSQL database storing posts  
- **Detoxify (AI model)** as the moderation engine  
- **Python producer/consumer** for publishing and processing events

### **Real-Time Scenario Used**
**Post moderation pipeline**:

1. A user creates a post.  
2. The API inserts the post into MongoDB.  
3. The API publishes an event to Kafka (`posts-created`).  
4. A Kafka Consumer listens to this topic.  
5. The consumer applies AI moderation using Detoxify.  
6. It updates the post in MongoDB with:
   - status: `approved` or `flagged`
   - visibility
   - moderation date
   - detected toxicity categories

This creates a **streaming moderation workflow** that operates automatically and continuously.

---

## **2. Why MongoDB Is a Good Fit**

MongoDB is an ideal NoSQL database for this streaming system because:

### **Flexible Schema**
Posts evolve over time (status, moderation info, comments, likes, metadata).  
MongoDB allows adding fields dynamically, which fits perfectly with the Kafka consumer updating documents after moderation.

### **Document-Oriented Format**
Each post is a JSON-like document → easy integration with Python and Kafka JSON messages.

### **Fast Writes**
Kafka consumers may update documents frequently.  
MongoDB handles high write throughput with ease.

### **Replica Set Compatibility**
Your Docker Compose config includes a **MongoDB replica set**, enabling:
- safe writes
- eventual scalability
- compatibility with production environments

---

## **3. System Architecture**

Below is the streaming architecture used in this project.

---

### **3.1 Components**

### **Flask API (Producer)**
- Accepts new posts via REST (`POST /api/posts`)
- Inserts the post into MongoDB
- Publishes a Kafka event to the topic `posts-created`
- Event contains:
  ```json
  {
    "post_id": "...",
    "title": "...",
    "content": "...",
    "author_id": "...",
    "category": "...",
    "type": "...",
    "timestamp": "..."
  }
  ```

(Implemented in `posts.py`)

---

### **Kafka Broker (KRaft Mode)**

Configured inside Docker Compose:

- No Zookeeper (modern Kafka architecture)
- Single-node cluster
- Listeners at `kafka:9092`
- Persisted in volume `kafka_data`

---

### **Topic: `posts-created`**

- Created manually by the development team  
- Used by API → produces new events  
- Used by Moderation Consumer → subscribes and processes events  
- Partition count: **1** (recommended for a single consumer)

---

### **Moderation Consumer**

Located at: `/app/app/consumers/moderation.py`

Responsibilities:

1. Subscribes to `posts-created`
2. Receives post creation events
3. Uses **Detoxify** to classify toxicity
4. Updates MongoDB:
   - Approves or flags the post
   - Adds causes (toxicity categories above threshold)
   - Hides toxic posts (`visible=False`)
   - Sets moderation timestamp

Example detection thresholds in code:

```python
for category, rate in results.items():
    if rate > 0.6:
        warnings[category] = float(rate)
```

If warnings exist → post is toxic.  
(Implemented in `moderation.py`)

---

### **Simulation Producer (Testing Script)**

The script `simulation.py`:

- Creates a random user
- Sends a sequence of **good** and **toxic** posts to the API
- Pauses between posts to simulate real users
- Triggers the full Kafka → Consumer → MongoDB pipeline

This is essential to demonstrate the real-time ingestion flow.  
(Located in `simulation.py`)

---

## **4. Architecture Diagram (ASCII)**

```
                       ┌────────────────────────────┐
                       │         User Client        │
                       └──────────────┬─────────────┘
                                      │  HTTP POST /api/posts
                                      ▼
                          ┌────────────────────────┐
                          │       Flask API        │
                          │      (Producer)        │
                          └───────────┬────────────┘
                                      │ Insert post in MongoDB
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │         MongoDB          │
                         │       (Posts DB)         │
                         └──────────────────────────┘
                                      │
                                      │ Produce event with post info
                                      ▼
                         ┌────────────────────────────┐
                         │          Kafka             │
                         │      Topic: posts-created  │
                         └────────────────────────────┘
                                      │
                                      │ Consumer polls events
                                      ▼
                    ┌──────────────────────────────────────────┐
                    │      Moderation Consumer (Detoxify)      │
                    └───────────────────┬──────────────────────┘
                                        │ Updates moderation status
                                        ▼
                         ┌────────────────────────────┐
                         │         MongoDB            │
                         │   (post updated/flagged)   │
                         └────────────────────────────┘
```

---

## **5. Setup and Execution Guide**

## **5.1 Start Docker Services**

```bash
docker compose up -d
```

This launches:

- MongoDB replica set  
- Kafka in KRaft mode  
- Flask API  
- Moderation consumer  

---

## **5.2 Create Kafka Topic Manually**

Required because auto-topic creation is disabled:

```bash
docker exec -it tennis_kafka kafka-topics.sh \
  --create \
  --topic posts-created \
  --partitions 1 \
  --replication-factor 1 \
  --bootstrap-server kafka:9092
```

Verify topic:

```bash
docker exec -it tennis_kafka kafka-topics.sh --list --bootstrap-server kafka:9092
```

---

## **5.3 Running the Producer Simulation**

```bash
docker compose exec api python -m app.consumers.simulation
```

This will:

- Register a demo user
- Send sequential posts (normal + toxic)
- Trigger the moderation pipeline


see what is happening in the background:
```bash
 docker compose logs moderator -f
```
---

## **5.4 Verifying MongoDB Results**

```bash
docker compose exec mongo mongosh -u admin -p 123456

use tennis_shop
db.posts.find({author_name:'Juan Velado'}).limit(5)
```

You will see fields added by moderation:

```json
{
  "status": "flagged",
  "visible": false,
  "causes": {
    "insult": 0.87
  },
  "moderation_date": "2025-01-01T12:00:00Z"
}
```

---

# **6. Code Explanation**

---

## **6.1 Producer Logic (`posts.py`)**

Steps performed when a user creates a post:

1. Validate request with Pydantic  
2. Insert the post into MongoDB  
3. Build an event containing essential post data  
4. Serialize event to JSON  
5. Publish to Kafka topic `posts-created`  
6. Flush producer buffer  

Example core snippet:

```python
producer.produce(
    'posts-created',
    value=json.dumps(event).encode('utf-8'),
    callback=delivery_report
)
producer.flush()
```

---

## **6.2 Consumer Logic (`moderation.py`)**

1. Subscribe to `posts-created`  
2. Poll events continuously  
3. Run Detoxify model on post content  
4. Build toxicity warnings if score > 0.6  
5. Update the corresponding MongoDB document  

Eg:

```python
db.posts.update_one(
    {'_id': ObjectId(event['post_id'])},
    {'$set': {
        'status': 'flagged',
        'visible': False,
        'causes': warnings,
        'moderation_date': datetime.now(timezone.utc)
    }}
)
```

This turns an unmoderated post into either:

- **approved**, visible  
- **flagged**, hidden  

---

## **7. Querying the Data**

### **Query 1: Get all flagged posts**
```js
db.posts.find({ status: "flagged" })
```

### **Query 2: Get visible posts ordered by date**
```js
db.posts.find({ visible: true }).sort({ date: -1 })
```

---

# **8. Reflections**


### **Difficulties**
- Configuring Kafka in KRaft mode (no Zookeeper)
- Ensuring MongoDB replica set initialization inside Docker
- Managing async behavior of Kafka producer
- Ensuring the Detoxify model loads inside the consumer container

### **Strengths of Kafka + MongoDB**
- Kafka ensures reliable, decoupled communication between API and moderation service  
- MongoDB’s flexibility allows easy updates after moderation  
- Real-time moderation becomes independent from API speed  
- Horizontal scalability: more consumers → faster moderation  

### **Limitations**
- Single-node Kafka setup is not production-ready  
- Detoxify model loads slowly  
- Moderation consumer is not fault-tolerant without partitioning or consumer groups  

### **Performance**
- MongoDB handles frequent writes efficiently  
- Kafka provides high ingestion rates  
- Current consumer is single-threaded → manageable but not scalable for high loads  

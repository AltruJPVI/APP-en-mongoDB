# MongoDB – Documentation

## 1. Context and Motivation

### General Overview

MongoDB is a **NoSQL, document-oriented database**. Instead of using tables and rows (as in relational databases), it stores data in **BSON documents** (binary JSON). Documents live in collections (roughly analogous to tables) without a fixed schema, making it easy to evolve data models.

This design naturally represents flexible, hierarchical, semi-structured data such as product catalogs, user profiles, carts, and orders — all typical in an online store.

### What Problems Does It Solve Better Than SQL Databases?

MongoDB is inherently suited for systems requiring **horizontal scalability** and high **availability** (often prioritizing the 'A' in the CAP theorem).

* **Flexible Schema:** No predefined schema required. Each document can have different fields, enabling **rapid iteration** without heavy migrations. This supports **microservices** architectures where individual services evolve independently.
* **High Scalability (Sharding):** MongoDB supports **horizontal scaling**, distributing data across multiple servers (a technique known as **Data Partitioning** or **Sharding**) to handle massive datasets and high traffic.
* **Performance-Oriented:** Optimized for fast reads/writes, especially when using **embedded documents**. This enables common reads to fetch everything in one go, reducing **latency**.
* **Natural Data Modeling:** Related data can be **embedded** (e.g., product reviews inside the product document), enabling **atomic updates at the document level** and avoiding expensive **joins** (which are typical in relational databases).
* **Smooth Backend Integration:** Excellent drivers for popular backend languages like **Node.js, Python, Java**, often used in modern, distributed system stacks.

### Common Use Cases

- Content management systems (CMS, blogs, video platforms)
- Geolocation-based apps (maps, delivery, routing)
- E-commerce platforms and product catalogs
- Analytics and logging systems
- IoT data storage (sensor data, telemetry)
- Social networks (posts, profiles, feeds, comments)

### Why Is MongoDB Well-Suited for an Online Tennis Store with an Active Community?

An online tennis store with an active community requires a database that can handle **flexible data structures**, **user-generated content**, and **high traffic** with great **availability**.

1.  **Variable Products:** Tennis rackets, shoes, and apparel have widely differing specifications. The **flexible schema** allows the product catalog to evolve without costly database migrations.
2.  **Community Features:** Social elements (posts, profiles, feeds, comments) are natural fits for the document model. The system can tolerate **eventual consistency** for displaying likes or comments, which aligns with the **BASE** principle and ensures high **Availability**.
3.  **Geolocation:** MongoDB's native support for **geospatial queries** is perfect for coordinating local community events or finding stores within a specific radius.

---

## 2. Main Characteristics: Deep Dive into System Concepts

### Consistency, ACID Properties, and Transactions

The choice of MongoDB represents a **trade-off** between **ACID** properties (typical of SQL databases) and **BASE** properties, often leaning toward **Availability** and **Scalability**.

* **BASE Philosophy:** MongoDB prioritizes **Availability** and **Scalability**, aligning with the **BASE (Basically Available, Soft state, Eventually consistent)** model. This is ideal for high-traffic web applications where minor temporary inconsistencies are acceptable if it prevents downtime.
* **Atomic Operations:** While traditionally associated with BASE, the document model provides **ACID guarantees** for **single-document operations**. This is why **embedded schema design** is the most efficient pattern—it leverages document-level atomicity to ensure data integrity.
* **Multi-Document Transactions:** Modern versions (≥ 4.0) introduced support for **multi-document transactions**. This is crucial for scenarios requiring **strong consistency** across multiple records (like complex e-commerce order processing) and brings MongoDB closer to **ACID** guarantees where necessary.

### CAP & PACELC Trade-offs

MongoDB’s operational mode determines its position in the core distributed system theorems:

| Theorem | Focus | MongoDB Default/Common Use | Trade-Off Implication |
| :--- | :--- | :--- | :--- |
| **CAP** | Consistency vs. Availability in a **Partition (P)**. | Can operate as **CP** (Consistency-Partition Tolerance) in strong consistency mode. | During a network split, the system may **reject or delay requests** to ensure data correctness. |
| **PACELC** | **P**artition: **A**vailability vs **C**onsistency; **E**lse: **L**atency vs **C**onsistency. | Operates as **ELC** (Consistency-Latency) when healthy. | Prioritizes **Consistency** over low read/write **Latency** in the absence of partitions. |

### Performance and Scalability: Horizontal Scaling

MongoDB is designed for **Horizontal Scaling**—adding more machines (nodes) to the system, which is more flexible than **Vertical Scaling** (upgrading CPU/RAM).

* **Sharding (Data Partitioning):** Data is divided and distributed across shards, enabling the system to handle massive datasets and traffic **throughput** efficiently. This prevents a single machine from becoming a bottleneck.
* **Replication (Replica Sets):** Data is replicated across multiple nodes to provide **fault tolerance** and **high availability**. If one node fails, automatic failover redirects traffic, ensuring the system remains **operational and accessible**.
* **Configurable Caching (WiredTiger):** MongoDB utilizes the WiredTiger storage engine, which provides efficient, configurable memory usage. This is a form of **server-side caching** used to store frequently accessed data and reduce the load on the disk I/O.

### Document Model and Constraints

* **Flexibility:** The **Document Model** allows for nested fields and arrays, naturally fitting hierarchical structures and reducing the number of database round-trips needed for complex data reads.
* **Document Size Limitation (16 MB):** Each document has a hard limit of 16 MB. This forces **best practice** modeling: large files (like images/videos) should be stored in **Storage/Data Lakes** (e.g., S3, GCS) and referenced by the document, while only the most frequently accessed or recent data should be embedded.

---

## 3. Querying, Indexing, and Observability

### Querying and Indexing

MongoDB offers sophisticated features essential for modern application development:

* **Rich Queries & Aggregation:** Supports complex queries and the powerful **Aggregation Framework** for analytics and data transformations.
* **Full-Text Search & Geospatial:** Includes specialized indexes for **Full-text search** and **Geospatial queries**, enabling features like searching product descriptions or locating nearby users/stores efficiently.
* **Indexing:** Comprehensive indexing (single-field, compound, text, geospatial) is vital for optimizing query performance and reducing **latency**.



## How to query in MongoDB

```
// view databases
show dbs

// Use a database
use tienda_tenis

// view collections
show collections


==============
VIEW DOCUMENTS
==============

// see all documents
db.products.find()
db.products.find().pretty()

// view a concrete document
db.products.findOne()
db.products.findOne({ brand: "Wilson" })

// count documentos
db.products.countDocuments()
db.products.countDocuments({ brand: "Wilson" })


============
BASIC FILTERS
============

// extact field
db.products.find({ brand: "Wilson" })
db.products.find({ price: 199.99 })
db.users.findOne({ email: "ana@gmail.com" })

// Sort by price
db.products.find({ price: { $gt: 100 } })    // greater than
db.products.find({ price: { $lt: 100 } })    // lower than
db.products.find({ price: { $gte: 100 } })   // greater or equal
db.products.find({ price: { $lte: 100 } })   // lower or equal

// search for many
db.products.find({ brand: { $in: ["Wilson", "Head", "Babolat"] } })

//AND
db.products.find({ 
  brand: "Wilson",
  price: { $lt: 200 }
})

// OR
db.products.find({
  $or: [
    { brand: "Wilson" },
    { price: { $lt: 100 } }
  ]
})

// embbebed fields
db.products.find({ "specs.weight": "300g" })




===================
SHOW CERTAIND FIELDS
===================

//only these fields
db.products.find({},{ name: 1, price: 1})

//search for someone which name has Gonzalo in it
db.users.find({name:/Gonzalo/i}, {name:1,level:1,email:1})


=================
ORDENAR Y LIMITAR
=================


// ascendent or descendent order (1) or (-1)
db.products.find().sort({ price: 1 })
db.products.find().sort({ price: -1 })

// Limit
db.productS.find().limit(5)

// paging
db.products.find().skip(10).limit(5)

// combine
db.products.find({ brand: "Wilson" }).sort({ price: -1 }).limit(3)


========
AGREGATE
========

// count by category
db.products.aggregate([
  { $group: { _id: "$category", total: { $sum: 1 } } }
])

// average pice per brand
db.products.aggregate([
  { $group: { _id: "$brand", average_price: { $avg: "$price" } } }
])

=======
OTHERS
=======

// Regex (find for text appearance) case sensitive
db.products.find({ name: /wilson/i})

// last inserted
db.products.find().sort({ _id: -1 }).limit(1)

//find with unique fields
db.comments.find({"rating": { $exists: true }})
```

---


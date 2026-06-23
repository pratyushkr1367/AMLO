# **System Requirement Document (SRD): Autonomous Maintenance & Logistics Orchestrator (AMLO)**

## **1\. Problem Statement**

Modern manufacturing plants face costly unplanned downtime because industrial data lives in disconnected silos. Real-time IoT sensor streams are isolated from transactional enterprise systems (ERP/inventory), while technical repair procedures remain locked away in unindexed PDF manuals.

When a machine fails, human operators must manually diagnose the issue, search through hundreds of pages of documentation, check physical inventory for spare parts, and manually plot dispatch logistics for technicians or Automated Guided Vehicles (AGVs). This fragmented approach results in slow response times, prolonged equipment degradation, and operational inefficiencies.

## **2\. What to Build**

Engineer a **3-Tier Agentic Cyber-Physical System** that unifies real-time IoT ingestion, algorithmic routing, and autonomous AI reasoning to automate factory incident resolution.

\[IoT Sensor Stream\] ──\> \[Message Queue\] ──\> \[Backend Microservices & Custom DSA\]  
                                                                                                      │  
             ┌───────────────————————————— ┴─────────┐  
             ▼                                                          ▼                                               ▼  
\[PostgreSQL \+ pgvector\]                         \[MongoDB\]                                     \[Agentic Loop\]  
• System Metadata & Assets              • Raw Polymorphic IoT Logs              • Triage, Sourcing &  
• Document Vector Chunks                • Purchase Orders & Audit Trails          Scheduling Multi-Agents

### **Core Components & Engineering Requirements:**

* **Presentation Layer (Frontend):** A React/Next.js dashboard featuring a real-time plant floor grid map, live Overall Equipment Effectiveness (OEE) metrics, and a dynamic WebSocket-driven alert panel.  
* **Application Layer (Backend):** A Python (FastAPI) ecosystem utilizing **RabbitMQ** or **Kafka** to ingest high-velocity data. It must run an internal Agentic State Machine (via LangGraph) that manages three specialized agents (Triage, Sourcing, and Scheduling).  
* **Data & RAG Layer (Storage):** A polyglot persistence architecture. **PostgreSQL** handles structured relational assets; **pgvector** stores embedded machinery manuals for Retrieval-Augmented Generation (RAG); **MongoDB** stores unstructured, high-volume raw telemetry timelines and dynamic purchase orders.  
* **Data Structures & Algorithms (DSA) Core:** To demonstrate pure engineering depth, the backend must execute two custom, library-free algorithms:  
  1. A *Circular Queue / Sliding Window* to evaluate rolling data streams for machine anomalies in O(1) time.  
  2. A *Min-Heap-based Dijkstra’s or A^* Search Algorithm\* to calculate the optimal path for an AGV traversing the factory floor grid around obstacles.

## **3\. What Will Be Measured (Success Metrics)**

The project will be evaluated on strict architectural and operational benchmarks:

### **Technical Performance**

* **Data Ingestion Resiliency:** The messaging queue must maintain **0% data packet loss** during a burst simulation of 10,000 concurrent IoT sensor messages.  
* **Algorithmic Efficiency:** The custom A\* pathfinding algorithm must calculate optimal routes on a 50 x 50 factory floor grid map in **under 50 milliseconds**, utilizing the custom Min-Heap.  
* **Database Optimization:** RAG query responses using pgvector index matching must execute with an LLM retrieval latency of **under 500ms**.

### **Functional Success**

* **E2E Automation Accuracy:** The multi-agent system must autonomously transition from an IoT anomaly trigger to a fully generated Work Order containing accurate, RAG-extracted torque and repair specifications with **zero human intervention**.  
* **State Machine Determinism:** The system must predictably log financial objects (Purchase Orders) to MongoDB *only* if PostgreSQL queries confirm spare parts are out of stock, proving reliable multi-agent system coordination.


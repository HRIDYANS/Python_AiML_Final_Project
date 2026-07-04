PO - INVOICE verification

Initailly download invoice details from database and the text is extracted from each invoice documents. After that compare the invoice details fetched from the document with the informations availale in the Database. And prepare a excel comparision report. Then that report is used for RAG based chatobt

# 📊 PO Invoice Verification RAG Chatbot

An AI-powered chatbot for querying Purchase Order (PO) Invoice Verification reports using **Retrieval-Augmented Generation (RAG)** with **Ollama**, **FAISS**, and **Flask**.

Instead of manually searching thousands of Purchase Order verification records, users can ask questions in natural language, and the chatbot retrieves the relevant records before generating an accurate respons

 

---

# Features

- AI chatbot powered by Ollama
- Retrieval-Augmented Generation (RAG)
- Semantic search using FAISS
- Natural language question answering
- Modern web interface
- Flask REST backend
- Works completely offline
- No cloud APIs required

---

# Tech Stack

| Component | Technology |
|------------|------------|
| AI Model | llama3.1 |
| Embedding Model | nomic-embed-text |
| Vector Database | FAISS |
| Backend | Flask |
| Frontend | HTML + CSS + JavaScript |
| Language | Python |

---

# Project Structure

```
po-rag-chatbot/
│
├── app.py                 # Flask application
├── chatbot_engine.py      # Chatbot pipeline
├── embedder.py            # Ollama embeddings
├── faiss_index.py         # FAISS vector database
├── data.json              # PO Invoice Verification data
│
├── templates/
│      index.html
│
├── requirements.txt
└── README.md
```

---

# Architecture

```
                    User Question
                          │
                          ▼
                 Flask Backend (/chat)
                          │
                          ▼
               Intent Classification
                          │
                          ▼
          Exact PO Search (if PO number found)
                          │
                ┌─────────┴─────────┐
                │                   │
                ▼                   ▼
         Exact Match          Semantic Search
                              (FAISS)
                │                   │
                └─────────┬─────────┘
                          ▼
                Retrieved Context
                          │
                          ▼
               Llama3.1 (Ollama)
                          │
                          ▼
                  Generated Answer
                          │
                          ▼
                      Web UI
```


---

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Install Ollama

Download from

https://ollama.com/download

---

## 3. Pull required models

```bash
ollama pull llama3.1

ollama pull nomic-embed-text
```

Verify installed models

```bash
ollama list
```

Example

```
llama3.1

nomic-embed-text
```

---

## 4. Start Ollama

```bash
ollama serve
```

---

## 5. Run the Flask application

python app.py

Output

```
Building FAISS index...

FAISS index ready with 52 records

Running on

http://127.0.0.1:5000
```

---

Open

```
http://localhost:5000
```

---

Developed as an offline AI-powered Purchase Order Invoice Verification Chatbot using Retrieval-Augmented Generation (RAG), FAISS, Flask, and Ollama.

```

### This project demonstrates how traditional document verification can be enhanced using Local Large Language Models and Vector Search to provide fast, intelligent, and interactive querying without relying on cloud services.
# 🧠 RAG Embedding API

This FastAPI service exposes a `/embed` endpoint that returns sentence embeddings using `sentence-transformers`.

---

## 🔧 How to Run

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the API server
uvicorn embed_api:app --host 0.0.0.0 --port 8001
```

---

## 📤 Example Request

POST to:

```
http://localhost:8001/embed
```

with body:

```json
{
  "text": ["This is a test.", "Another sentence."]
}
```

---

## 📦 Required Dependencies

Install these inside your venv:

```bash
pip install fastapi "uvicorn[standard]" torch sentence-transformers
```

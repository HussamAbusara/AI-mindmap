<div align="center">

# 🔬 AI Research Assistant
### مساعد البحث الذكي

**An Arabic-first AI-powered research assistant with RAG, real-time chat, and interactive mind map generation**

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Streamlit-FF4B4B?style=for-the-badge)](https://ai-research-app.streamlit.app)
[![Backend](https://img.shields.io/badge/⚡_Backend-HuggingFace-FFD21E?style=for-the-badge)](https://hussamfaisal-ai-research-backend.hf.space)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br/>

![Demo Screenshot](docs/demo.png)

</div>

---

## ✨ Features | المميزات

| Feature | Description |
|---------|-------------|
| 💬 **Smart Chat** | Arabic-first conversational AI powered by Qwen 2.5 7B via Ollama |
| 📄 **RAG Pipeline** | Upload PDF/DOCX → automatic indexing → context-aware answers |
| 🗺️ **Mind Maps** | AI summarizes any text into interactive, exportable mind maps |
| 🌙 **Light/Dark Theme** | Full theme support with RTL Arabic layout |
| 💾 **Export PNG** | Save mind maps as high-resolution PNG images |
| ⚡ **Local Extraction** | PDF/DOCX text extraction happens client-side — no data sent unnecessarily |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│            Streamlit (Python)                    │
│   Chat UI │ Mind Map Viewer │ File Upload        │
└──────────────────┬──────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────┐
│                  Backend                         │
│           FastAPI + Uvicorn                      │
│                                                  │
│  ┌─────────────┐  ┌──────────────┐              │
│  │   Ollama    │  │  ChromaDB    │              │
│  │ Qwen2.5 7B  │  │  Vector DB   │              │
│  └─────────────┘  └──────────────┘              │
│                                                  │
│  ┌──────────────────────────────┐               │
│  │   LangChain RAG Pipeline     │               │
│  │  HuggingFace Embeddings      │               │
│  └──────────────────────────────┘               │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai) installed locally
- 8GB+ RAM recommended

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/HUSSAMFaisal/ai-research-assistant.git
cd ai-research-assistant/backend

# Install dependencies
pip install -r requirements.txt

# Pull the AI model
ollama pull qwen2.5:7b

# Set environment variables
cp .env.example .env
# Edit .env with your settings

# Run the backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
pip install -r requirements.txt

# Set the backend URL
export API_BASE_URL=http://localhost:8000/api

# Run the app
streamlit run app.py
```

---

## 📁 Project Structure

```
ai-research-assistant/
│
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Environment configuration
│   │   │   ├── rag.py          # RAG pipeline (LangChain + Ollama)
│   │   │   └── vector_store.py # ChromaDB integration
│   │   └── routers/
│   │       ├── query.py        # /query, /chat, /mindmap endpoints
│   │       └── upload.py       # Document upload & indexing
│   ├── main.py                 # FastAPI app entry point
│   └── requirements.txt
│
├── frontend/                   # Streamlit frontend
│   ├── app.py                  # Main UI (chat + mind maps)
│   └── requirements.txt
│
└── docs/                       # Screenshots & documentation
    └── demo.png
```

---

## 🔧 Environment Variables

Create a `.env` file in the `backend/` directory:

```env
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
CHROMA_DB_PATH=./chroma_db
UPLOAD_FOLDER=./data
```

For the frontend, set:
```env
API_BASE_URL=https://your-backend-url/api
```

---

## 🧠 How the RAG Pipeline Works

```
User uploads PDF/DOCX
        ↓
Text extraction (PyMuPDF / python-docx)
        ↓
Chunking (RecursiveCharacterTextSplitter)
chunk_size=800, overlap=150
        ↓
Embedding (paraphrase-multilingual-MiniLM-L12-v2)
        ↓
Storage in ChromaDB (persistent)
        ↓
Query → MMR retrieval (k=6) → LLM → Arabic answer
```

---

## 🗺️ Mind Map Generation

```
User pastes text / uploads file
        ↓
Local text extraction (no server needed)
        ↓
LLM generates structured outline:
  Title
  ## Branch 1
  - Detail
  ## Branch 2
  - Detail
        ↓
D3.js renders interactive radial tree
        ↓
Export as PNG (2x resolution)
```

---

## 📊 Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — REST API framework
- [LangChain](https://langchain.com/) — RAG orchestration
- [Ollama](https://ollama.ai/) — Local LLM inference
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [HuggingFace](https://huggingface.co/) — Multilingual embeddings

**Frontend**
- [Streamlit](https://streamlit.io/) — Web UI framework
- [D3.js](https://d3js.org/) — Interactive mind map visualization
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF text extraction

---

## 🌐 Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Backend | HuggingFace Spaces | [hussamfaisal-ai-research-backend.hf.space](https://hussamfaisal-ai-research-backend.hf.space) |
| Frontend | Streamlit Cloud | [ai-research-app.streamlit.app](https://ai-research-app.streamlit.app) |

---

## 📸 Screenshots

<div align="center">

### Chat Mode | وضع الدردشة
![Chat](docs/chat.png)

### Mind Map Mode | وضع الخريطة الذهنية
![Mindmap](docs/mindmap.png)

</div>

---

## 👤 Author

**Hussam Faisal**

[![GitHub](https://img.shields.io/badge/GitHub-HUSSAMFaisal-181717?style=flat&logo=github)](https://github.com/HUSSAMFaisal)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/hussamfaisal)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

> **Note:** The core AI logic and proprietary configurations are not included in this public repository.

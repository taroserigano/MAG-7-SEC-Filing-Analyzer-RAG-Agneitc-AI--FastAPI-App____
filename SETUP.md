# 📦 Setup Guide - Portable App V2

## 🎯 Quick 5-Minute Setup

### 1. Extract Package
```bash
# If you received a ZIP file
unzip portable-app-v2-light.zip
cd portable-app-v2
```

> **💡 Note**: The light version excludes SEC cache files to keep the ZIP small (105KB vs 20MB).
> You'll fetch filings fresh on first use (see step 6 below).

### 2. Configure Environment Variables

**Backend Configuration:**
```bash
cd backend
cp .env.example .env
nano .env  # or use any text editor
```

**Required Variables:**
```bash
OPENAI_API_KEY=sk-...                    # Your OpenAI API key
PINECONE_API_KEY=pcsk_...                # Your Pinecone API key
PINECONE_INDEX_NAME=mag7-sec-filings     # Your index name
PINECONE_ENVIRONMENT=us-east-1           # Your Pinecone environment
```

**Optional Variables:**
```bash
ANTHROPIC_API_KEY=sk-ant-...             # For Claude support
OLLAMA_BASE_URL=http://localhost:11434   # For local LLMs
```

### 3. Install Backend Dependencies

```bash
# From backend directory
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
# From frontend directory
cd ../frontend
npm install
```

### 5. Launch Application

```bash
# From portable-app-v2 root
cd ..
bash start-all.sh
```

**Access your app:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 6. Fetch SEC Filings (First Time Setup)

Since the light version doesn't include cached SEC filings, you'll need to fetch them:

```bash
# Option A: Via UI (Recommended)
# 1. Open http://localhost:5173
# 2. Select a ticker (e.g., AAPL)
# 3. Click "Fetch SEC Filings" button
# 4. Wait 10-15 seconds for download
# 5. Repeat for other tickers you want

# Option B: Via API (Bulk fetch)
curl -X POST "http://localhost:8000/sec/fetch?ticker=AAPL"
curl -X POST "http://localhost:8000/sec/fetch?ticker=MSFT"
curl -X POST "http://localhost:8000/sec/fetch?ticker=GOOGL"
# ... etc for AMZN, META, NVDA, TSLA
```

**What gets cached:**
- Latest 10-K and 10-Q filings
- Stored in `backend/sec_cache/`
- Persists across restarts
- Reduces future query time from 15s → 20ms (485x faster!)

---

## 📦 Full Version vs Light Version

**portable-app-v2-light.zip (105KB)** ← Recommended for transfer
- ✅ All source code + optimizations
- ✅ Configuration files
- ✅ Documentation
- ❌ No SEC cache (fetch on first use)

**portable-app-v2.zip (20MB)**
- ✅ Everything above
- ✅ Pre-cached SEC filings for all 7 tickers
- ✅ Instant queries without initial fetch

Use **light** for easy transfer, **full** if you want pre-loaded data.

---

## 🐳 Docker Setup (Alternative)

If you have Docker installed:

```bash
cd portable-app-v2
docker-compose up -d
```

That's it! Same URLs apply.

---

## ✅ Verify Installation

### Check Backend Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "pinecone_connected": true,
  "openai_configured": true
}
```

### Check Frontend
Open http://localhost:5173 in your browser.

---

## 🛑 Stop Services

```bash
bash stop-all.sh
```

Or manually:
```bash
# Kill backend
kill $(cat /tmp/backend.pid)

# Kill frontend
kill $(cat /tmp/frontend.pid)
```

---

## 🔧 Troubleshooting

### "Port already in use"
```bash
# Backend (port 8000)
lsof -ti:8000 | xargs kill -9

# Frontend (port 5173)
lsof -ti:5173 | xargs kill -9
```

### "Module not found"
```bash
# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules
npm install
```

### "Pinecone connection failed"
- Verify your `PINECONE_API_KEY` in `.env`
- Check your Pinecone index exists
- Ensure `PINECONE_ENVIRONMENT` matches your index location

### "OpenAI API error"
- Verify your `OPENAI_API_KEY` is valid
- Check you have credits in your OpenAI account
- Try switching to Ollama for local testing

---

## 📂 Directory Structure After Setup

```
portable-app-v2/
├── backend/
│   ├── venv/               # ← Created after pip install
│   ├── .env                # ← Created from .env.example
│   └── ...
├── frontend/
│   ├── node_modules/       # ← Created after npm install
│   └── ...
└── ...
```

---

## 🚀 Next Steps

1. **Test the App**: Ask a question like "What are Apple's main risk factors?"
2. **Try Compare Mode**: Enable multi-select and compare AAPL vs MSFT
3. **Fetch SEC Data**: Click "Fetch SEC Filings" to get latest data
4. **Explore Settings**: Try different model providers and search modes

---

## 💡 Tips

- Use **Ollama** for free local testing (slower but no API costs)
- Enable **Retrieval Cache** for 485x faster repeated queries
- **Hybrid Search** works best for factual questions
- **Reranking** improves precision but adds latency

---

## 📞 Need Help?

Check the logs:
```bash
# Backend logs
tail -f /tmp/backend.log

# Frontend logs
tail -f /tmp/frontend.log
```

Check API documentation:
http://localhost:8000/docs

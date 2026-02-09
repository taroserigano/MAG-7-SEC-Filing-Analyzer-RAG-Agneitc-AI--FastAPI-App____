# 🚚 Transfer Guide - Moving to Another PC

## 📦 Choose Your ZIP File

**portable-app-v2-light.zip (105KB)** ← **Recommended**
- Fast download/transfer
- Fetch SEC filings on first use (15 sec per ticker)

**portable-app-v2.zip (20MB)**
- Pre-loaded SEC cache for 7 tickers
- Instant queries without initial fetch
- Larger file size

---

## 🔄 Transfer Methods

### Method 1: USB Drive
```bash
# On current PC
cp portable-app-v2-light.zip /Volumes/YOUR_USB_DRIVE/

# On new PC
cp /Volumes/YOUR_USB_DRIVE/portable-app-v2-light.zip ~/Downloads/
cd ~/Downloads
unzip portable-app-v2-light.zip
```

### Method 2: Cloud Storage (OneDrive, Dropbox, Google Drive)
```bash
# Upload to cloud, then download on new PC
# File path will be in your cloud sync folder
```

### Method 3: Network Transfer (SCP)
```bash
# If both PCs are on same network
scp portable-app-v2-light.zip user@other-pc:~/Downloads/
```

### Method 4: Email/Slack
- Light version (105KB) is small enough to email
- Full version (20MB) works for most platforms

---

## ⚙️ Setup on New PC

### 1. System Requirements
- Python 3.9+ (`python3 --version`)
- Node.js 16+ (`node --version`)
- Git (optional, for updates)

### 2. Install Python Dependencies
```bash
cd portable-app-v2/backend
python3 -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure API Keys
```bash
cd portable-app-v2/backend
cp .env.example .env
nano .env  # or use any text editor
```

**Required keys:**
```bash
OPENAI_API_KEY=sk-...              # Get from platform.openai.com
PINECONE_API_KEY=pcsk_...          # Get from app.pinecone.io
PINECONE_INDEX_NAME=mag7-sec-filings
PINECONE_ENVIRONMENT=us-east-1
```

### 4. Install Frontend Dependencies
```bash
cd ../frontend
npm install
```

### 5. Launch App
```bash
cd ..
bash start-all.sh
```

### 6. Fetch SEC Data (Light Version Only)

**Via UI:**
1. Open http://localhost:5173
2. Select ticker (AAPL, MSFT, etc.)
3. Click **"Fetch SEC Filings"**
4. Wait 10-15 seconds
5. Repeat for other tickers

**Via API (Faster for bulk):**
```bash
# Fetch all 7 tickers at once
for ticker in AAPL MSFT GOOGL AMZN META NVDA TSLA; do
  curl -X POST "http://localhost:8000/sec/fetch?ticker=$ticker"
  echo "Fetched $ticker"
done
```

---

## ✅ Verify Everything Works

### Check Backend
```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "pinecone_connected": true,
  "openai_configured": true
}
```

### Check Frontend
Open http://localhost:5173 in browser.

### Test a Query
1. Select ticker: AAPL
2. Ask: "What are Apple's main risk factors?"
3. Should respond in ~2-3 seconds (first query)
4. Cached queries: ~20ms (485x faster!)

---

## 🎯 Performance Expectations

**First Query (No Cache):**
- SEC fetch: 10-15 seconds (one-time)
- Retrieval + Response: 8-10 seconds

**Cached Queries:**
- 20ms response time
- 485x faster than cold start
- Compare mode: 16ms (610x faster)

**After Initial Setup:**
- All queries use cache
- Instant responses
- No re-fetching needed

---

## 🔧 Troubleshooting

### "Port already in use"
```bash
# Kill existing processes
lsof -ti:8000 | xargs kill -9   # Backend
lsof -ti:5173 | xargs kill -9   # Frontend
```

### "Module not found"
```bash
# Reinstall dependencies
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

### "API key invalid"
- Double-check `.env` file
- Ensure no extra spaces
- Verify keys at provider websites

### "Pinecone connection failed"
- Confirm index name: `mag7-sec-filings`
- Check environment matches (us-east-1)
- Test connection: `curl http://localhost:8000/health`

---

## 💡 Pro Tips

1. **Use Ollama for Free Testing**
   - Install: `curl https://ollama.ai/install.sh | sh`
   - Download model: `ollama pull llama3.2:3b`
   - No API costs!

2. **Enable Docker for Easier Setup**
   ```bash
   docker-compose up -d
   # No manual dependency installation!
   ```

3. **Cache Everything**
   - Fetch all 7 tickers on first run
   - Enables instant compare queries
   - Reduces API costs

4. **Monitor Performance**
   ```bash
   # Watch logs
   tail -f backend/backend.log
   
   # Check cache hits
   ls -lh backend/sec_cache/
   ```

---

## 📞 Need Help?

Check logs:
```bash
tail -f backend/backend.log
tail -f frontend/frontend.log
```

Test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Test query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Apple?", "ticker": "AAPL"}'
```

API Documentation:
http://localhost:8000/docs

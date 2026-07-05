# Industrial Knowledge Intelligence System - UPDATED

**Complete, production-ready solution with proper React app structure and environment variable support**

---

## 🆕 What's Changed

### ✅ Frontend Structure
- **Before:** Single JSX file (can't be deployed as static site)
- **After:** Proper React app with `package.json`, `public/`, `src/` folder structure
- **Result:** Can be deployed to Render Static Sites, Vercel, or Netlify

### ✅ Environment Variables
- **Before:** Hardcoded URLs and API keys
- **After:** Proper `.env` and `.env.example` files with all required variables
- **Result:** Works seamlessly on localhost and production (Render)

### ✅ Backend Configuration
- **Before:** Minimal error handling for missing environment variables
- **After:** Full graceful degradation when optional services aren't configured
- **Result:** Backend works even if Neo4j isn't available; clearly logs what's configured

---

## 📦 Project Structure

```
ikis/
├── ikis-backend/
│   ├── ikis_backend_updated.py      ← Updated backend with env var handling
│   ├── requirements.txt
│   ├── sample_data.py
│   ├── .env.example                 ← Environment variables template
│   ├── .gitignore
│   └── Procfile                     ← For Render deployment
│
├── ikis-frontend/
│   ├── package.json                 ← React dependencies and scripts
│   ├── public/
│   │   └── index.html               ← HTML entry point
│   ├── src/
│   │   ├── index.js                 ← React DOM render
│   │   └── App.jsx                  ← Main app component
│   └── .env                         ← Frontend environment variables
│
├── .env.example                     ← All required environment variables
├── .gitignore                       ← Git ignore rules
└── DEPLOYMENT_GUIDE_UPDATED.md      ← Complete deployment instructions
```

---

## 🚀 Quick Start (20 minutes)

### Prerequisites
- Python 3.10+
- Node.js 18+
- OpenAI API key
- Anthropic API key

### Step 1: Backend Setup

```bash
# Create and setup backend
mkdir ikis-backend && cd ikis-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Copy files:
# - ikis_backend_updated.py (rename to ikis_backend.py)
# - requirements.txt
# - sample_data.py
# - .env.example (copy to .env and fill values)

# Install dependencies
pip install -r requirements.txt

# Fill in .env with your API keys
nano .env  # or use your favorite editor

# Create sample documents
python sample_data.py

# Start backend
python ikis_backend.py
# ✅ Running at http://localhost:8000
```

### Step 2: Frontend Setup

```bash
# Create React app (in different terminal)
cd ..
npx create-react-app ikis-frontend
cd ikis-frontend

# Copy files:
# - package.json (replace)
# - public/index.html (replace)
# - src/index.js (replace)
# - src/App.jsx (new)

# Create .env
echo "REACT_APP_BACKEND_URL=http://localhost:8000" > .env

# Install dependencies
npm install

# Start development server
npm start
# ✅ Opens http://localhost:3000
```

### Step 3: Test Everything

**Backend health:**
```bash
curl http://localhost:8000/api/health
```

**Browser tests:**
1. Go to http://localhost:3000
2. Click "📄 Documents" → Upload a sample document
3. Click "🔍 Expert Query" → Ask a question
4. Click "⚙️ Maintenance" → Get recommendations
5. Click "✅ Compliance" → Scan for gaps

---

## 🌍 Environment Variables

### Required

| Variable | Example | Where to Get |
|----------|---------|---|
| OPENAI_API_KEY | sk-proj-xxx | https://platform.openai.com/api-keys |
| ANTHROPIC_API_KEY | sk-ant-xxx | https://console.anthropic.com/ |

### Database

| Variable | Default | Purpose |
|----------|---------|---------|
| DATABASE_URL | sqlite:///./ikis.db | Where to store documents |

### Optional (Neo4j Knowledge Graph)

| Variable | Purpose |
|----------|---------|
| NEO4J_URI | bolt://localhost:7687 |
| NEO4J_USER | neo4j |
| NEO4J_PASSWORD | password |

### Frontend

| Variable | Default | Purpose |
|----------|---------|---------|
| REACT_APP_BACKEND_URL | http://localhost:8000 | Backend API endpoint |

### Create .env File

```bash
# Copy template
cp .env.example .env

# Fill in your keys
OPENAI_API_KEY=sk-proj-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
DATABASE_URL=sqlite:///./ikis.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## ☁️ Deploy to Render (2.5 hours)

### Step 1: Backend on Render Web Service

```bash
# In ikis-backend/ folder

# Create Procfile
echo "web: uvicorn ikis_backend:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create runtime.txt
echo "python-3.11.0" > runtime.txt

# Initialize Git
git init
git add -A
git commit -m "Initial commit: IKIS backend"
git remote add origin https://github.com/YOUR_USERNAME/ikis-backend.git
git push -u origin main
```

**On Render.com:**
1. New+ → Web Service
2. Connect GitHub repo
3. Name: `ikis-backend`
4. Build: `pip install -r requirements.txt`
5. Start: `uvicorn ikis_backend:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables:
   - `OPENAI_API_KEY=sk-proj-xxx`
   - `ANTHROPIC_API_KEY=sk-ant-xxx`
   - `DATABASE_URL=sqlite:////var/data/ikis.db`
7. Deploy!
8. **Copy your Render backend URL** (will be `https://ikis-backend.onrender.com`)

### Step 2: Frontend on Render Static Site

```bash
# In ikis-frontend/ folder

# Create .env.production
cat > .env.production << EOF
REACT_APP_BACKEND_URL=https://ikis-backend.onrender.com
EOF

# Build production bundle
npm run build

# Commit to Git
git add build/ .env.production
git commit -m "Add production build"
git push
```

**On Render.com:**
1. New+ → Static Site
2. Connect same GitHub repo
3. Name: `ikis-frontend`
4. Build Command: `npm install && npm run build`
5. Publish Directory: `ikis-frontend/build`
6. Deploy!

**Done!**
- Backend: `https://ikis-backend.onrender.com`
- Frontend: `https://ikis-frontend.onrender.com`

---

## 🔧 API Endpoints

**All endpoints documented at:** `http://localhost:8000/docs` (Swagger UI)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/documents/upload` | Upload document |
| POST | `/api/query` | Query knowledge base |
| GET | `/api/maintenance/recommendations/{equipment_id}` | Get maintenance recs |
| GET | `/api/compliance/gaps` | Check compliance gaps |
| GET | `/api/health` | System health check |

### Example Requests

**Upload Document:**
```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@sample_docs/CP2000_Equipment_Manual.txt" \
  -F "doc_type=equipment_manual"
```

**Query RAG:**
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the maintenance procedures?",
    "include_citations": true
  }'
```

**Get Maintenance Recommendations:**
```bash
curl "http://localhost:8000/api/maintenance/recommendations/PUMP-001"
```

**Check Compliance:**
```bash
curl "http://localhost:8000/api/compliance/gaps"
```

---

## 🐛 Troubleshooting

### Backend Issues

**Problem:** `ModuleNotFoundError: No module named 'anthropic'`
```bash
# Solution:
pip install -r requirements.txt
```

**Problem:** API keys not working
```bash
# Solution: Verify .env file exists and has correct keys
cat .env
# Should see:
# OPENAI_API_KEY=sk-proj-...
# ANTHROPIC_API_KEY=sk-ant-...
```

**Problem:** Backend returns "Vector store not available"
```bash
# Solution: Make sure OPENAI_API_KEY is set
# Frontend queries will fail without OpenAI embeddings
```

### Frontend Issues

**Problem:** `npm ERR! code ENOENT`
```bash
# Solution:
rm -rf node_modules
npm install
```

**Problem:** "Cannot connect to backend"
```bash
# Check:
# 1. Is backend running? (ps aux | grep uvicorn)
# 2. Is REACT_APP_BACKEND_URL correct in .env?
# 3. Restart frontend: npm start
```

**Problem:** Frontend shows CORS errors
```bash
# Solution: Backend CORS is configured to allow all (*) 
# This is fine for hackathon
# For production, edit ikis_backend.py and change:
# allow_origins=["https://ikis-frontend.onrender.com"]
```

---

## 📝 Key Changes Summary

### Frontend (React App Structure)
✅ `package.json` - Proper npm configuration
✅ `public/index.html` - HTML entry point
✅ `src/index.js` - React DOM render
✅ `src/App.jsx` - Main component with environment variables
✅ `.env` support - `REACT_APP_BACKEND_URL` read from environment

### Backend (Environment Variables)
✅ Proper `.env.example` template
✅ Graceful error handling for missing APIs
✅ Logs what's configured on startup
✅ Works with SQLite, PostgreSQL, Neo4j optionally
✅ CORS configured for frontend communication

### Deployment
✅ `Procfile` for Render Web Service
✅ `runtime.txt` for Python version specification
✅ `.gitignore` for clean Git repositories
✅ `DEPLOYMENT_GUIDE_UPDATED.md` - Step-by-step Render instructions

---

## 🎯 For Hackathon

1. **Setup locally** (20 min) - Use Quick Start above
2. **Test all 4 features** (10 min) - Upload, Query, Maintenance, Compliance
3. **Deploy to Render** (2 hours) - Follow DEPLOYMENT_GUIDE_UPDATED.md
4. **Final testing** (30 min) - Verify production deployment works
5. **Record demo video** (10 min) - As backup
6. **Rehearse pitch** (1 hour) - Practice 5-minute presentation

**Total: ~4.5 hours from zero to production ready**

---

## 📚 Files Included

| File | Purpose |
|------|---------|
| ikis_backend_updated.py | Backend API with env var support |
| ikis_frontend.jsx | React app (put in src/App.jsx) |
| package.json | React dependencies |
| public/index.html | HTML entry point |
| src/index.js | React render |
| requirements.txt | Python dependencies |
| sample_data.py | Test documents |
| .env.example | Environment variables template |
| .gitignore | Git ignore rules |
| Procfile | Render backend configuration |
| DEPLOYMENT_GUIDE_UPDATED.md | Complete deployment guide |

---

## ✨ What You Get

✅ **Complete System**
- Backend API with RAG, knowledge graphs, AI agents
- Professional React dashboard with 4 tabs
- Proper app structure ready for production

✅ **Environment Variables**
- Supports localhost and cloud deployment
- All API keys configured via .env
- Different database options (SQLite, PostgreSQL)

✅ **Deployment Ready**
- Works on Render Web Service (backend)
- Works on Render Static Sites (frontend)
- Clear instructions for each platform

✅ **Documentation**
- This README
- Updated deployment guide
- Environment variable reference
- Troubleshooting guide

---

## 🚀 You're Ready!

Everything is set up for:
1. **Local development** - Test everything locally first
2. **Cloud deployment** - Deploy to Render with 1 click per service
3. **Hackathon submission** - Fully working system with working URLs

Start with the Quick Start above. You'll have it running locally in 20 minutes.

**Good luck! 🎉**

---

*Industrial Knowledge Intelligence System - ET AI Hackathon 2026*

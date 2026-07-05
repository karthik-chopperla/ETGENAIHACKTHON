# IKIS Deployment Guide - Updated for React App Structure

## 📋 New Project Structure

Your frontend is now a proper React app with:
```
ikis-frontend/
├── package.json          # Dependencies and scripts
├── public/
│   └── index.html       # HTML entry point
├── src/
│   ├── index.js         # React DOM render
│   └── App.jsx          # Main app component
└── .env                 # Environment variables
```

Your backend remains:
```
ikis-backend/
├── ikis_backend_updated.py  # Updated with env var handling
├── requirements.txt
├── .env
└── sample_data.py
```

---

## 🚀 Quick Start (Local Development - 20 minutes)

### Step 1: Backend Setup

```bash
# Create backend directory
mkdir ikis-backend && cd ikis-backend

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Copy files:
# - ikis_backend_updated.py (rename to ikis_backend.py)
# - requirements.txt
# - sample_data.py
# - .env.example (rename to .env and fill in values)

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cat > .env << EOF
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATABASE_URL=sqlite:///./ikis.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EOF

# Create sample data
python sample_data.py

# Start backend
python ikis_backend.py
# Server runs at http://localhost:8000
```

### Step 2: Frontend Setup

```bash
# In new terminal, create React app
cd ..
npx create-react-app ikis-frontend
cd ikis-frontend

# Copy files:
# - package.json (replace existing)
# - public/index.html
# - src/index.js
# - src/App.jsx

# Create .env file
cat > .env << EOF
REACT_APP_BACKEND_URL=http://localhost:8000
EOF

# Install dependencies
npm install

# Start development server
npm start
# Opens http://localhost:3000
```

### Step 3: Test Everything

**Backend Health:**
```bash
curl http://localhost:8000/api/health
```

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
    "query": "What maintenance procedures exist?",
    "include_citations": true
  }'
```

---

## ☁️ Deploy to Production (2.5 hours)

### Option A: Backend on Render Web Service + Frontend on Render Static Site (RECOMMENDED)

#### Step 1A: Prepare Backend for Render

```bash
cd ikis-backend

# Create Procfile
cat > Procfile << EOF
web: uvicorn ikis_backend:app --host 0.0.0.0 --port $PORT
EOF

# Create runtime.txt
echo "python-3.11.0" > runtime.txt

# Create .gitignore
cat > .gitignore << EOF
venv/
__pycache__/
*.db
chroma_db/
.env
.pytest_cache/
EOF

# Initialize Git
git init
git add -A
git commit -m "Initial commit: IKIS backend"
git remote add origin https://github.com/yourusername/ikis-backend.git
git push -u origin main
```

#### Step 2A: Deploy Backend to Render

1. Go to https://render.com
2. Sign up/login
3. Click "New+" → "Web Service"
4. Select your GitHub repository
5. Configure:
   - **Name:** ikis-backend
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn ikis_backend:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (for hackathon)

6. Add Environment Variables:
   ```
   OPENAI_API_KEY = sk-proj-your-key
   ANTHROPIC_API_KEY = sk-ant-your-key
   DATABASE_URL = sqlite:////var/data/ikis.db
   NEO4J_URI = bolt://your-neo4j-url.com:7687
   NEO4J_USER = neo4j
   NEO4J_PASSWORD = your-password
   ```

7. Click "Create Web Service"
8. Wait 5-10 minutes → Backend deployed to `https://ikis-backend.onrender.com`
9. **Copy this URL** for frontend configuration

#### Step 3A: Build Frontend

```bash
cd ../ikis-frontend

# Create .env.production
cat > .env.production << EOF
REACT_APP_BACKEND_URL=https://ikis-backend.onrender.com
EOF

# Build production bundle
npm run build
# Creates build/ folder with static files
```

#### Step 4A: Deploy Frontend to Render Static Site

1. In same GitHub repo, push the build folder:
```bash
git add build
git commit -m "Add production build"
git push
```

2. Go to Render → "New+" → "Static Site"
3. Connect same GitHub repository
4. Configure:
   - **Name:** ikis-frontend
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `ikis-frontend/build`
   - **Plan:** Free

5. Click "Create Static Site"
6. Wait 3-5 minutes → Frontend deployed to `https://ikis-frontend.onrender.com`

---

### Option B: Deploy Everything to Single Render Web Service (Alternative)

If you want both backend and frontend in one service:

1. Create folder structure:
```
ikis/
├── backend/
│   ├── ikis_backend.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── public/
│   └── src/
└── start.sh
```

2. Create `start.sh`:
```bash
#!/bin/bash

# Install and build frontend
cd frontend
npm install
npm run build

# Install and start backend
cd ../backend
pip install -r requirements.txt
uvicorn ikis_backend:app --host 0.0.0.0 --port $PORT
```

3. Create Procfile:
```
web: ./start.sh
```

**This works but is slower** - Static Site deployment (Option A) is preferred.

---

## 🌍 Production Environment Variables

### On Render Dashboard:

1. Backend Web Service → Settings → Environment
2. Add each variable (copy from .env.example):

```
OPENAI_API_KEY = sk-proj-xxxxx
ANTHROPIC_API_KEY = sk-ant-xxxxx
DATABASE_URL = sqlite:////var/data/ikis.db
NEO4J_URI = bolt://xxxx.neo4j.io:7687
NEO4J_USER = neo4j
NEO4J_PASSWORD = xxxxx
```

### For Frontend Static Site:

Build-time environment variables in Render dashboard:
```
REACT_APP_BACKEND_URL = https://ikis-backend.onrender.com
```

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Check logs in Render dashboard
# Common issues:
# - OPENAI_API_KEY not set → Query will fail
# - ANTHROPIC_API_KEY not set → Entity extraction will fail
# - DATABASE_URL wrong format → Database connection fails

# Solution: Verify all environment variables in Render dashboard
```

### Frontend shows "Cannot connect to backend"
```bash
# Check:
# 1. Backend service is running (check Render dashboard)
# 2. REACT_APP_BACKEND_URL is correct (should be your Render backend URL)
# 3. Frontend rebuilt with correct URL (npm run build)

# Solution: Rebuild with correct backend URL
REACT_APP_BACKEND_URL=https://ikis-backend.onrender.com npm run build
```

### CORS errors in browser console
```bash
# Backend CORS is set to allow all origins (*)
# This is configured in ikis_backend_updated.py:
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, restrict to frontend domain
# )

# Solution: No action needed for hackathon
# For production: Change to allow_origins=["https://ikis-frontend.onrender.com"]
```

### Database errors
```
# SQLite is fine for hackathon
# For production, use PostgreSQL:

# On Render:
# 1. Create PostgreSQL database (Render → Services → PostgreSQL)
# 2. Copy connection string
# 3. Set DATABASE_URL to PostgreSQL connection string
# 4. Restart backend

# Connection string format:
# postgresql://user:password@host:port/dbname
```

---

## 📊 Deployment Checklist

### Before Deploying

- [ ] All environment variables defined in .env.example
- [ ] Backend tested locally with sample documents
- [ ] Frontend loads at http://localhost:3000
- [ ] All 4 demo flows work (upload, query, maintenance, compliance)
- [ ] `npm run build` succeeds without errors
- [ ] Git repository initialized and committed

### Render Backend Deployment

- [ ] Procfile created
- [ ] runtime.txt specifies Python 3.11
- [ ] .gitignore configured
- [ ] Code pushed to GitHub
- [ ] Environment variables added to Render dashboard
- [ ] Backend service is running (green status)
- [ ] Health check passes: `curl https://ikis-backend.onrender.com/api/health`

### Render Frontend Deployment

- [ ] build/ folder created (`npm run build`)
- [ ] .env.production has correct REACT_APP_BACKEND_URL
- [ ] Frontend pushed to GitHub
- [ ] Static site service is running
- [ ] Frontend loads without 404 errors

### Post-Deployment

- [ ] Frontend opens at Render URL
- [ ] API calls work (check browser DevTools Network tab)
- [ ] Document upload works
- [ ] Queries return results
- [ ] No CORS errors in console

---

## 🎯 Total Deployment Time

- **Local setup:** 20 minutes
- **Build frontend:** 5 minutes
- **Deploy backend to Render:** 5-10 minutes (wait for build)
- **Deploy frontend to Render:** 3-5 minutes (wait for build)
- **Total:** ~45 minutes

**For hackathon:** Deploy 2-3 days before so you have backup time.

---

## 💡 Environment Variable Reference

| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| OPENAI_API_KEY | Yes | sk-proj-xxx | Text embeddings for RAG |
| ANTHROPIC_API_KEY | Yes | sk-ant-xxx | Claude AI for extraction + reasoning |
| DATABASE_URL | Yes | sqlite:///./ikis.db | Document storage |
| NEO4J_URI | No | bolt://localhost:7687 | Knowledge graph (optional) |
| NEO4J_USER | No | neo4j | Neo4j auth |
| NEO4J_PASSWORD | No | password | Neo4j auth |
| REACT_APP_BACKEND_URL | Yes (frontend) | http://localhost:8000 | Backend URL for frontend |

---

## 🔐 Security Notes

1. **Never commit .env file** → Use .env.example only
2. **Use Render's environment variables** → Don't hardcode secrets
3. **SQLite in production** → Suitable for hackathon, use PostgreSQL for real product
4. **CORS allow_origins: "*"** → Change to specific domain in production

---

## ✅ Your Checklist for Render Deployment

**Right now:**
1. [ ] Copy all files to proper structure
2. [ ] Create .env file with your API keys
3. [ ] Test locally: `python ikis_backend.py` + `npm start`
4. [ ] Git push: `git add . && git commit && git push`

**Tomorrow:**
1. [ ] Create Render Web Service for backend
2. [ ] Create Render Static Site for frontend
3. [ ] Set environment variables
4. [ ] Test cloud deployment
5. [ ] Get Render URLs

**Day before hackathon:**
1. [ ] Final testing of cloud deployment
2. [ ] Verify backend health endpoint
3. [ ] Verify all 4 demo flows work
4. [ ] Record backup demo video

---

That's it! You're ready for production deployment. Good luck! 🚀

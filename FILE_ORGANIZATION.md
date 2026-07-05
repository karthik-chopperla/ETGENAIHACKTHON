# IKIS Files - Where They Go

**Quick reference for organizing downloaded files**

---

## 📂 Your Project Structure (After Setup)

```
ikis/
│
├─ ikis-backend/
│  ├─ ikis_backend.py                  ← ikis_backend_updated.py (renamed)
│  ├─ requirements.txt                 ← from previous files
│  ├─ sample_data.py                   ← from previous files
│  ├─ .env                             ← copy from .env.example and fill in values
│  ├─ .gitignore                       ← new file
│  ├─ Procfile                         ← for Render deployment (create this)
│  └─ venv/                            ← created by: python -m venv venv
│
├─ ikis-frontend/
│  ├─ package.json                     ← new file
│  ├─ .env                             ← create: REACT_APP_BACKEND_URL=...
│  ├─ .env.production                  ← for production deployment
│  ├─ public/
│  │  ├─ index.html                    ← new file (replaces default)
│  │  └─ favicon.ico                   ← (optional, keep default)
│  ├─ src/
│  │  ├─ index.js                      ← new file
│  │  └─ App.jsx                       ← new file
│  ├─ node_modules/                    ← created by: npm install
│  └─ build/                           ← created by: npm run build
│
├─ .env.example                        ← reference only (don't use directly)
├─ .gitignore                          ← copy to root folder
├─ README_UPDATED.md                   ← READ THIS FIRST
├─ DEPLOYMENT_GUIDE_UPDATED.md         ← for Render deployment
└─ UPDATE_SUMMARY.md                   ← what changed summary
```

---

## 📥 Download → Organize → Use

### Files to Download (10 files)

```
✓ package.json                    → backend-folder
✓ index.html                      → frontend/public/
✓ index.js                        → frontend/src/
✓ App.jsx                         → frontend/src/
✓ ikis_backend_updated.py         → backend-folder (rename to ikis_backend.py)
✓ .env.example                    → root folder
✓ .gitignore                      → backend-folder and root
✓ DEPLOYMENT_GUIDE_UPDATED.md     → root folder
✓ README_UPDATED.md               → root folder
✓ UPDATE_SUMMARY.md               → root folder (this one!)
```

### Plus Keep These From Before

```
✓ requirements.txt                → backend-folder (unchanged)
✓ sample_data.py                  → backend-folder (unchanged)
```

---

## 🚀 Setup Sequence

### 1. Download All Files
- [ ] Download all 10 new files
- [ ] Download 2 files from before (requirements.txt, sample_data.py)

### 2. Create Folders
```bash
mkdir ikis-project
cd ikis-project
mkdir ikis-backend
mkdir ikis-frontend
```

### 3. Backend Setup
```bash
cd ikis-backend

# Copy these files:
# - ikis_backend_updated.py (rename → ikis_backend.py)
# - requirements.txt
# - sample_data.py
# - .env.example (rename → .env, then edit with your keys)
# - .gitignore

# Create Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python sample_data.py

cd ..
```

### 4. Frontend Setup
```bash
cd ikis-frontend

# Copy these files:
# - package.json
# - .gitignore

# Create folders:
mkdir public src

# Copy into folders:
# - index.html → public/
# - index.js → src/
# - App.jsx → src/

# Create .env file
echo "REACT_APP_BACKEND_URL=http://localhost:8000" > .env

# Install dependencies
npm install

cd ..
```

### 5. Test Locally
```bash
# Terminal 1: Backend
cd ikis-backend
python ikis_backend.py
# ✅ http://localhost:8000

# Terminal 2: Frontend
cd ikis-frontend
npm start
# ✅ http://localhost:3000
```

---

## 🔧 Configuration Files

### Backend Configuration (.env)

**Location:** `ikis-backend/.env`

**Content:**
```
OPENAI_API_KEY=sk-proj-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
DATABASE_URL=sqlite:///./ikis.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

**How to create:**
```bash
cp .env.example ikis-backend/.env
nano ikis-backend/.env  # Edit with your keys
```

### Frontend Configuration (.env)

**Location:** `ikis-frontend/.env`

**Content:**
```
REACT_APP_BACKEND_URL=http://localhost:8000
```

**How to create:**
```bash
echo "REACT_APP_BACKEND_URL=http://localhost:8000" > ikis-frontend/.env
```

### Production Configuration (.env.production)

**Location:** `ikis-frontend/.env.production`

**Content:**
```
REACT_APP_BACKEND_URL=https://ikis-backend.onrender.com
```

**How to create:**
```bash
cat > ikis-frontend/.env.production << EOF
REACT_APP_BACKEND_URL=https://ikis-backend.onrender.com
EOF
```

---

## 📋 File Checklist

### Backend Folder

- [ ] ikis_backend.py (from ikis_backend_updated.py)
- [ ] requirements.txt
- [ ] sample_data.py
- [ ] .env (created from .env.example)
- [ ] .gitignore
- [ ] venv/ (created by python -m venv venv)

### Frontend Folder

- [ ] package.json
- [ ] .env (created manually)
- [ ] public/index.html
- [ ] src/index.js
- [ ] src/App.jsx
- [ ] node_modules/ (created by npm install)

### Root Folder

- [ ] .env.example (reference)
- [ ] .gitignore
- [ ] README_UPDATED.md
- [ ] DEPLOYMENT_GUIDE_UPDATED.md
- [ ] UPDATE_SUMMARY.md

---

## ⚡ Quick Commands

```bash
# Backend setup
cd ikis-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python sample_data.py
python ikis_backend.py

# Frontend setup
cd ../ikis-frontend
npm install
npm start

# Frontend build
npm run build

# Backend with Render deployment
cd ../ikis-backend
echo "web: uvicorn ikis_backend:app --host 0.0.0.0 --port \$PORT" > Procfile
echo "python-3.11.0" > runtime.txt
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOU/ikis-backend.git
git push -u origin main
```

---

## 🆚 File Naming

| New Filename | What It Is | Rename To? |
|---|---|---|
| ikis_backend_updated.py | Backend with env vars | ikis_backend.py |
| App.jsx | React component | No rename |
| index.html | HTML entry | No rename |
| index.js | React DOM render | No rename |
| package.json | NPM config | No rename |
| .env.example | Env var template | Copy to .env |
| .gitignore | Git ignore | No rename |
| Procfile | Render config | No rename |

---

## 📝 File Sizes (For Reference)

- ikis_backend_updated.py: ~20 KB
- App.jsx: ~18 KB
- package.json: ~0.5 KB
- index.html: ~2 KB
- index.js: ~0.3 KB
- .env.example: ~2 KB
- Total: ~43 KB (all new files combined)

---

## ✅ Verification

After setup, you should have:

```bash
# Check backend
ls -la ikis-backend/
# Should see: ikis_backend.py, requirements.txt, sample_data.py, .env, venv/

# Check frontend
ls -la ikis-frontend/
# Should see: package.json, public/, src/, node_modules/, .env

# Check root
ls -la ./
# Should see: .env.example, .gitignore, README_UPDATED.md, etc.
```

---

## 🎯 Three Simple Steps

**Step 1:** Download 10 files, organize in folders as shown above

**Step 2:** Fill in .env with your API keys
```bash
OPENAI_API_KEY=sk-proj-your-actual-key
ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

**Step 3:** Run
```bash
# Terminal 1
cd ikis-backend && python ikis_backend.py

# Terminal 2
cd ikis-frontend && npm start
```

That's it! System runs at http://localhost:3000

---

**Need help?** Read README_UPDATED.md Quick Start section (5 minutes)

**Ready to deploy?** Read DEPLOYMENT_GUIDE_UPDATED.md (complete instructions)

**Want to understand changes?** Read UPDATE_SUMMARY.md (what changed and why)

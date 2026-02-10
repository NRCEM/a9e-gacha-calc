# A9E Gacha Calc (Arknight Endfield)

A small web calculator for an Endfield-style gacha banner.

## What it shows
- Chance to get the **current banner Limited** (at least once)
- Chance to get **off-banner 6★** (at least once)
- Chance to get **other-version Limited 6★** (at least once)
- **Minimum guaranteed** total 6★ under worst-luck (hard pity only)
- **Expected 5★ count** with **10-pull guarantee (5★+)**

## Repo structure
- `backend/` FastAPI API
- `frontend/` Static HTML/CSS/JS UI

---

## Run locally (Windows)

### Backend
    cd .\backend
    python -m pip install -r requirements.txt
    python -m uvicorn app:app --reload --port 8000

Docs:
- http://127.0.0.1:8000/docs

### Frontend
    cd .\frontend
    python -m http.server 5500

Open:
- http://127.0.0.1:5500

> If your backend is deployed, update `API_BASE` in `frontend/main.js`.

---

## Deploy

### Backend (Railway example)
Add these files in `backend/`:

Procfile:
    web: uvicorn app:app --host 0.0.0.0 --port $PORT

runtime.txt:
    python-3.12.0

Then deploy the `backend/` folder as a service.

### Frontend (Vercel/Netlify)
Deploy `frontend/` as a static site.
Set `API_BASE` in `frontend/main.js` to your backend URL.

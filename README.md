# ClinicalFHIR

AI-powered Revenue Cycle Management platform for cashless hospitalization. Converts clinical documents into FHIR R4 bundles and manages the full insurance claim lifecycle — from pre-authorization to settlement.

---

## What it does

| Module | Description |
|--------|-------------|
| **Document Processing** | Upload PDFs, images, Word, Excel, or CSV — Gemini extracts structured clinical data and generates FHIR R4 bundles |
| **Pre-Authorization** | Fill and submit cashless hospitalization pre-auth forms; auto-fill via ABHA ID lookup and medical document upload |
| **Enhancement** | Raise enhancement requests when treatment scope or costs change during admission |
| **Discharge** | Capture final diagnosis, procedure codes, and bill breakdown; Gemini-powered financial audit with document references |
| **Settlement** | Record TPA settlement, deductions, and final payout |
| **Patient Records** | Persistent per-patient FHIR store with claim readiness scoring |

---

## Tech Stack

**Backend** — FastAPI · Gemini (google-generativeai) · PyMuPDF · doctr OCR · fhir.resources · Supabase · fpdf2

**Frontend** — React 18 · TypeScript · Vite · Tailwind CSS v4 · Axios

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gemini API key — [aistudio.google.com](https://aistudio.google.com)
- Supabase project (URL + service role key)

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173` · API docs at `http://localhost:8000/docs`

---

## Environment Variables

**`backend/.env`**
```env
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=http://localhost:5173
```

**`frontend/.env`** (optional)
```env
VITE_API_URL=http://localhost:8000/api
```

---

## API Overview

```
GET  /api/health
POST /api/process-pdf

GET  /api/patients
GET  /api/patients/{id}

POST /api/pre-auth
GET  /api/pre-auth/{id}
PUT  /api/pre-auth/{id}
POST /api/pre-auth/{id}/extract-medical
POST /api/pre-auth/{id}/generate-pdf

POST /api/enhancement/pre-auth/{id}
GET  /api/enhancement/pre-auth/{id}

POST /api/discharge
PUT  /api/discharge/{id}
POST /api/discharge/{id}/extract
POST /api/discharge/{id}/financial-audit

POST /api/settlement
PUT  /api/settlement/{id}

GET  /api/cases
GET  /api/cases/{bill_no}
```

---

## Notes

- Gemini free tier: ~500 req/day on `gemini-2.5-flash`. Generate a new API key if quota is exhausted.
- Supabase schema is in `backend/supabase_schema.sql` — run it once to create all tables.
- Dummy patient data for testing is in `dummy_data/`.

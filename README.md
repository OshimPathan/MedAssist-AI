<div align="center">

# 🏥 MedAssist AI

### Real-Time Intelligent Hospital Communication & Emergency Response System

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?logo=mongodb&logoColor=white)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![PWA](https://img.shields.io/badge/PWA-Installable-5A0FC8?logo=pwa&logoColor=white)](#-progressive-web-app)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A 24/7 AI-powered hospital assistant that handles patient triage, appointment booking, emergency detection, and intelligent Q&A — with real-time dashboards, Chart.js analytics, and PWA support.

[Features](#-features) · [Tech Stack](#-tech-stack) · [Quick Start](#-quick-start) · [Architecture](#-architecture) · [API Docs](#-api-endpoints) · [Screenshots](#-screenshots)

</div>

---

## ✨ Features

### 🤖 AI-Powered Intelligence
- **Multi-Provider LLM** — Google Gemini (free), Ollama (local), OpenAI (fallback) with automatic failover
- **Intent Classification** — Rule-based + NLP pipeline for understanding patient queries
- **RAG System** — FAISS vector store with sentence-transformers for context-aware hospital Q&A
- **AI Guardrails** — Strict filters prevent diagnosis/prescription; always recommends professional consultation

### 🚨 Emergency Triage System
- **70+ symptom weights** with severity scoring (CRITICAL → NON_URGENT)
- **Real-time emergency detection** from chat messages
- **Emergency orchestration** — location collection → staff alerts → first-aid guidance
- **Multi-channel alerts** to dashboard + SMS + WhatsApp + Email

### 📅 Appointment Engine
- **Smart booking** with slot locking (prevents double-booking)
- **Available slots API** — query doctor availability by date
- **Reschedule/Cancel** with conflict re-validation
- **Confirmation notifications** via SMS, WhatsApp, Email, and in-app

### 📊 Analytics Dashboard
- **6 interactive Chart.js visualizations**:
  - 7-day activity trends (conversations, appointments, emergencies)
  - Emergency severity distribution (doughnut)
  - Appointment status breakdown
  - AI intent classification (horizontal bar)
  - Department load analysis (30-day)
  - Hourly activity heatmap

### 🔒 Security & GDPR Compliance
- JWT authentication with role-based access (Admin, Doctor, Receptionist, Patient)
- AES-256 (Fernet) encryption for PII at rest
- API rate limiting (sliding window, 60 req/min)
- GDPR endpoints: consent management, data export (Art. 15), data erasure (Art. 17)
- Complete audit trail logging

### 📱 Progressive Web App (PWA)
- Installable on iOS, Android, and desktop
- Service worker with network-first caching
- Offline fallback page with emergency numbers
- Push notification support (service worker ready)

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Async REST API framework |
| **Prisma** | Type-safe ORM for MongoDB |
| **FAISS** | Vector similarity search (RAG) |
| **sentence-transformers** | Text embeddings (MiniLM-L6-v2) |
| **Google Gemini** | Primary LLM (free tier) |
| **Twilio** | SMS & WhatsApp notifications |
| **Fernet/cryptography** | AES encryption for PII |
| **python-jose** | JWT token management |
| **pytest** | Unit testing (33 tests) |

### Frontend
| Technology | Purpose |
|-----------|---------|
| **React 18** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool & dev server |
| **Chart.js** | Analytics visualizations |
| **Tailwind CSS** | Utility-first styling |
| **React Router** | Client-side routing |
| **WebSocket** | Real-time chat communication |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| **PostgreSQL 16** | Primary database |
| **Docker Compose** | Container orchestration |
| **Redis** | Session & cache (optional) |
| **Service Worker** | PWA offline support |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ & Node.js 18+
- MongoDB 7 (or Docker)
- Google Gemini API key ([get free](https://aistudio.google.com/apikey))

### 1. Clone & Configure

```bash
git clone https://github.com/OshimPathan/MedAssist-AI.git
cd MedAssist-AI
cp .env.example .env
```

Edit `.env` and set:
```env
DATABASE_URL="mongodb://localhost:27017/medassist_db"
SECRET_KEY="your-secret-key-here"
GOOGLE_GEMINI_API_KEY="your-gemini-key"
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
prisma generate
prisma db push
uvicorn app.main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Access the App

| Service | URL |
|---------|-----|
| 💬 Patient Chat | http://localhost:3000 |
| ⚙️ Admin Dashboard | http://localhost:3000/admin |
| 📊 Analytics | http://localhost:3000/analytics |
| 📚 API Docs (Swagger) | http://localhost:8000/api/docs |

### Docker (Alternative)

```bash
docker-compose up -d
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Chat UI  │  │ Admin Panel  │  │ Analytics (Chart.js)   │ │
│  └────┬─────┘  └──────┬───────┘  └───────────┬────────────┘ │
│       │               │                      │              │
│       └───────────────┼──────────────────────┘              │
│                       │  REST + WebSocket                    │
├───────────────────────┼─────────────────────────────────────┤
│                    Backend (FastAPI)                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Auth &  │  │ Triage & │  │  RAG &   │  │ Appointments │ │
│  │ RBAC    │  │Emergency │  │  LLM AI  │  │ & Scheduling │ │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │            │             │                │         │
│  ┌────┴────────────┴─────────────┴────────────────┴───────┐ │
│  │              Prisma ORM + MongoDB                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │ Rate Limiter │  │ Encryption │  │ Audit Logger         │ │
│  └──────────────┘  └────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         ┌────┴───┐  ┌───┴────┐  ┌──┴─────┐
         │ Twilio │  │  SMTP  │  │ Gemini │
         │SMS/WA  │  │ Email  │  │  LLM   │
         └────────┘  └────────┘  └────────┘
```

---

## 📁 Project Structure

```
MedAssist-AI/
├── backend/
│   ├── app/
│   │   ├── api/                 # REST API endpoints
│   │   │   ├── auth.py          # Registration, login, JWT
│   │   │   ├── chat.py          # WebSocket chat handler
│   │   │   ├── appointments.py  # Booking with slot locking
│   │   │   ├── admin.py         # Dashboard stats & logs
│   │   │   ├── analytics.py     # Chart.js data aggregation
│   │   │   ├── emergency.py     # Emergency case management
│   │   │   ├── compliance.py    # GDPR consent, export, erasure
│   │   │   ├── triage_api.py    # Symptom assessment API
│   │   │   └── knowledge.py     # RAG knowledge base CRUD
│   │   ├── ai_engine/
│   │   │   ├── llm_client.py    # Multi-provider LLM (Gemini/Ollama/OpenAI)
│   │   │   ├── intent_classifier.py
│   │   │   ├── rag_engine.py    # FAISS vector store
│   │   │   ├── guardrails.py    # Safety filters
│   │   │   └── conversation_manager.py
│   │   ├── triage/
│   │   │   ├── triage_engine.py # 70+ symptom severity scoring
│   │   │   └── emergency_orchestrator.py
│   │   ├── services/
│   │   │   └── notification_service.py  # SMS/WhatsApp/Email/InApp
│   │   ├── utils/
│   │   │   ├── security.py      # JWT, password hashing, RBAC
│   │   │   ├── encryption.py    # Fernet AES + PII masking
│   │   │   ├── rate_limiter.py  # Sliding window middleware
│   │   │   └── audit_logger.py
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── prisma/
│   │   └── schema.prisma        # Database schema (9 models)
│   ├── tests/
│   │   └── test_core.py         # 33 unit tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx     # Patient chat interface
│   │   │   ├── AdminDashboard.tsx # 5-tab admin panel
│   │   │   ├── AnalyticsPage.tsx  # 6 Chart.js visualizations
│   │   │   └── LoginPage.tsx
│   │   ├── services/
│   │   │   ├── api.ts           # REST API client (20+ methods)
│   │   │   └── websocket.ts     # Real-time chat connection
│   │   └── App.tsx              # Router setup
│   ├── public/
│   │   ├── manifest.json        # PWA manifest
│   │   ├── sw.js                # Service worker
│   │   ├── offline.html         # Offline fallback
│   │   └── icons/               # 8 PWA icon sizes
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/api/chat/ws/{session_id}` | WebSocket chat |
| POST | `/api/chat/message` | Send message (REST) |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/appointments/` | List appointments |
| POST | `/api/appointments/` | Book appointment |
| PUT | `/api/appointments/{id}` | Reschedule |
| DELETE | `/api/appointments/{id}` | Cancel |
| GET | `/api/appointments/available-slots` | Query availability |
| POST | `/api/appointments/lock-slot` | Lock a slot |
| POST | `/api/appointments/release-slot` | Release a lock |

### Emergency & Triage
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/triage/assess` | Symptom assessment |
| GET | `/api/triage/first-aid/{condition}` | First-aid guidance |
| GET | `/api/emergency/` | List emergencies |
| PUT | `/api/emergency/{id}` | Update dispatch |

### Analytics & Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/overview` | Full analytics data |
| GET | `/api/admin/stats` | Dashboard metrics |
| GET | `/api/admin/conversations` | Chat logs |

### GDPR Compliance
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/compliance/consent` | Update consent |
| GET | `/api/compliance/data-export/{id}` | Export patient data |
| DELETE | `/api/compliance/data-erasure/{id}` | Anonymize & delete |

---

## 🧪 Testing

```bash
cd backend
source venv/bin/activate
pytest tests/test_core.py -v
```

**Results**: 32 passed, 1 skipped across 8 test modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| Triage Engine | 8 | Severity scoring, department mapping, first-aid |
| Intent Classifier | 6 | Emergency detection, fallback intents |
| Guardrails | 3 | Blocks diagnosis/prescription |
| Encryption | 5 | Encrypt/decrypt, PII masking, hashing |
| Slot Locking | 2 | Acquire/release locks |
| RAG Engine | 2 | Vector store init, document indexing |
| Seed Data | 3 | Knowledge base structure |
| Security | 3 | JWT roundtrip, password hashing |

---

## 🚨 Emergency Workflow

```
Patient Message → Intent Classification
                         │
                   ┌─────┴─────┐
                   │ Emergency  │
                   │ Detected?  │
                   └─────┬─────┘
                    YES  │  NO
              ┌──────────┤    └──→ Normal Response
              ▼          │
     Severity Scoring    │
     (70+ symptoms)      │
              │          │
              ▼          │
     Collect Location    │
     & Contact Info      │
              │          │
              ▼          │
     ┌────────┴────────┐ │
     │ Alert Dashboard │ │
     │ SMS Staff       │ │
     │ WhatsApp Admin  │ │
     │ Email Hospital  │ │
     └────────┬────────┘ │
              ▼          │
     First-Aid Guidance  │
     + Audit Log         │
```

---

## 📈 Roadmap

- [x] **Phase 1**: Foundation & Database Architecture
- [x] **Phase 2**: Core Communication (WebSocket, Chat UI)
- [x] **Phase 3**: AI & Intelligence (LLM, RAG, Intent Classification)
- [x] **Phase 4**: Triage & Emergency System
- [x] **Phase 5**: Appointment Engine (Slot Locking, Notifications)
- [x] **Phase 6**: Admin Dashboard (5 tabs, Real-time)
- [x] **Phase 7**: Security & GDPR Compliance
- [x] **Phase 8**: Testing & Deployment (33 unit tests, Docker)
- [x] **Phase 9**: Wow-Factor (Chart.js Analytics, PWA)

---

## ⚠️ Disclaimer

This system is for **informational and educational purposes only**. It does **not** provide medical diagnosis or prescribe medications. Built-in guardrails ensure:

- ❌ Never diagnoses medical conditions
- ❌ Never prescribes medications
- ✅ Always recommends consulting healthcare providers
- ✅ Encourages calling official emergency numbers

**Consult legal counsel and medical professionals before any production deployment.**

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [Oshim Pathan](https://github.com/OshimPathan)**

*For better healthcare communication*

</div>

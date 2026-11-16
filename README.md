# WorkflowGuard: Anomaly Detection in Process Workflows Using Automata and Machine Learning

A dual-paradigm framework for detecting anomalies in business workflows by coupling **Theory of Computation (Deterministic Finite Automata)** with **Machine Learning (Isolation Forest)**.

---

## 1. Project Overview

Modern process workflows (such as online payment processing, order fulfillment, and loan approvals) are vulnerable to both:
1. **Syntactic / Structural Violations**: Out-of-order execution, skipped verification steps, illegal state transitions, and retry count violations.
2. **Behavioral / Temporal Outliers**: Attacks or failures that strictly follow the grammatical state sequence but demonstrate statistically abnormal attributes (e.g. sub-millisecond execution indicative of bot attacks, extreme payment amounts, or sudden execution spikes).

**WorkflowGuard** implements a hybrid architecture:
- **TOC Engine (DFA)**: Provides $O(1)$ formal verification against a mathematically defined transition graph $M = (Q, \Sigma, \delta, q_0, F)$.
- **ML Engine (Isolation Forest)**: Provides continuous unsupervised outlier scoring over multi-dimensional execution telemetry.
- **Hybrid Arbiter**: Combines structural guarantees with statistical insights for complete explainability.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite | Fast, typed, reactive user interface |
| **Styling** | Tailwind CSS | Utility-first responsive design |
| **Workflow Visualization** | React Flow (`@xyflow/react`) | Interactive node-edge workflow graph with real-time state highlighting |
| **Backend Framework** | Python 3.11+, FastAPI | High-performance asynchronous REST API with automatic OpenAPI docs |
| **Automata (TOC)** | Pure Python DFA Engine | Mathematical transition function $\delta(q, a)$ and trace evaluation |
| **Machine Learning** | scikit-learn (Isolation Forest) | Behavioral anomaly detection on continuous telemetry |
| **Data Processing** | Pandas, NumPy | Feature extraction, tabular logs, and vector normalization |
| **Database** | MySQL 8.0+ | Relational persistence for workflows, states, transitions, cases, and logs |
| **ORM & Driver** | SQLAlchemy 2.0 + PyMySQL | Python relational mapping and database connectivity |
| **API Protocol** | REST (JSON payloads) | Client-server communication |

---

## 3. Reference Workflow: Online Payment Processing

### 3.1. States ($Q$)
- `ORDER_CREATED`: Initial checkout state ($q_0$)
- `PAYMENT_INITIATED`: Handoff to payment processor
- `PAYMENT_VERIFYING`: Asynchronous payment gateway settlement check
- `PAYMENT_FAILED`: Payment declined or communication error
- `ORDER_CONFIRMED`: Terminal accept state ($F_{success}$)
- `ORDER_CANCELLED`: Terminal reject/cancelled state ($F_{cancel}$)
- `TRAP_STATE`: Dead-end state entered when an illegal event is attempted

### 3.2. Events Alphabet ($\Sigma$)
- `CREATE_ORDER`
- `INITIATE_PAYMENT`
- `VERIFY_PAYMENT`
- `PAYMENT_SUCCESS`
- `PAYMENT_FAILURE`
- `RETRY_PAYMENT`
- `EXCEED_MAX_RETRIES`
- `CANCEL_ORDER`

### 3.3. Retry Invariants & Rules
- Allowed retries from `PAYMENT_FAILED` back to `PAYMENT_INITIATED`: Maximum **3** attempts.
- If `retry_count >= 3`, the only permissible transition from `PAYMENT_FAILED` is via `EXCEED_MAX_RETRIES` to `ORDER_CANCELLED`.
- Any transition not explicitly listed in the DFA table transitions to `TRAP_STATE` and triggers a **CRITICAL SYNTACTIC ANOMALY**.

For formal mathematical details, see [docs/architecture.md](docs/architecture.md).

---

## 4. Repository Structure

```
WorkflowGuard_Project/
│
├── .env.example                     # Template for environment configuration
├── .gitignore                       # Git exclusion rules for Python & Node
├── README.md                        # Project documentation and guide
│
├── backend/                         # FastAPI Backend
│   ├── requirements.txt             # Python dependencies
│   └── app/
│       ├── api/                     # REST API routers & endpoints
│       ├── core/                    # App configuration, database session
│       ├── engine/                  # DFA engine, Isolation Forest, Hybrid Arbiter
│       ├── models/                  # SQLAlchemy ORM models
│       ├── schemas/                 # Pydantic request/response schemas
│       └── services/                # Business logic and simulation
│
├── database/                        # Database scripts
│   └── schema.sql                   # MySQL DDL schema and initial seed data
│
├── docs/                            # Architectural and technical documentation
│   └── architecture.md              # Detailed architecture, DFA math, and API spec
│
└── frontend/                        # React + TypeScript + Vite + React Flow
    ├── .env.example                 # Frontend environment template
    ├── vite.config.ts               # Vite config with Tailwind plugin
    ├── src/
    │   ├── api/client.ts            # Typed Axios API client
    │   ├── types/index.ts           # TypeScript interfaces mirroring backend schemas
    │   ├── hooks/                   # React custom hooks (useHealth, useWorkflow, useCase)
    │   ├── components/
    │   │   ├── Layout/              # Sidebar, HealthIndicator
    │   │   ├── Workflow/            # React Flow canvas + custom WorkflowNode
    │   │   ├── Simulator/           # Event simulator with bot-speed toggle
    │   │   ├── Anomaly/             # Hybrid DFA+ML analysis inspector
    │   │   ├── History/             # Paginated anomaly log with filters
    │   │   └── Simulation/          # Batch simulation with preset scenarios
    │   └── App.tsx                  # Root component with tab routing
    └── dist/                        # Production build output
```

---

## 5. Software Prerequisites & Manual Setup

Before running the application in subsequent phases, make sure the following software is installed on your Windows system:

### 5.1. Required Software
1. **Python 3.11+** (Python 3.13 is already installed on this machine):
   - Verify: `python --version`
2. **Node.js (v18+) & npm (v9+)** (Node v22 and npm 10 are already installed):
   - Verify: `node --version` and `npm --version`
3. **MySQL Community Server 8.0+**:
   - Download installer: [MySQL Community Downloads](https://dev.mysql.com/downloads/mysql/) or via Chocolatey/Winget:
     ```powershell
     winget install Oracle.MySQL
     ```
   - Make sure the MySQL Windows Service is running and you know your `root` password.
   - (Optional) MySQL Workbench or DBeaver for database browsing.

---

## 6. Windows PowerShell Setup Guide (Phase 0)

Execute these steps in **Windows PowerShell** inside the project root:

### Step 1: Create local environment configuration
```powershell
Copy-Item .env.example .env
```
Open `.env` in a text editor and update `DB_PASSWORD` to your local MySQL root password:
```env
DB_PASSWORD=your_actual_mysql_password
```

### Step 2: Set up MySQL Database & Schema
Open a PowerShell terminal with access to the MySQL client (or via MySQL Command Line Client):
```powershell
mysql -u root -p < database/schema.sql
```
*Note: If `mysql` command is not yet in your PATH, provide the full path to `mysql.exe`, typically located at `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`.*

Verify the created tables:
```powershell
mysql -u root -p -e "USE workflowguard_db; SHOW TABLES;"
```

### Step 3: Setup Backend Python Virtual Environment
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

---

## 7. Phase-Wise Development Roadmap

- [x] **Phase 0: Architecture and Project Setup** *(Current)*
  - System architecture and data flow design.
  - Theory of Computation (DFA) mathematical specification.
  - Machine learning (Isolation Forest) integration design.
  - Complete MySQL schema and initial seed data.
  - Clean directory structure and PowerShell setup guides.
- [x] **Phase 1: Database Models & Backend Foundation**
  - SQLAlchemy 2.0 models for all entities (`Workflow`, `WorkflowState`, `WorkflowTransition`, `ProcessCase`, `EventLog`, `AnomalyResult`).
  - PyMySQL database engine, session management, and configuration via Pydantic Settings.
  - Database migration and verification script.
- [x] **Phase 2: Theory of Computation Core — Python DFA Engine**
  - Pure Python deterministic finite automaton ($M = (Q, \Sigma, \delta, q_0, F)$).
  - Validation of event traces, retry limits, and dead-end trap state transitions.
  - Unit test suite testing valid paths and anomalous traces (sequence skipping, unauthorized loops, retry limit violations).
- [x] **Phase 3: Machine Learning Engine — Isolation Forest**
  - Feature extraction pipeline (duration, amount, retry count, time delta).
  - Synthetic dataset generator for normal transactions and subtle timing/amount anomalies.
  - Isolation Forest training, model persistence (Joblib), and inference wrapper.
- [x] **Phase 4: Hybrid Decision Engine & REST APIs**
  - Hybrid arbitration matrix implementation.
  - Complete FastAPI routers for workflow retrieval, case creation, event processing, and anomaly inspection.
  - Interactive OpenAPI documentation (`/docs`).
- [x] **Phase 5: Frontend Application (React + Vite + React Flow + Tailwind CSS)**
  - Interactive workflow graph visualization using React Flow with custom styled nodes.
  - Real-time active node highlighting, transition tracking, and visual anomaly alerts.
  - Event simulator controls with bot-speed simulation and custom event injection.
  - Anomaly inspector showing DFA + ML hybrid analysis side by side.
  - Paginated anomaly history log with severity and detector-type filters.
  - Batch simulation with preset scenarios (normal, bot-speed, invalid traces, mixed).
- [ ] **Phase 6: End-to-End Integration, Simulation Suite & College Demo Presentation**
  - Pre-built demonstration attack scenarios (skipping payment verification, bot brute-force retries, hung transaction timeouts).
  - Performance benchmarks, verification tests, and project documentation for viva presentation.

---

## 8. Frontend Setup (Phase 5)

### Step 4: Set up Frontend

```powershell
cd frontend

# Install Node.js dependencies
npm install

# Create environment file
Copy-Item .env.example .env

# Start the development server
npm run dev
```

The dashboard runs at **http://localhost:5173** and connects to the backend at **http://localhost:8000**.

### Running the Full Stack

Open two PowerShell terminals:

**Terminal 1 — Backend:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir .
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

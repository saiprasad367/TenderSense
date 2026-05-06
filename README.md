# TenderSense AI — Government of Karnataka e-Procurement Evaluation System

TenderSense AI is a production-grade, multi-agent AI platform designed to automate and harden the government procurement evaluation process. It leverages an orchestrated pipeline of 5 LangGraph-based specialist agents to evaluate bidder submissions against complex tender criteria, complete with real-time external database verification, OCR, fraud detection, and RTI-compliant audit trails.

## Features
- **Multi-Agent Evaluation Pipeline:** Dedicated AI agents for Finance, Technical, Compliance, Validation, and Fraud detection.
- **Live Database Verification:** Real-time cross-referencing of GSTIN and MCA data directly against Government of India databases.
- **Multilingual OCR:** Support for English and Kannada document processing using PaddleOCR and IndicBERT embeddings.
- **Fraud Detection:** Cosine similarity checks via ChromaDB to catch bidder cartels, document tampering, and duplicate project claims.
- **Automated Notifications:** Sends RTI-compliant HTML emails and comprehensive PDF evaluation reports to bidders instantly.

---

## 🛠️ Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase Account
- OpenRouter API Key (for Claude 3 models)

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI Server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start the Vite Dev Server
npm run dev
```

### 4. Environment Variables (`.env`)
You need a `.env` file in **both** the `backend/` and `frontend/` folders.
**Backend (`backend/.env`):**
```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=anthropic/claude-3-haiku

SMTP_EMAIL=your_email@gmail.com
SMTP_APP_PASSWORD=your_google_app_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

---

## 📖 How to Use the System

### For Admins (Procurement Officers)
1. **Upload a Tender:** Go to "Upload Tender". Fill out the tender details and upload the official Tender Notification PDF. The system will automatically extract the mandatory criteria (e.g., minimum turnover, required ISO certificates).
2. **Review Evaluations:** Once bidders apply, the AI automatically evaluates them. Go to the "Review Queue" to see bidders flagged as `Needs Review` (e.g., due to fraud indicators or failed checks).
3. **Approve / Reject:** Manually adjudicate the result. The system will auto-send the email and update the database.

### For Bidders
1. **Submit Bid:** Select an active tender and upload your application packet.
2. **Required Documents:** Depending on the tender, you typically need to upload:
   - **Balance Sheet (Last 3 Years)** for financial evaluation.
   - **GST Certificate & PAN Card** for compliance.
   - **ISO 9001 Certificate** (if applicable).
   - **Project Completion Certificates** for technical evaluation.
   - **Bank Guarantee / EMD**.
3. **Receive Result:** Within minutes, you will receive an automated email from the Government of Karnataka with your AI verdict and a legally-admissible PDF evaluation report.

---

## 🚀 Deployment Guide (Preventing Sleep Mode)

If deploying the Python Backend to **Render.com's Free Tier**, it will automatically go to "sleep" after 15 minutes of inactivity, causing a 50-second delay on the next request.

### The "Always Awake" Solution
You can use a free uptime monitoring service to ping the backend every 10 minutes to keep it awake permanently.

1. Add a `/ping` or `/health` endpoint to your `main.py` (already included in this project if using standard setup).
2. Create a free account at [UptimeRobot](https://uptimerobot.com/) or [Cron-job.org](https://cron-job.org/).
3. Create a new HTTP Monitor/Job.
4. Set the URL to your Render backend URL (e.g., `https://tendersense-api.onrender.com/api/health`).
5. Set the interval to **10 minutes**.
6. The service will hit your backend every 10 mins, preventing Render from ever spinning it down!

### Alternative Deployment
For a production environment, consider deploying the backend on **Fly.io** or upgrading to Render's **$7/mo Starter Plan**, which removes the sleep restriction entirely.

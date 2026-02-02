# 📊 BillAgent Pro - AI Bill Management System

An intelligent, agentic AI-powered bill digitization and analysis system. Automatically extracts, validates, and analyzes bills/invoices using advanced OCR (EasyOCR) and agentic AI workflows.

**Stack:** React 19 + TypeScript + Vite | Python FastAPI | EasyOCR | PyTorch

---

## 🎯 Features

✨ **Smart Bill Digitization**
- High-accuracy OCR using EasyOCR (deep learning-based)
- Supports printed & handwritten bills
- Automatic extraction of items, quantities, and prices

🤖 **Agentic AI Pipeline**
- **Confidence Agent** - OCR quality scoring (0-100%)
- **Error Detection** - Find math/logic errors
- **Workflow Router** - Auto-approve or manual review
- **Learning Module** - Improve accuracy over time

📈 **Dashboard & Analytics**
- Bill history tracking
- OCR confidence metrics
- Error detection reports
- Spending analytics

---

## 🚀 Quick Start (3 Steps)

### Prerequisites
- Node.js v18+
- Python 3.10+

### Step 1: Setup

```bash
git clone https://github.com/yourusername/billagent-pro.git
cd billagent-pro

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 2: Backend (Terminal 1)

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend: http://localhost:8000

### Step 3: Frontend (Terminal 2)

```bash
npm install
npm run dev
```

✅ App: http://localhost:3000

---

## 📋 Project Structure

```
.
├── README.md                      # Documentation
├── package.json                   # Frontend deps
├── backend/requirements.txt       # Python deps
│
├── components/                    # React Components
│   ├── Dashboard.tsx             # Main dashboard
│   ├── BillUpload.tsx            # Upload & analyze
│   ├── BillHistory.tsx           # View bills
│   ├── Analytics.tsx             # Charts
│   ├── Settings.tsx              # Settings
│   └── ...more components
│
├── services/                      # Frontend Services
│   ├── ocrService.ts             # OCR coordination
│   ├── correctionService.ts      # Data fixing
│   └── geminiOCR.ts              # Backup OCR
│
├── backend/                       # Python FastAPI Server
│   ├── main.py                   # API endpoints
│   ├── requirements.txt          # Dependencies
│   │
│   ├── services/                 # OCR & Processing
│   │   ├── paddleocr_service.py  # EasyOCR
│   │   ├── image_preprocessing.py
│   │   ├── layout_detection.py
│   │   └── ocr_service.py
│   │
│   ├── agents/                   # AI Agents
│   │   ├── confidence_agent.py   # Quality scoring
│   │   ├── error_agent.py        # Error detection
│   │   ├── workflow_agent.py     # Routing logic
│   │   └── learning_agent.py     # Learning module
│   │
│   ├── models/                   # Data Models
│   │   ├── bill.py
│   │   └── item.py
│   │
│   └── schemas/                  # API Schemas
│       ├── bill_schema.py
│       └── item_schema.py
│
└── .gitignore
```

---

## 🔧 Configuration

**Optional:** Create `.env.local`:

```env
VITE_GEMINI_API_KEY=your_key_here
VITE_BACKEND_URL=http://localhost:8000
```

---

## 🧠 How It Works

```
Upload Bill Image
      ↓
EasyOCR Extracts Text & Numbers
      ↓
Confidence Agent Scores Quality (0-100%)
      ↓
Error Detection Agent Checks Math
      ↓
Workflow Agent Routes Decision
      ↓
User Reviews & Saves Data
```

---

## 💾 Usage Guide

1. **Login** - Demo mode (any credentials work)
2. **Upload Bill** - Select JPEG/PNG/WebP image
3. **AI Analyzes** - Automatic extraction via EasyOCR
4. **Review Results** - Check extracted items & total
5. **Edit if Needed** - Correct any errors
6. **Save** - Store to localStorage/database

---

## 🐛 Troubleshooting

### Backend won't start
```bash
pip install --force-reinstall -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Connection refused error
- Verify backend is running on port 8000
- Refresh browser page
- Check firewall isn't blocking port

### Low OCR accuracy
- Use clear, well-lit images
- High resolution (300+ DPI)
- Avoid shadows/reflections
- Ensure legible text

### Module not found
```bash
# Frontend
npm install --legacy-peer-deps

# Backend
pip install -r backend/requirements.txt --force-reinstall
```

---

## 📦 Key Dependencies

**Frontend:**
- React 19.2.4 - UI Framework
- TypeScript 5.8 - Type Safety
- Vite 6.2.0 - Build Tool
- Lucide React - Icons
- Recharts - Charts

**Backend:**
- FastAPI 0.128.0 - Web Framework
- EasyOCR 1.7.2 - OCR Engine
- PyTorch 2.10.0 - Deep Learning
- OpenCV - Image Processing
- Pydantic 2.12.5 - Data Validation
- Uvicorn 0.40.0 - ASGI Server

---

## 🚀 Production Deployment

### Build Frontend
```bash
npm run build
```

### Build Backend
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Providers
- AWS EC2 (recommended - t3.medium, 4GB RAM)
- Heroku
- Google Cloud Run
- Azure App Service
- DigitalOcean

---

## 🔐 Security for Production

**Must implement:**
- [ ] JWT Authentication (no localStorage)
- [ ] API keys in environment variables (not frontend)
- [ ] Rate limiting on endpoints
- [ ] HTTPS only
- [ ] Input validation & sanitization
- [ ] Database encryption
- [ ] CORS whitelist (not allow all)
- [ ] Secure headers (CSP, X-Frame-Options, etc)

---

## 📚 API Reference

### POST `/bills/analyze`

Analyzes an uploaded bill image.

**Request:**
```bash
curl -X POST http://localhost:8000/bills/analyze \
  -F "file=@bill.jpg"
```

**Response:**
```json
{
  "items": [
    {
      "name": "Item Name",
      "quantity": 2,
      "unit_price": 100.00,
      "line_total": 200.00,
      "confidence": 92.5
    }
  ],
  "total": 200.00,
  "confidence_scores": {
    "overall": 92.5
  },
  "errors": [],
  "workflow_decision": "AUTO_APPROVE"
}
```

---

## 🧪 Development Guide

### Add Custom Agent
```python
# backend/agents/custom_agent.py
class CustomAgent:
    def analyze(self, items, total):
        # Your logic here
        return {
            "verdict": "OK",
            "reasoning": "Analysis complete",
            "score": 95.0
        }
```

### Add React Component
```tsx
// components/CustomComponent.tsx
import React from 'react';

const CustomComponent: React.FC = () => {
  return (
    <div>
      {/* Component content */}
    </div>
  );
};

export default CustomComponent;
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| OCR Accuracy | 85-95% |
| Processing Time | 2-5 seconds |
| EasyOCR Models | ~500MB |
| Frontend Bundle | ~1.2MB |
| Recommended RAM | 4GB minimum |

---

## 📝 License

MIT License - Free for personal & commercial use

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/name`
3. Commit changes: `git commit -m "Add feature"`
4. Push: `git push origin feature/name`
5. Open Pull Request

---

## 📞 Support

- **Issues:** GitHub Issues tab
- **Discussions:** GitHub Discussions
- **Email:** your-email@example.com

---

## ✅ Pre-GitHub Checklist

Before uploading to GitHub:

- [ ] Remove `.env.local` file (contains API keys)
- [ ] Remove `node_modules/` directory
- [ ] Remove `venv/` directory
- [ ] Remove `dist/` directory
- [ ] Remove `__pycache__/` folders
- [ ] Update `.gitignore` with all above
- [ ] Update repository URL in README
- [ ] Update author/email information
- [ ] Test setup from scratch locally
- [ ] Add LICENSE file if needed
- [ ] Create `.github/` folder with templates (optional)

---

## 🎓 Learning Resources

- [EasyOCR Documentation](https://github.com/JaidedAI/EasyOCR)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev)
- [Agent Design Patterns](https://www.anthropic.com/agents)
- [PyTorch Basics](https://pytorch.org/tutorials/)

---

**Version:** 1.0.0 | **Last Updated:** February 2026

Made with ❤️ by BillAgent Team

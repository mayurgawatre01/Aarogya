# 🌿 Aarogya — AI-Powered Healthcare Platform

> *Aarogya (आरोग्य) — Sanskrit for Health & Wellness*

Aarogya is a full-stack AI-powered healthcare web application that bridges the gap between patients and doctors. Built with Flask and powered by LLaMA AI, it provides smart health tools, appointment management, and real-time medical assistance — all in one place.

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🔐 **Auth System** | Secure login & registration for Patients and Doctors |
| 📅 **Appointment Booking** | Book, view, and cancel appointments with doctors |
| 🤖 **AI Symptom Checker** | LLaMA-powered symptom analysis with PDF report download |
| 💊 **Medicine Reminders** | Set and track daily medicine schedules |
| 📊 **Health Dashboard** | Log and track vitals — BP, Sugar, Weight, SpO2, Heart Rate |
| 🏥 **Nearby Hospitals** | Find hospitals near you with filters (Govt/Private/Emergency) |
| 💬 **AI Doctor Chat** | Chat with an AI doctor for quick health advice |
| 🩺 **Doctor Dashboard** | Doctors can view all appointments and AI pre-consultation summaries |
| 📈 **Appointment Timeline** | Visual timeline of all past and upcoming appointments |
| 📄 **PDF Reports** | Download AI-generated symptom analysis reports |

---

## 🛠️ Tech Stack

- **Backend** — Python, Flask, SQLite
- **Frontend** — HTML, CSS, JavaScript (Vanilla)
- **AI** — LLaMA 3.1 8B via OpenRouter API
- **PDF** — ReportLab
- **Auth** — Werkzeug password hashing, Flask sessions

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/aarogya.git
cd aarogya
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a `.env` file:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 4. Run the app
```bash
python app.py
```

Visit `http://127.0.0.1:5000`

---

## 📁 Project Structure


aarogya/
├── app.py                  # Main Flask application
├── vitacure.db             # SQLite database
├── requirements.txt
├── .env
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── patient.html
│   ├── doctor.html
│   ├── booking.html
│   ├── health_dashboard.html
│   ├── symptom_checker.html
│   ├── history.html
│   ├── reminders.html
│   ├── chat.html
│   └── slots.html
└── static/
    ├── css/
    └── js/


---

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| OPENROUTER_API_KEY | API key from [openrouter.ai](https://openrouter.ai) |

---

## 👨‍💻 Author

**Mayur** — Full Stack Developer  
Built as a placement project showcasing AI integration with healthcare.

---

## 📜 License

MIT License — free to use and modify.

---

> ⚠️ *Aarogya is an AI-assisted tool and does not replace professional medical advice. Always consult a qualified doctor.*

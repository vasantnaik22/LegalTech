VakilAI — Indian AI Legal Advisor

Project Overview

VakilAI is a multilingual AI-powered legal assistant designed for Indian citizens. It provides instant legal guidance across major Indian laws using AI, voice interaction, and document intelligence.
Core Features
•	AI Legal Chat (IPC, CrPC, Consumer Law, Property, Divorce, Cybercrime, RTI)
•	Document Analysis with clause breakdown and risk detection
•	Legal Document Generator (FIR, Complaint, Notice, RTI, Agreements)
•	Case Outcome Predictor
•	Voice-based Legal AI
•	Support for 9+ Indian Languages
•	Advocate Booking Integration

Technology Stack

Frontend: HTML5, CSS3, JavaScript
Backend: Python (FastAPI / Flask)
AI Integration: Gemini API
Architecture: REST-based modular backend

Installation Steps

1.	Clone Repository
git clone https://github.com/yourusername/vakilai.git
2.	Create Virtual Environmentpython -m venv venv
3.	Install Dependenciespip install -r requirements.txt
4.	Configure .env
GEMINI_API_KEY=your_api_key
SECRET_KEY=your_secret_key
5.	Run Serveruvicorn app:app --reload
Security Practices
•	API keys stored securely in .env
•	No secrets exposed to frontend
•	Input validation on document uploads
•	Server-side AI processing

Legal Disclaimer
VakilAI provides general legal guidance for informational purposes only. It does not constitute formal legal advice. Users should consult a licensed advocate for official legal matters.
Author
Developed by  — Shreya TN, Vasant Naik, Veenashree D, Ranjith Kumar KA

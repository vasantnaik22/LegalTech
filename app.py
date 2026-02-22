from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import json
import re

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = "AIzaSyAeFmHqhVJD36s1-KR41MoHeBZTsDMuGS8"
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are VakilAI — India's most trusted AI Legal Advisor, built by four law-tech students.

EXPERTISE: IPC, CrPC, CPC, Consumer Protection Act 2019, Labour Laws (ID Act, PF, ESIC, Gratuity),
Property Law, RERA 2016, Cyber Law (IT Act 2000 + Amendment 2008), Family Law (Hindu Marriage Act,
Muslim Personal Law, Special Marriage Act), RTI Act 2005, Constitution of India.

RESPONSE STYLE:
- Always cite exact law + section (e.g., "Under Section 498A IPC...")
- Give 3-5 concrete, actionable steps the person can take TODAY
- Mention critical time limits / limitation periods
- For criminal matters add: Police: 100 | Women: 1091 | Cyber crime: 1930 | Legal Aid: 15100
- End EVERY response with: "⚠ This is general guidance only. Consult a licensed advocate for official advice."

CRITICAL LANGUAGE RULE:
- You MUST detect and respond in the EXACT language the user writes in
- Hindi message → respond ENTIRELY in Hindi (Devanagari script, not transliteration)
- Kannada message → respond ENTIRELY in Kannada script
- Tamil message → respond ENTIRELY in Tamil script
- Telugu message → respond ENTIRELY in Telugu script
- Marathi message → respond ENTIRELY in Marathi (Devanagari)
- Bengali message → respond ENTIRELY in Bengali script
- Gujarati message → respond ENTIRELY in Gujarati script
- Malayalam message → respond ENTIRELY in Malayalam script
- If a "Please respond in [Language]" instruction is prepended → ALWAYS strictly follow it
- Legal section names (IPC, RTI, RERA etc.) can stay in English within native script responses
- NEVER mix languages. NEVER respond in English when the user wrote in a regional language.

TONE: Like a knowledgeable elder sibling who is a top Indian advocate — warm, precise, practical."""

text_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"temperature": 0.3, "max_output_tokens": 1500},
    system_instruction=SYSTEM_PROMPT
)

vision_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"temperature": 0.25, "max_output_tokens": 2000},
    system_instruction=SYSTEM_PROMPT
)

predictor_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"temperature": 0.2, "max_output_tokens": 1500},
)

docgen_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"temperature": 0.15, "max_output_tokens": 2500},
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "").strip()[:2000]
        history = data.get("history", [])[-12:]
        lang = data.get("lang", "English")
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400

        lang_prefix = f"Please respond in {lang}. "
        if not user_msg.startswith("Please respond in"):
            user_msg = lang_prefix + user_msg

        gemini_history = []
        for m in history:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "assistant": role = "model"
            if role in ("user", "model") and content:
                gemini_history.append({"role": role, "parts": [{"text": content}]})

        session = text_model.start_chat(history=gemini_history)
        response = session.send_message(user_msg)
        return jsonify({"reply": response.text})
    except Exception as e:
        print(f"[CHAT ERROR] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/analyze-document", methods=["POST"])
def analyze_document():
    try:
        data = request.get_json()
        file_data = data.get("fileData", "")
        mime_type = data.get("mimeType", "")
        file_name = data.get("fileName", "document")
        lang = data.get("lang", "English")
        question = data.get("question", "").strip()

        if not file_data or not mime_type:
            return jsonify({"error": "No file data provided"}), 400

        # CRITICAL: Triple-enforce language — document may be in a different language
        lang_enforce = (
            f"IMPORTANT LANGUAGE INSTRUCTION: You MUST respond ENTIRELY in {lang}. "
            f"Do NOT respond in the language of the document. "
            f"Even if the document is written in Hindi, Tamil, Kannada, or any other language, "
            f"your entire response must be in {lang} only. This is mandatory.\n\n"
        )

        if question:
            prompt = (
                f"{lang_enforce}"
                f'The user uploaded "{file_name}" and asks: "{question}"\n'
                f"Analyze this legal document and answer their specific question in {lang}. "
                f"Also provide a brief overall legal assessment with a risk rating (Low/Medium/High). "
                f"Your response must be in {lang}."
            )
        else:
            prompt = (
                f"{lang_enforce}"
                f'Analyze this legal document "{file_name}" thoroughly as a senior Indian advocate.\n\n'
                f"Respond in {lang}. Provide your analysis in the following sections:\n\n"
                f"DOCUMENT TYPE: What kind of legal document is this?\n\n"
                f"KEY PARTIES: Who are the parties involved?\n\n"
                f"IMPORTANT CLAUSES: List the 5 most important clauses or terms.\n\n"
                f"RED FLAGS: Identify any unfair, illegal, or missing clauses under Indian law.\n\n"
                f"LEGAL ASSESSMENT: Which Indian laws apply? Are there any violations?\n\n"
                f"RISK RATING: Rate as Low Risk, Medium Risk, or High Risk with a brief reason.\n\n"
                f"NEXT STEPS: Give 3 to 5 specific actions the person should take now.\n\n"
                f"Cite relevant Indian law sections where applicable. "
                f"Remember: your entire response must be written in {lang}."
            )

        response = vision_model.generate_content(
            [{"mime_type": mime_type, "data": file_data}, prompt]
        )
        return jsonify({"reply": response.text, "type": "document_analysis"})
    except Exception as e:
        print(f"[DOC ERROR] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/predict-outcome", methods=["POST"])
def predict_outcome():
    try:
        data = request.get_json()
        facts = data.get("facts", "").strip()[:3000]
        lang = data.get("lang", "English")
        if not facts:
            return jsonify({"error": "No facts provided"}), 400

        prompt = f"""You are a senior Indian legal expert. Analyze this case and return ONLY valid JSON (no markdown, no code fences, no extra text).

Case Facts: {facts}

Return EXACTLY this JSON:
{{
  "case_type": "Type of legal case",
  "win_probability": 72,
  "strength": "Strong",
  "applicable_laws": ["IPC Section X", "Act Y Section Z"],
  "key_factors_for": ["Supporting factor 1", "Supporting factor 2", "Supporting factor 3"],
  "key_factors_against": ["Weakness 1", "Weakness 2"],
  "recommended_actions": ["Action 1", "Action 2", "Action 3"],
  "time_limit": "X years from date of incident (Limitation Act 1963)",
  "estimated_duration": "X-Y months",
  "court": "Appropriate court/forum",
  "summary": "2-3 sentence plain-language case assessment in {lang}"
}}

win_probability = integer 0-100. strength = one of: Very Strong / Strong / Moderate / Weak / Very Weak.
Base strictly on Indian law. Return ONLY the JSON object."""

        response = predictor_model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
        result = json.loads(text)
        return jsonify({"prediction": result})
    except json.JSONDecodeError as e:
        print(f"[PREDICT JSON ERROR] {e}")
        return jsonify({"error": "Could not parse prediction. Please describe your case more clearly."}), 500
    except Exception as e:
        print(f"[PREDICT ERROR] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/generate-document", methods=["POST"])
def generate_document():
    try:
        data = request.get_json()
        doc_type = data.get("docType", "")
        details = data.get("details", {})
        lang = data.get("lang", "English")
        if not doc_type:
            return jsonify({"error": "No document type"}), 400

        prompts = {
            "rti": _rti_prompt,
            "consumer_complaint": _consumer_prompt,
            "legal_notice": _notice_prompt,
            "rent_agreement": _rent_prompt,
            "bail_application": _bail_prompt,
        }
        fn = prompts.get(doc_type)
        if not fn:
            return jsonify({"error": "Unknown document type"}), 400

        response = docgen_model.generate_content(fn(details, lang))
        return jsonify({"document": response.text, "docType": doc_type})
    except Exception as e:
        print(f"[DOCGEN ERROR] {e}")
        return jsonify({"error": str(e)}), 500


def _rti_prompt(d, lang):
    return f"""Generate a complete, formal RTI application letter in {lang} (English is fine for legal terms).

Applicant: {d.get('name','[Name]')} | Address: {d.get('address','[Address]')}
Department: {d.get('department','[Public Authority]')}
Information Sought: {d.get('info_sought','[Information required]')}
Time Period: {d.get('time_period','Last 3 years')}

Include: date, CPIO salutation, RTI Act 2005 Section 6(1) reference, numbered information points,
certified copies request, Indian citizenship declaration, Rs.10 fee note, 30-day deadline note (Section 7).
Format as a proper ready-to-send formal letter."""


def _consumer_prompt(d, lang):
    return f"""Generate a Consumer Complaint under Consumer Protection Act 2019 in {lang}.

Complainant: {d.get('name','[Name]')} | Address: {d.get('address','[Address]')}
Opposite Party: {d.get('company','[Company]')} | Address: {d.get('company_address','[Address]')}
Product/Service: {d.get('product','[Product]')} | Date: {d.get('purchase_date','[Date]')} | Amount: Rs.{d.get('amount','[Amount]')}
Issue: {d.get('complaint','[Issue]')} | Relief: {d.get('relief','Refund/Replacement/Compensation')}

Include: District Consumer Disputes Redressal Commission heading, jurisdiction statement, numbered facts,
Consumer Protection Act 2019 grounds, Section 39 relief, verification, signature block. Ready to file."""


def _notice_prompt(d, lang):
    return f"""Generate a formal Legal Notice in {lang}.

Sender: {d.get('sender_name','[Sender]')} | Address: {d.get('sender_address','[Address]')}
Recipient: {d.get('recipient_name','[Recipient]')} | Address: {d.get('recipient_address','[Address]')}
Matter: {d.get('matter','[Dispute]')} | Demand: {d.get('demand','[Demand]')}
Amount: {d.get('amount','N/A')} | Reply Deadline: {d.get('deadline','15 days')}

Include: "LEGAL NOTICE" header, applicable Indian law reference, numbered chronological facts,
clear demand, consequences of non-compliance, time limit, "without prejudice" clause, advocate signature."""


def _rent_prompt(d, lang):
    return f"""Generate a Rental Agreement in {lang} compliant with Indian law.

Landlord: {d.get('landlord_name','[Landlord]')} | Tenant: {d.get('tenant_name','[Tenant]')}
Property: {d.get('property','[Address]')} | Rent: Rs.{d.get('rent','[Amount]')}/month
Deposit: Rs.{d.get('deposit','[Amount]')} | Period: {d.get('period','11 months')} | Start: {d.get('start_date','[Date]')}

Include all standard clauses: rent+payment date, deposit terms, lock-in+notice period, permitted use,
maintenance, utilities, restrictions, termination, dispute resolution, registration note (>12 months = mandatory),
witness+signature block. Indian Contract Act 1872 + Transfer of Property Act 1882 compliant."""


def _bail_prompt(d, lang):
    return f"""Generate a Bail Application under CrPC Section 437/439 in {lang}.

Accused: {d.get('accused_name','[Name]')} | FIR No.: {d.get('fir_no','[FIR]')}
Police Station: {d.get('police_station','[PS]')} | Offence: {d.get('offence','[IPC Section]')}
Arrest Date: {d.get('arrest_date','[Date]')} | Court: {d.get('court','[Court Name]')}

Include: court heading, "APPLICATION FOR BAIL U/S 437/439 CrPC", grounds (clean record, no flight risk,
cooperation with investigation), legal arguments with Supreme Court bail jurisprudence, prayer section,
undertaking by accused, advocate signature. Make it persuasive and legally sound."""


if __name__ == "__main__":
    print("\n✅ VakilAI — Full Feature Build Running!")
    print("📋 /chat | /analyze-document | /predict-outcome | /generate-document")
    print("🌐 http://localhost:5000\n")
    app.run(debug=False, port=5000)
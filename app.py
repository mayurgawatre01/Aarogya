from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from dotenv import load_dotenv
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

app = Flask(__name__)
app.secret_key = 'vitacure_secret_key'
DB = 'vitacure.db'

COMMON_SYMPTOMS = [
    "Fever", "Headache", "Cough", "Sore throat", "Fatigue",
    "Nausea", "Vomiting", "Diarrhea", "Chest pain", "Shortness of breath",
    "Body ache", "Runny nose", "Dizziness", "Back pain", "Stomach pain",
    "Loss of appetite", "Chills", "Sweating", "Rash", "Joint pain"
]

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        verified INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        symptoms TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS symptom_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symptoms TEXT NOT NULL,
        result TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

def send_email(to_email, subject, body):
    try:
        EMAIL = os.environ.get("MAIL_EMAIL")
        PASSWORD = os.environ.get("MAIL_PASSWORD")
        if not EMAIL or not PASSWORD:
            return False
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except:
        return False

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            if not user[5]:
                flash('Please verify your email first.')
                return redirect(url_for('verify_otp', email=email))
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4]
            session['user_email'] = user[2]
            if user[4] == 'doctor':
                return redirect(url_for('doctor'))
            return redirect(url_for('patient'))
        flash('Invalid email or password')
    clerk_pub_key = os.environ.get("CLERK_PUBLISHABLE_KEY", "")
    return render_template('login.html', clerk_pub_key=clerk_pub_key)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute('INSERT INTO users (name, email, password, role, verified) VALUES (?, ?, ?, ?, 0)',
                      (name, email, password, role))
            conn.commit()
            conn.close()

            otp = generate_otp()
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute('DELETE FROM otp_store WHERE email = ?', (email,))
            c.execute('INSERT INTO otp_store (email, otp) VALUES (?, ?)', (email, otp))
            conn.commit()
            conn.close()

            body = f"""Hi {name},

Welcome to VitaCure!

Your email verification OTP is: {otp}

This OTP is valid for 10 minutes.

Stay healthy!
VitaCure Team"""
            send_email(email, "VitaCure - Verify Your Email", body)
            flash('OTP sent to your email. Please verify.')
            return redirect(url_for('verify_otp', email=email))
        except sqlite3.IntegrityError:
            flash('Email already registered!')
    clerk_pub_key = os.environ.get("CLERK_PUBLISHABLE_KEY", "")
    return render_template('register.html', clerk_pub_key=clerk_pub_key)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email') or request.form.get('email')
    if request.method == 'POST':
        otp_entered = request.form.get('otp')
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT otp FROM otp_store WHERE email = ? ORDER BY created_at DESC LIMIT 1', (email,))
        record = c.fetchone()
        conn.close()
        if record and record[0] == otp_entered:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute('UPDATE users SET verified = 1 WHERE email = ?', (email,))
            c.execute('DELETE FROM otp_store WHERE email = ?', (email,))
            conn.commit()
            conn.close()
            flash('Email verified! Please login.')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Try again.')
    return render_template('verify_otp.html', email=email)

@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    email = request.form.get('email')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT name FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    if user:
        otp = generate_otp()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('DELETE FROM otp_store WHERE email = ?', (email,))
        c.execute('INSERT INTO otp_store (email, otp) VALUES (?, ?)', (email, otp))
        conn.commit()
        conn.close()
        send_email(email, "VitaCure - New OTP", f"Your new OTP is: {otp}")
        flash('New OTP sent!')
    return redirect(url_for('verify_otp', email=email))

@app.route('/patient')
def patient():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM appointments WHERE patient_id = ?', (session['user_id'],))
    appointments = c.fetchall()
    conn.close()
    return render_template('patient.html', name=session['user_name'], appointments=appointments)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        doctor = request.form['doctor']
        date = request.form['date']
        time = request.form['time']
        symptoms = request.form['symptoms']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('INSERT INTO appointments (patient_id, doctor, date, time, symptoms) VALUES (?, ?, ?, ?, ?)',
                  (session['user_id'], doctor, date, time, symptoms))
        conn.commit()
        conn.close()
        body = f"""Dear {session['user_name']},

Your appointment has been booked!

Doctor: {doctor}
Date: {date}
Time: {time}
Symptoms: {symptoms}

Please arrive 10 minutes early.

VitaCure Team"""
        send_email(session['user_email'], "VitaCure - Appointment Confirmed", body)
        flash('Appointment booked! Confirmation sent to your email.')
        return redirect(url_for('patient'))
    return render_template('booking.html')

@app.route('/cancel/<int:appt_id>', methods=['POST'])
def cancel(appt_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('DELETE FROM appointments WHERE id = ? AND patient_id = ?', (appt_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Appointment cancelled.')
    return redirect(url_for('patient'))

@app.route('/doctor')
def doctor():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT appointments.*, users.name, users.email
                 FROM appointments JOIN users ON appointments.patient_id = users.id
                 ORDER BY appointments.date DESC''')
    appointments = c.fetchall()
    conn.close()
    return render_template('doctor.html', name=session['user_name'], appointments=appointments)

@app.route('/doctor_ai_summary')
def doctor_ai_summary():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT users.name, symptom_history.symptoms, symptom_history.result, symptom_history.created_at
                 FROM symptom_history JOIN users ON symptom_history.user_id = users.id
                 ORDER BY symptom_history.created_at DESC LIMIT 20''')
    records = c.fetchall()
    conn.close()
    summary = None
    if records:
        try:
            all_symptoms = "\n".join([f"Patient {r[0]}: {r[1]}" for r in records])
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": "You are a medical AI helping doctors. Analyze patient symptoms and give a brief summary of common patterns and recommendations."},
                    {"role": "user", "content": f"Recent patient symptoms:\n{all_symptoms}\n\nGive a concise summary for the doctor."}
                ]
            )
            summary = response.choices[0].message.content
        except Exception as e:
            summary = f"AI Summary error: {str(e)}"
    return render_template('doctor_ai_summary.html', records=records, summary=summary, name=session['user_name'])

@app.route('/symptom_checker', methods=['GET', 'POST'])
def symptom_checker():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    result = None
    error = None
    history_id = None
    if request.method == 'POST':
        symptoms = request.form.get('symptoms', '').strip()
        if not symptoms:
            error = "Please enter your symptoms."
        else:
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-3.1-8b-instruct",
                    messages=[
                        {"role": "system", "content": "You are a medical assistant AI for VitaCure. Based on symptoms, give:\n1) Possible Conditions\n2) Advice\n3) Note (consult a doctor)\nKeep it concise."},
                        {"role": "user", "content": f"My symptoms are: {symptoms}"}
                    ]
                )
                result = response.choices[0].message.content
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute('INSERT INTO symptom_history (user_id, symptoms, result) VALUES (?, ?, ?)',
                          (session['user_id'], symptoms, result))
                conn.commit()
                history_id = c.lastrowid
                conn.close()
            except Exception as e:
                error = f"AI service error: {str(e)}"
    return render_template('symptom_checker.html', result=result, error=error,
                           history_id=history_id, symptoms=COMMON_SYMPTOMS)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, symptoms, result, created_at FROM symptom_history WHERE user_id = ? ORDER BY created_at DESC',
              (session['user_id'],))
    records = c.fetchall()
    conn.close()
    return render_template('history.html', records=records)

@app.route('/download_report/<int:record_id>')
def download_report(record_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT symptoms, result, created_at FROM symptom_history WHERE id = ? AND user_id = ?',
              (record_id, session['user_id']))
    record = c.fetchone()
    conn.close()
    if not record:
        flash('Record not found.')
        return redirect(url_for('history'))
    symptoms, result, created_at = record
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("VitaCure - AI Symptom Report", styles['Title']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Patient: {session['user_name']}", styles['Normal']))
    story.append(Paragraph(f"Date: {created_at}", styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Symptoms Reported:", styles['Heading2']))
    story.append(Paragraph(symptoms, styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("AI Analysis:", styles['Heading2']))
    for line in result.split('\n'):
        if line.strip():
            story.append(Paragraph(line.strip(), styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("This report is AI-generated and not a substitute for professional medical advice.", styles['Normal']))
    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=vitacure_report_{record_id}.pdf'
    return response

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/health_dashboard')
def health_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('health_dashboard.html', name=session['user_name'])

@app.route('/reminders')
def reminders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('reminders.html', name=session['user_name'])

@app.route('/api/health_insight', methods=['POST'])
def health_insight():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        vitals = data.get('vitals', {})
        prompt = f"Patient vitals: {vitals}. Give a brief health insight in 2-3 sentences."
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a health AI assistant. Give brief, helpful insights about patient vitals."},
                {"role": "user", "content": prompt}
            ]
        )
        insight = response.choices[0].message.content
        return jsonify({'insight': insight})
    except Exception as e:
        return jsonify({'insight': f'Unable to generate insight: {str(e)}'})

@app.route('/api/nearby_hospitals', methods=['POST'])
def nearby_hospitals():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    hospitals = [
        {"name": "City General Hospital", "distance": "0.8 km", "type": "Multi-specialty", "phone": "1800-VITA-001"},
        {"name": "Apollo Clinic", "distance": "1.2 km", "type": "Clinic", "phone": "1800-VITA-002"},
        {"name": "Care Hospital", "distance": "2.1 km", "type": "Multi-specialty", "phone": "1800-VITA-003"},
        {"name": "LifeLine Medical Center", "distance": "3.4 km", "type": "Emergency", "phone": "1800-VITA-004"},
    ]
    return jsonify({'hospitals': hospitals})

@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        history = data.get('history', [])
        
        if not message:
            return jsonify({'reply': 'Please type a message.'})
            
        messages = [
            {"role": "system", "content": "You are a professional medical assistant AI for ArogyaAI (AI Powered Smart Healthcare Assistant). Based on the symptoms or questions, provide: 1) Guidance/Insights, 2) Lifestyle suggestions, 3) Recommended specialist. Make it very structured and conversational. Add a clear disclaimer warning that this is AI-generated guidance, not a medical diagnosis, and they must consult a doctor or specialist for medical concerns."}
        ]
        
        # Limit history to prevent large context usage
        for msg in history[-10:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=messages
        )
        reply = response.choices[0].message.content
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'reply': f"ArogyaAI assistant error: {str(e)}"})

@app.route('/api/upload_report', methods=['POST'])
def upload_report():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    filename = file.filename
    try:
        content_sample = file.read(2000).decode('utf-8', errors='ignore')
    except Exception:
        content_sample = ""
        
    prompt = f"The patient uploaded a medical report file named '{filename}'. "
    if content_sample:
        prompt += f"Here is the text content parsed from the report:\n{content_sample}\n"
    prompt += "Analyze this medical report details and provide: 1) Executive Summary 2) Key Health Insights 3) Actionable lifestyle or medical advice. Limit formatting, make it extremely professional, clear, and structured."
    
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a health report analyst AI. Analyze the file details and text to provide helpful insights."},
                {"role": "user", "content": prompt}
            ]
        )
        analysis = response.choices[0].message.content
        
        # Save to database symptom_history so patient can see it in history and download PDF
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('INSERT INTO symptom_history (user_id, symptoms, result) VALUES (?, ?, ?)',
                  (session['user_id'], f"Uploaded Medical Report: {filename}", analysis))
        conn.commit()
        history_id = c.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'summary': analysis,
            'history_id': history_id
        })
    except Exception as e:
        return jsonify({'error': f"AI analysis failed: {str(e)}"}), 500

@app.route('/api/doctor_summary', methods=['POST'])
def doctor_summary_api():
    if 'user_id' not in session or session['user_role'] != 'doctor':
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        symptoms = data.get('symptoms', '').strip()
        patient_id = data.get('patient_id')
        
        prompt = f"Summarize symptoms: {symptoms} for patient ID #{patient_id}. Provide key highlights, urgency score (low/medium/high), and suggested questions for the doctor to ask. Keep it structured and under 150 words."
        
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a clinical assistant AI for doctors. Triage the patient symptoms and prepare a professional case briefing."},
                {"role": "user", "content": prompt}
            ]
        )
        summary = response.choices[0].message.content
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'summary': f"AI summarization failed: {str(e)}"})

@app.route('/api/analyze_symptoms', methods=['POST'])
def analyze_symptoms_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        symptoms = data.get('symptoms', '').strip()
        temperature = data.get('temperature', '').strip()
        duration = data.get('duration', '').strip()
        fever = data.get('fever', False)
        body_ache = data.get('body_ache', False)
        vomiting = data.get('vomiting', False)
        age = data.get('age', '').strip()

        if not symptoms:
            return jsonify({'error': 'Symptoms input description is required.'}), 400

        prompt = f"""
Patient Symptom Triage Form:
- Reported Symptoms: {symptoms}
- Patient Age: {age if age else 'Not specified'}
- Measured Temperature: {temperature if temperature else 'Not specified'}
- Duration of Symptoms: {duration if duration else 'Not specified'}
- Accompanying: Fever={fever}, Body Ache={body_ache}, Vomiting={vomiting}

Please analyze this clinical intake. Give a structured response.
Format your output as a raw JSON object (with no markdown code block backticks or leading/trailing text) containing exactly the following keys:
{{
  "summary": "a brief 2-sentence clinical intake summary",
  "possible_causes": "comma-separated list of possible causes (e.g. Viral illness, dehydration, heat exposure)",
  "recommended_specialist": "the specialist type (default to 'General Physician' unless severe/neurological/dermatological symptoms specifically demand another specialist)",
  "confidence": "either 'Low confidence', 'Moderate confidence', or 'High confidence'",
  "urgency_level": "either 'Home care', 'Doctor visit', or 'Emergency'",
  "immediate_care": "bullet points for home care",
  "urgent_care_signs": "red-flag warning signs when to seek immediate emergency care"
}}
"""

        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a professional medical triage AI for ArogyaAI. You analyze patient symptoms and return structured JSON reports. Do not include markdown formatting or backticks around the JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content = "\n".join(lines[1:-1]).strip()

        import json
        result_json = json.loads(content)

        text_result = f"""SUMMARY: {result_json.get('summary')}
POSSIBLE CAUSES: {result_json.get('possible_causes')}
RECOMMENDED SPECIALIST: {result_json.get('recommended_specialist')}
CONFIDENCE: {result_json.get('confidence')}
URGENCY LEVEL: {result_json.get('urgency_level')}
IMMEDIATE CARE: {result_json.get('immediate_care')}
WHEN TO SEEK URGENT CARE: {result_json.get('urgent_care_signs')}"""

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('INSERT INTO symptom_history (user_id, symptoms, result) VALUES (?, ?, ?)',
                  (session['user_id'], symptoms, text_result))
        conn.commit()
        history_id = c.lastrowid
        conn.close()

        result_json['history_id'] = history_id
        return jsonify(result_json)

    except Exception as e:
        return jsonify({'error': f"Clinical triage failed: {str(e)}"}), 500

@app.route('/api/auth/clerk', methods=['POST'])
def auth_clerk_api():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()

        if not email:
            return jsonify({'error': 'Verified email is required.'}), 400

        # Check if user already exists
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()

        if not user:
            # Create user dynamically as a verified patient
            dummy_password = generate_password_hash(string.ascii_letters + string.digits)
            c.execute('INSERT INTO users (name, email, password, role, verified) VALUES (?, ?, ?, ?, 1)',
                      (name if name else email.split('@')[0], email, dummy_password, 'patient'))
            conn.commit()
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = c.fetchone()

        conn.close()

        # Set session details
        session['user_id'] = user[0]
        session['user_name'] = user[1]
        session['user_role'] = user[4]
        session['user_email'] = user[2]

        return jsonify({'success': True, 'redirect': url_for('patient')})
    except Exception as e:
        return jsonify({'error': f"Authentication failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
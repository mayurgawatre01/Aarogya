from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO
import datetime

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

app = Flask(__name__)
app.secret_key = 'vitacure_secret_key'

DB = 'vitacure.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
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
    conn.commit()
    conn.close()

init_db()

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
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4]
            if user[4] == 'doctor':
                return redirect(url_for('doctor'))
            return redirect(url_for('patient'))
        flash('Invalid email or password')
    return render_template('login.html')

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
            c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                      (name, email, password, role))
            conn.commit()
            conn.close()
            flash('Account created! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered!')
    return render_template('register.html')

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
        flash('Appointment booked successfully!')
        return redirect(url_for('patient'))
    return render_template('booking.html')

@app.route('/cancel/<int:appt_id>', methods=['POST'])
def cancel(appt_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('DELETE FROM appointments WHERE id = ? AND patient_id = ?',
              (appt_id, session['user_id']))
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
    c.execute('SELECT * FROM appointments')
    appointments = c.fetchall()
    conn.close()
    return render_template('doctor.html', name=session['user_name'], appointments=appointments)

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
                        {"role": "system", "content": ("You are a medical assistant AI for an app called VitaCure. Based on the symptoms provided, give:\n1) Possible Conditions (not a definite diagnosis)\n2) Advice (general advice/precautions)\n3) Note (recommend consulting a doctor)\n\nKeep it concise and simple.")},
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
    return render_template('symptom_checker.html', result=result, error=error, history_id=history_id)

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
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
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
    story.append(Paragraph("⚠ This report is AI-generated and not a substitute for professional medical advice.", styles['Normal']))
    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=vitacure_report_{record_id}.pdf'
    return response

@app.route('/api/suggest_symptoms', methods=['POST'])
def suggest_symptoms():
    query = request.json.get('query', '')
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "Return exactly 5 symptom suggestions as a JSON array only. Example: [\"headache\",\"fever\"]. No extra text at all."},
                {"role": "user", "content": f"Symptoms related to: {query}"}
            ]
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        suggestions = json.loads(text)
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"suggestions": [], "error": str(e)})

@app.route('/api/doctor_summary', methods=['POST'])
def doctor_summary():
    symptoms = request.json.get('symptoms', '')
    patient_id = request.json.get('patient_id', '')
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a clinical assistant. Give a doctor a 3-line pre-consultation summary: 1) Likely conditions, 2) Urgency level (Low/Medium/High), 3) One key question to ask the patient. Be brief and clinical."},
                {"role": "user", "content": f"Patient ID: {patient_id}. Symptoms: {symptoms}"}
            ]
        )
        return jsonify({"summary": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"summary": f"Error: {str(e)}"})

@app.route('/reminders')
def reminders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('reminders.html', name=session['user_name'])

@app.route('/api/medicine_tip', methods=['POST'])
def medicine_tip():
    medicine = request.json.get('medicine', '')
    dose     = request.json.get('dose', '')
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a pharmacist assistant. Give 2-line practical tip for taking this medicine: best time to take it, food interaction, common side effect to watch for. Be brief and simple."},
                {"role": "user", "content": f"Medicine: {medicine}, Dose: {dose}"}
            ]
        )
        return jsonify({"tip": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"tip": f"Error: {str(e)}"})

@app.route("/slots")
def slots():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("slots.html", name=session["user_name"])

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", name=session["user_name"])

@app.route("/api/chat_reply", methods=["POST"])
def chat_reply():
    data = request.json
    doctor = data.get("doctor", "Doctor")
    specialty = data.get("specialty", "General")
    patient = data.get("patient", "Patient")
    message = data.get("message", "")
    history = data.get("history", [])
    history_text = "\n".join([f"{'Patient' if m['from']=='patient' else doctor}: {m['text']}" for m in history[-6:]])
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": f"You are {doctor}, a {specialty} doctor. Reply warmly and concisely in 2-3 sentences."},
                {"role": "user", "content": f"History:\n{history_text}\n\nPatient: {message}"}
            ]
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": "Unable to respond right now."})

@app.route('/ai_symptom', methods=['POST'])
def ai_symptom():
    data = request.get_json()
    symptoms = data.get('symptoms', '').strip()
    if not symptoms:
        return jsonify({"result": "Please enter symptoms."})
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a medical assistant. Give possible causes, advice and recommendation to consult doctor. Keep concise."},
                {"role": "user", "content": symptoms}
            ]
        )
        return jsonify({"result": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"result": f"Error: {str(e)}"}), 500

@app.route('/health_dashboard')
def health_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM appointments WHERE patient_id = ?', (session['user_id'],))
    appointments = c.fetchall()
    conn.close()
    return render_template('health_dashboard.html', appointments=appointments, name=session['user_name'])

@app.route('/api/health_insight', methods=['POST'])
def health_insight():
    data = request.json
    vitals = data.get('vitals', {})
    total_records = data.get('total_records', 0)
    try:
        vitals_text = f"""
        Blood Pressure: {vitals.get('bp', 'Not recorded')}
        Weight: {vitals.get('weight', 'Not recorded')} kg
        Blood Sugar: {vitals.get('sugar', 'Not recorded')} mg/dL
        Heart Rate: {vitals.get('heart', 'Not recorded')} bpm
        Temperature: {vitals.get('temp', 'Not recorded')} °C
        SpO2: {vitals.get('spo2', 'Not recorded')}%
        Total vitals records: {total_records}
        """
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": "You are a health assistant for VitaCure. Analyze the patient's latest vitals and give a 3-4 line personalized health insight. Mention what looks good, what needs attention, and one simple lifestyle tip. Be encouraging and simple."},
                {"role": "user", "content": f"My latest vitals:\n{vitals_text}"}
            ]
        )
        return jsonify({"insight": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"insight": f"Could not generate insight: {str(e)}"})

@app.route('/api/nearby_hospitals', methods=['POST'])
def nearby_hospitals():
    data = request.json
    location = data.get('location', '')
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return ONLY a valid JSON array of 6 hospitals. No text before or after. No markdown. "
                        "Fields required: name, type (exactly one of: Government/Private/Specialty), "
                        "address (full real address), rating (number), distance (e.g. '2.1 km'), "
                        "phone (real number with country code), hours (e.g. '24/7' or '9AM-6PM'), "
                        "open (boolean), emergency (boolean). "
                        "All hospitals must be within 5km of the given location."
                    )
                },
                {
                    "role": "user",
                    "content": f"Hospitals within 5km of: {location}"
                }
            ],
            max_tokens=1000,
            temperature=0.1
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != 0:
            text = text[start:end]
        hospitals = json.loads(text)
        return jsonify({"hospitals": hospitals})
    except Exception as e:
        return jsonify({"hospitals": [], "error": str(e)})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
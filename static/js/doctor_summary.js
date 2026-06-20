// ── VitaCure Doctor AI Summary ─────────────────────────────────

async function getAISummary(symptoms, patientId, apptId) {
    const box = document.getElementById(`summary-${apptId}`);
    const btn = document.getElementById(`btn-${apptId}`);

    // Show loading state
    btn.disabled = true;
    btn.textContent = '⏳ Loading...';
    box.classList.add('visible');
    box.textContent = 'Generating AI summary...';

    try {
        const res = await fetch('/api/doctor_summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symptoms, patient_id: patientId })
        });
        const data = await res.json();

        box.innerHTML = `<strong>🤖 AI Pre-Consultation Summary</strong><br><br>${data.summary.replace(/\n/g, '<br>')}`;
        btn.textContent = '✅ Done';

    } catch (e) {
        box.textContent = '❌ Could not fetch summary. Check server.';
        btn.disabled = false;
        btn.textContent = '✨ AI Summary';
    }
}

// ── Summarize All appointments ─────────────────────────────────
function summarizeAll() {
    // Find all AI summary buttons and click them
    const allBtns = document.querySelectorAll('.ai-btn');
    allBtns.forEach(btn => {
        if (!btn.disabled) btn.click();
    });
}
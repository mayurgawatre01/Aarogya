// ── VitaCure Symptom Auto-Suggest ──────────────────────────────
let selectedSymptoms = [];
let debounceTimer = null;

const inputField   = document.getElementById('symptom-input-field');
const dropdown     = document.getElementById('suggestDropdown');
const tagsDiv      = document.getElementById('symptomTags');
const hiddenField  = document.getElementById('symptoms');

// ── Typing listener ────────────────────────────────────────────
inputField.addEventListener('input', function () {
    clearTimeout(debounceTimer);
    const val = this.value.trim();

    if (val.length < 3) {
        closeDropdown();
        return;
    }

    showLoading();
    debounceTimer = setTimeout(() => fetchSuggestions(val), 500);
});

// ── Fetch from Flask backend ───────────────────────────────────
async function fetchSuggestions(query) {
    try {
        const res = await fetch('/api/suggest_symptoms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        if (data.suggestions && data.suggestions.length > 0) {
            renderDropdown(data.suggestions);
        } else {
            closeDropdown();
        }
    } catch (e) {
        closeDropdown();
    }
}

// ── Render dropdown items ──────────────────────────────────────
function renderDropdown(suggestions) {
    dropdown.innerHTML = suggestions
        .filter(s => !selectedSymptoms.includes(s))
        .map(s => `<div class="suggest-item" onclick="addSymptom('${s}')">${s}</div>`)
        .join('');

    if (dropdown.innerHTML === '') {
        closeDropdown();
        return;
    }
    dropdown.style.display = 'block';
}

function showLoading() {
    dropdown.innerHTML = '<div class="suggest-loading">⏳ Getting AI suggestions...</div>';
    dropdown.style.display = 'block';
}

function closeDropdown() {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
}

// ── Add symptom tag ────────────────────────────────────────────
function addSymptom(sym) {
    if (selectedSymptoms.includes(sym)) return;
    selectedSymptoms.push(sym);
    inputField.value = '';
    closeDropdown();
    renderTags();
    updateHiddenField();
}

// ── Remove symptom tag ─────────────────────────────────────────
function removeSymptom(sym) {
    selectedSymptoms = selectedSymptoms.filter(s => s !== sym);
    renderTags();
    updateHiddenField();
}

// ── Render tags above input ────────────────────────────────────
function renderTags() {
    tagsDiv.innerHTML = selectedSymptoms
        .map(s => `
            <span class="s-tag">
                ${s}
                <button type="button" onclick="removeSymptom('${s}')" title="Remove">×</button>
            </span>`)
        .join('');
}

// ── Sync tags → hidden textarea (submitted to Flask) ──────────
function updateHiddenField() {
    hiddenField.value = selectedSymptoms.join(', ');
    // Fire input + keyup so booking.js validation re-runs
    hiddenField.dispatchEvent(new Event('input'));
    hiddenField.dispatchEvent(new Event('keyup'));
}

// ── Close dropdown on outside click ───────────────────────────
document.addEventListener('click', function (e) {
    if (!e.target.closest('.symptom-wrapper')) {
        closeDropdown();
    }
});
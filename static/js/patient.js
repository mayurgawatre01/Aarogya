document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('appointments-container');

  // LocalStorage se appointments lo
  const appointments = JSON.parse(localStorage.getItem('appointments')) || [];

  if (appointments.length === 0) {
    container.innerHTML = '<div class="appointment-card"><p>No appointments yet.</p></div>';
  } else {
    container.innerHTML = '';
    appointments.forEach(function (appt, index) {
      const card = document.createElement('div');
      card.className = 'appointment-card';
      card.innerHTML = `
        <p><strong>Doctor:</strong> ${appt.doctor}</p>
        <p><strong>Date:</strong> ${appt.date}</p>
        <p><strong>Time:</strong> ${appt.time}</p>
        <p><strong>Symptoms:</strong> ${appt.symptoms}</p>
        <button onclick="cancelAppointment(${index})">Cancel</button>
      `;
      container.appendChild(card);
    });
  }
});

function cancelAppointment(index) {
  const appointments = JSON.parse(localStorage.getItem('appointments')) || [];
  appointments.splice(index, 1);
  localStorage.setItem('appointments', JSON.stringify(appointments));
  location.reload();
}
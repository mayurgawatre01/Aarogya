window.onload = function () {
  var doctor   = document.getElementById('doctor');
  var date     = document.getElementById('date');
  var time     = document.getElementById('time');
  var symptoms = document.getElementById('symptoms');
  var btn      = document.getElementById('book-btn');

  function check() {
    var ok = doctor.value !== '' && date.value !== '' && time.value !== '' && symptoms.value.trim().length >= 10;
    btn.disabled = !ok;
    btn.style.background = ok ? '#008080' : '#b0c4c4';
    btn.style.cursor = ok ? 'pointer' : 'not-allowed';
  }

  doctor.addEventListener('change', check);
  date.addEventListener('change', check);
  date.addEventListener('input', check);
  time.addEventListener('change', check);
  time.addEventListener('input', check);
  symptoms.addEventListener('input', check);
  symptoms.addEventListener('keyup', check);

  check();
};
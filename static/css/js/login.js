function validateEmail(val) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(val.trim());
}

function validatePassword(val) {
  return val.length >= 8 && /[A-Z]/.test(val) && /[0-9]/.test(val);
}

document.addEventListener('DOMContentLoaded', function () {
  const emailInput = document.getElementById('email');
  const passInput  = document.getElementById('password');
  const emailMsg   = document.getElementById('email-msg');
  const passMsg    = document.getElementById('pass-msg');
  const loginBtn   = document.getElementById('login-btn');

  function checkReady() {
    loginBtn.disabled = !(validateEmail(emailInput.value) && validatePassword(passInput.value));
  }

  emailInput.addEventListener('input', function () {
    const ok = validateEmail(this.value);
    emailMsg.textContent = this.value ? (ok ? '✓ Valid email' : 'Enter a valid email') : '';
    emailMsg.style.color = ok ? 'green' : 'red';
    checkReady();
  });

  passInput.addEventListener('input', function () {
    const ok = validatePassword(this.value);
    passMsg.textContent = this.value ? (ok ? '✓ Strong enough' : 'Min 8 chars, 1 uppercase, 1 number') : '';
    passMsg.style.color = ok ? 'green' : 'red';
    checkReady();
  });
});
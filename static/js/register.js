function validateName(val) {
  return val.trim().length >= 3;
}

function validateEmail(val) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(val.trim());
}

function validatePassword(val) {
  return val.length >= 8 && /[A-Z]/.test(val) && /[0-9]/.test(val);
}

function validateRole(val) {
  return val !== '';
}

document.addEventListener('DOMContentLoaded', function () {
  const nameInput  = document.getElementById('name');
  const emailInput = document.getElementById('email');
  const passInput  = document.getElementById('password');
  const roleInput  = document.getElementById('role');
  const nameMsg    = document.getElementById('name-msg');
  const emailMsg   = document.getElementById('email-msg');
  const passMsg    = document.getElementById('pass-msg');
  const roleMsg    = document.getElementById('role-msg');
  const regBtn     = document.getElementById('register-btn');

  function checkReady() {
    regBtn.disabled = !(
      validateName(nameInput.value) &&
      validateEmail(emailInput.value) &&
      validatePassword(passInput.value) &&
      validateRole(roleInput.value)
    );
  }

  nameInput.addEventListener('input', function () {
    const ok = validateName(this.value);
    nameMsg.textContent = this.value ? (ok ? '✓ Valid name' : 'Min 3 characters required') : '';
    nameMsg.style.color = ok ? 'green' : 'red';
    checkReady();
  });

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

  roleInput.addEventListener('change', function () {
    const ok = validateRole(this.value);
    roleMsg.textContent = ok ? '✓ Role selected' : 'Please select a role';
    roleMsg.style.color = ok ? 'green' : 'red';
    checkReady();
  });
});
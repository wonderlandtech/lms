// Classroom Ledger — shared front-end behaviour

document.addEventListener('DOMContentLoaded', function () {
  initDeadlineCountdowns();
  initSubmissionTypeToggle();
  initConfirmForms();
  initAttendanceQuickFill();
});

/* ---------- Live deadline countdowns ---------- */
function initDeadlineCountdowns() {
  const nodes = document.querySelectorAll('[data-deadline]');
  if (!nodes.length) return;

  function tick() {
    const now = new Date();
    nodes.forEach((node) => {
      const deadline = new Date(node.getAttribute('data-deadline'));
      const diffMs = deadline - now;
      const target = node.querySelector('.countdown-text') || node;

      if (diffMs <= 0) {
        target.textContent = 'Closed';
        node.classList.remove('deadline-open', 'deadline-soon');
        node.classList.add('deadline-closed');
        return;
      }

      const totalHours = diffMs / 36e5;
      const days = Math.floor(totalHours / 24);
      const hours = Math.floor(totalHours % 24);
      const minutes = Math.floor((diffMs / 60000) % 60);

      let label;
      if (days > 0) {
        label = `${days}d ${hours}h left`;
      } else if (hours > 0) {
        label = `${hours}h ${minutes}m left`;
      } else {
        label = `${minutes}m left`;
      }
      target.textContent = label;

      node.classList.remove('deadline-closed');
      if (totalHours <= 24) {
        node.classList.add('deadline-soon');
        node.classList.remove('deadline-open');
      } else {
        node.classList.add('deadline-open');
        node.classList.remove('deadline-soon');
      }
    });
  }

  tick();
  setInterval(tick, 30000);
}

/* ---------- Project submission: group vs individual ---------- */
function initSubmissionTypeToggle() {
  const radios = document.querySelectorAll('input[name="submission_type"]');
  if (!radios.length) return;

  const groupFields = document.getElementById('group-fields');
  const cards = document.querySelectorAll('.group-toggle-card');

  function refresh() {
    const checked = document.querySelector('input[name="submission_type"]:checked');
    const value = checked ? checked.value : null;

    cards.forEach((card) => {
      card.classList.toggle('active', card.getAttribute('data-type') === value);
    });

    if (groupFields) {
      groupFields.classList.toggle('d-none', value !== 'group');
      groupFields.querySelectorAll('[data-required-for-group]').forEach((el) => {
        if (value === 'group') {
          el.setAttribute('required', 'required');
        } else {
          el.removeAttribute('required');
        }
      });
    }
  }

  radios.forEach((r) => r.addEventListener('change', refresh));
  cards.forEach((card) => {
    card.addEventListener('click', () => {
      const input = card.querySelector('input[type="radio"]');
      if (input && !input.disabled) {
        input.checked = true;
        refresh();
      }
    });
  });
  refresh();
}

/* ---------- Confirm before destructive actions ---------- */
function initConfirmForms() {
  document.querySelectorAll('[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (e) => {
      const message = form.getAttribute('data-confirm') || 'Are you sure?';
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });
}

/* ---------- Attendance sheet: mark everyone present/absent at once ---------- */
function initAttendanceQuickFill() {
  document.querySelectorAll('[data-quickfill]').forEach((button) => {
    button.addEventListener('click', () => {
      const status = button.getAttribute('data-quickfill');
      document.querySelectorAll(`input[type="radio"][value="${status}"][data-attendance-radio]`)
        .forEach((radio) => { radio.checked = true; });
    });
  });
}

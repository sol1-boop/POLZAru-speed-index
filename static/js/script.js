// static/js/script.js

// Utility to display a modal, focus the first interactive element
// and close the modal when the Escape key is pressed.
document.addEventListener('DOMContentLoaded', () => {
  window.showModal = function (modal) {
    modal.style.display = 'block';
    const focusable = modal.querySelector(
      'input, button, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable) {
      focusable.focus();
    }
    function escListener(event) {
      if (event.key === 'Escape') {
        modal.style.display = 'none';
        document.removeEventListener('keydown', escListener);
      }
    }
    document.addEventListener('keydown', escListener);
  };
});

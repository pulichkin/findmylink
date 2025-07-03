window.focus();
function closeOnEsc(e) {
  if (e.key === 'Escape') {
    window.close();
  }
}
window.addEventListener('keydown', closeOnEsc);
window.addEventListener('keyup', closeOnEsc); 
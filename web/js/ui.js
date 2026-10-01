/* Small DOM helpers shared by the screens. */

export const $ = (selector) => document.querySelector(selector);

const SCREENS = ['home', 'pick', 'game', 'end'];

export function showScreen(id) {
  SCREENS.forEach((screen) => {
    $('#' + screen).classList.toggle('hide', screen !== id);
  });
}

// Highlights one button in the top bar (or none).
export function setActiveTab(modeName) {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.toggle('on', tab.dataset.mode === modeName);
  });
}

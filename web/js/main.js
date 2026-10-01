/*
  Entry point and screen routing.
  Data comes from data/countries.js (window.COUNTRIES) and data/world.js
  (window.WORLD). Libraries: d3 and topojson-client (see vendor/), loaded
  as classic scripts before this module.
*/
import { $, showScreen, setActiveTab } from './ui.js';
import { normalize } from './answer.js';
import { drawMap } from './map.js';
import * as classic from './modes/classic.js';

let countries = []; // every country: name, flag code, continent, map shape...

/* Loading the data and drawing the map */
function init() {
  try {
    const features = topojson.feature(window.WORLD, window.WORLD.objects.countries).features;

    countries = window.COUNTRIES.map((c) => ({
      code: c.code,
      name: c.name,
      latlng: c.ll,
      continent: c.continent,
      // Match by numeric id first. Fall back to name.
      feature: (c.id && features.find((f) => f.id === c.id))
        || features.find((f) => f.properties.name === c.name),
      // All accepted spellings, already normalized.
      acceptedNames: c.names.map(normalize),
    }));

    drawMap(features);
    classic.setup(countries);
    $('#status').textContent = countries.length + ' countries ready.';
  } catch (error) {
    $('#status').textContent = 'Could not load the game data: ' + error.message;
  }
}

/* Event listeners */
// Mode cards on the home screen and mode buttons in the top bar.
document.querySelectorAll('[data-mode]').forEach((button) => {
  button.onclick = () => {
    if (button.dataset.mode === 'continent') {
      classic.openContinentPicker();
    } else {
      classic.startRound(button.dataset.mode);
    }
  };
});

$('#home-btn').onclick = () => {
  showScreen('home');
  setActiveTab(null);
};

init();

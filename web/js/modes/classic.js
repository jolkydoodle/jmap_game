/*
  The original world-quizz rounds: Country mode, Flag mode and Continent
  mode. Every country is asked once per round, in a fresh random order.
*/
import { $, showScreen, setActiveTab } from '../ui.js';
import { normalize } from '../answer.js';
import { CONTINENTS, showCountryOnMap } from '../map.js';

let countries = [];

let mode; // 'country' (map question) or 'flag' (flag question)
let continent = null; // selected continent, or null for the whole world
let pickerType = 'country'; // what the continent picker will start: map or flags

let queue = []; // shuffled countries for the current round
let index = 0; // position in the queue
let score = 0;
let missed = []; // names of countries answered wrong
let answered = false; // true after the current question was checked

export function openContinentPicker() {
  if (!countries.length) return;

  setActiveTab('continent');

  $('#conts').innerHTML = CONTINENTS.map((name) => {
    const count = countries.filter((c) => c.continent === name).length;
    return `
      <button class="mode cbtn" data-continent="${name}">
        <h2>${name}</h2>
        <span>${count} countries</span>
      </button>`;
  }).join('');

  showScreen('pick');
}

// Starts a new round. `continentName` is optional (omit for the whole world).
export function startRound(newMode, continentName) {
  if (!countries.length) return;

  mode = newMode;
  continent = continentName || null;
  index = 0;
  score = 0;
  missed = [];

  // New random order on every round.
  queue = d3.shuffle(countries.filter((c) => !continent || c.continent === continent));

  setActiveTab(continent ? 'continent' : mode);
  showScreen('game');

  $('#map').classList.toggle('hide', mode !== 'country');
  $('#flagbox').classList.toggle('hide', mode !== 'flag');
  $('#question').textContent = mode === 'country'
    ? 'Which country is highlighted?'
    : 'Which country does this flag belong to?';

  askQuestion();
}

function askQuestion() {
  const current = queue[index];
  answered = false;

  $('#prog').textContent = `${continent || 'World'} · Question ${index + 1} of ${queue.length}`;
  $('#score').textContent = `Correct: ${score}`;
  $('#fb').textContent = '';
  $('#fb').className = '';
  $('#go').textContent = 'Check';
  $('#skip').classList.remove('hide');
  $('#ans').value = '';
  $('#ans').disabled = false;
  $('#ans').focus();

  if (mode === 'flag') {
    $('#flag').src = `flags/${current.code}.svg`;
  } else {
    showCountryOnMap(current, continent);
  }
}

function finishQuestion(correct) {
  const current = queue[index];
  answered = true;

  if (correct) {
    score++;
  } else {
    missed.push(current.name);
  }

  $('#fb').className = correct ? 'ok' : 'bad';
  $('#fb').textContent = correct ? `Correct! ${current.name}` : `It's ${current.name}.`;
  $('#score').textContent = `Correct: ${score}`;
  $('#ans').disabled = true;
  $('#skip').classList.add('hide');
  $('#go').textContent = index + 1 < queue.length ? 'Next' : 'See results';
  $('#go').focus();
}

// "Check" button / Enter key: check the answer, or go on if already checked.
function submitAnswer() {
  if (answered) return nextQuestion();

  const guess = normalize($('#ans').value);
  if (!guess) return;

  finishQuestion(queue[index].acceptedNames.includes(guess));
}

function nextQuestion() {
  index++;
  if (index < queue.length) return askQuestion();
  showResults();
}

function showResults() {
  const kind = mode === 'country' ? 'map' : 'flag';

  $('#final').textContent = `${score} / ${queue.length} correct`;
  $('#finalsub').textContent = `${continent || 'World'} · ${kind} round finished.`;
  $('#chg').classList.toggle('hide', !continent);
  $('#mh').textContent = missed.length ? 'Missed' : 'Perfect round. Nothing missed!';
  $('#missed').innerHTML = missed.map((name) => `<li>${name}</li>`).join('');

  showScreen('end');
}

// Wires up the picker, game and results screens.
export function setup(allCountries) {
  countries = allCountries;

  // Continent picker: Map / Flags switch and the continent buttons.
  $('#seg').onclick = (event) => {
    const button = event.target.closest('[data-type]');
    if (!button) return;

    pickerType = button.dataset.type;
    document.querySelectorAll('#seg button').forEach((b) => {
      b.classList.toggle('on', b === button);
    });
  };

  $('#conts').onclick = (event) => {
    const button = event.target.closest('[data-continent]');
    if (button) startRound(pickerType, button.dataset.continent);
  };

  // Answering
  $('#go').onclick = submitAnswer;
  $('#skip').onclick = () => finishQuestion(false);

  $('#ans').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') submitAnswer();
  });

  // Enter also moves on once the answer is shown (the input is disabled then).
  document.addEventListener('keydown', (event) => {
    const playing = !$('#game').classList.contains('hide');
    if (event.key === 'Enter' && answered && playing) nextQuestion();
  });

  // Results screen
  $('#again').onclick = () => startRound(mode, continent);
  $('#other').onclick = () => startRound(mode === 'country' ? 'flag' : 'country', continent);
  $('#chg').onclick = openContinentPicker;
}

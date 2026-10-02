# Map Game

An offline desktop game for learning the countries of the world and where they are on the map,
with a spaced-repetition memory algorithm (FSRS) deciding what to practise. Work in progress:
see [SPEC.md](SPEC.md) for the plan and milestones.

Forked from [dianabali/world-quizz](https://github.com/dianabali/world-quizz) (MIT), the
[World Quizz](https://world-quizz.vercel.app/) browser game by dianabali. The upstream quiz is
still playable as-is; the sections below describe it.

## Running it (current state)

Needs Python 3.11 or newer.

```
pip install -r requirements.txt
python run.py              # opens the game in its own window
python run.py --browser    # opens it in your default web browser instead (for development)
python run.py --debug      # app window with the web inspector enabled
python run.py --db PATH    # use a different progress database file
```

`run.py` starts a small local server on `127.0.0.1` (port 8765, or the next free one) and waits
until it answers before opening the window. Closing the window quits the app; in `--browser` mode,
press Ctrl+C to stop.

Progress is stored in `progress.db` next to `run.py` (created on first run, not committed).

The app window uses the operating system's built-in web engine through
[pywebview](https://pywebview.flowrl.com/): Edge WebView2 on Windows 10/11 (preinstalled) and
WebKit on macOS. On Linux, pywebview needs a GTK or Qt backend installed; see its documentation.
Linux isn't a supported target, but `--browser` works anywhere.

The page uses ES modules, so it must be served over HTTP; opening `web/index.html` directly from
disk won't work.

Development: `pip install -r requirements-dev.txt`, then `python -m pytest`.

## Table of contents

1. [Running it](#running-it-current-state)
2. [Features](#features)
3. [Game modes](#game-modes)
4. [Project structure](#project-structure)
5. [How it works](#how-it-works)
6. [Customizing](#customizing)
7. [Updating the data](#updating-the-data)
8. [Credits and licenses](#credits-and-licenses)

## Features

- **Three modes:** country (map), flag and continent.
- **196 countries:** the 193 UN member states, Vatican City, Palestine and Kosovo.
- **Random every time:** each round is a fresh shuffle, so no two rounds have the same order.
- **Every country is asked once per round:** there are no repeats and no skipped countries.
- **Typed answers:** answers are forgiving about case, accents, punctuation and common alternative names (see [Answer matching](#answer-matching)).
- **Zoomable map:** scroll or pinch to zoom and drag to pan.
- **Ring marker:** a ring surrounds the target country so tiny countries and islands are easy to find.
- **Results screen:** shows your score and the list of countries you missed.
- **Fully self-contained:** the map data, country list, flags and libraries are all in the project. The app makes no network requests.

## Game modes

### Country mode

A world map is shown with one country highlighted and ringed. Type its name.

### Flag mode

A flag is shown. Type the name of the country it belongs to.

### Continent mode

1. Choose what you want to be asked about: **Map** or **Flags**.
2. Choose a continent. The quiz then covers only the countries of that continent.

In Map questions the view zooms to the chosen continent. If a country lies outside that view (for example Samoa and Tonga, which sit across the date line from the rest of Oceania), the map falls back to the full world view for that question.

| Continent     | Countries |
| ------------- | --------: |
| Africa        |        54 |
| Asia          |        47 |
| Europe        |        46 |
| North America |        23 |
| South America |        12 |
| Oceania       |        14 |

North America includes Central America and the Caribbean. Antarctica has no countries, so it is not a choice. Continent assignment follows the dataset's own region field, so transcontinental countries are placed the way the dataset places them (for example Russia in Europe and Turkey in Asia).

### During a question

- **Check** (or Enter): submits your answer.
- **I don't know:** reveals the answer and counts the question as missed.
- After an answer is shown, **Next** (or Enter) moves on. The last question shows **See results**.
- At the end you can **Play again** (same mode and continent, new order), **Switch mode**, or **Change continent** (continent rounds only).

## Project structure

```
jmap_game/
├── SPEC.md               Build spec and milestones
├── CLAUDE.md             Conventions for Claude Code
├── README.md             This file
├── requirements.txt      Runtime dependencies (fsrs, pywebview)
├── requirements-dev.txt  Dev/build dependencies (pytest, pyinstaller)
├── run.py                Entry point: starts the server, opens the window or browser
├── server/
│   ├── app.py            HTTP server: static files from web/ plus /api routes
│   ├── db.py             SQLite schema and migrations
│   ├── settings.py       Settings defaults, validation, load/save
│   ├── paths.py          Where web/ and progress.db live (source vs. packaged)
│   ├── desktop.py        pywebview app window
│   ├── scheduling.py     FSRS scheduling (Milestone 3; stub for now)
│   └── tests/            pytest suite
├── tools/                Data build script and raw data (Milestone 2)
└── web/                  Everything the browser loads
    ├── index.html        Page structure (all screens)
    ├── css/
    │   └── style.css     All styling and layout
    ├── js/
    │   ├── main.js       Entry point: loads data, draws the map, home screen
    │   ├── ui.js         Small DOM helpers: $, screen switching, active tab
    │   ├── map.js        Map drawing, zoom/pan, highlight, ring, continent views
    │   ├── answer.js     normalize() for typed answers
    │   ├── api.js, distractors.js, geo.js   Stubs for later milestones
    │   └── modes/
    │       └── classic.js   The original Country / Flag / Continent rounds
    ├── data/
    │   ├── countries.js  Country list: names, flag codes, continents, coordinates
    │   └── world.js      World map shapes (TopoJSON)
    ├── flags/            One SVG flag per country, e.g. flags/de.svg
    └── vendor/
        ├── d3.min.js     d3 v7.9.0: map drawing, zoom, shuffle
        └── topojson-client.min.js   topojson-client v3.1.0: converts map data
```

## How it works

### Data flow

`index.html` loads its scripts in this order:

1. `vendor/d3.min.js` and `vendor/topojson-client.min.js`.
2. `data/countries.js`, which defines `window.COUNTRIES`.
3. `data/world.js`, which defines `window.WORLD`.
4. `js/main.js` (an ES module), which uses all of the above and imports the other modules.

On start, `main.js` converts the TopoJSON into map shapes and links each country in the list to its shape.

### Country records

Each entry in `data/countries.js` looks like this:

```js
{
  "code": "de",              // flag file name: flags/de.svg
  "id": "276",               // numeric id used to find the country on the map
  "name": "Germany",         // shown as the correct answer
  "continent": "Europe",
  "ll": [51, 9],             // [latitude, longitude], where the ring is drawn
  "names": ["Germany", "Federal Republic of Germany", "DE", "..."]   // accepted answers
}
```

### Linking a country to its map shape

The map file identifies shapes by numeric id. `main.js` matches on `id` first, and if that fails it matches by name. The name fallback is needed for Kosovo, which has no numeric id on the map. A country with no shape at all (Tuvalu) still works: it is shown as a ring marker only.

### Random order

At the start of each round the countries (filtered by continent if one is chosen) are shuffled with `d3.shuffle` (Fisher-Yates), and the game walks through the shuffled list. Nothing is stored between rounds, so every round is a fresh shuffle.

### Answer matching

Both your input and every accepted name are normalized before comparing:

- lowercased
- accents removed (`Côte d'Ivoire` becomes `cote divoire`)
- `&` becomes `and`
- `St` becomes `Saint`
- punctuation removed
- a leading `the` ignored
- extra spaces collapsed

A guess is correct if it equals any accepted name: the common name, the official name, and the alternative spellings and abbreviations from the dataset. Examples that work: `usa`, `United States`, `uk`, `Czechia`, `Ivory Coast`, `st lucia`.

Matching is exact after normalizing. There is no fuzzy matching, so a typo counts as wrong.

### The map

- Projection: Natural Earth (`d3.geoNaturalEarth1`), drawn into a 960 by 500 SVG.
- The highlighted country gets the `hl` CSS class and is moved to the front.
- The ring is a circle at the country's latitude and longitude. Its radius and stroke are divided by the zoom level so it stays the same size on screen.
- Zoom and pan use `d3.zoom` (1x to 40x, restricted to the map area).
- In continent mode, each continent has a geographic bounding box (`CONTINENT_BOX` in `map.js`) that is converted into a zoom transform.

## Customizing

### Colours

All colours are CSS variables at the top of `web/css/style.css`. There is one block for the light theme and one for dark mode (`prefers-color-scheme: dark`).

| Variable | Used for |
| --- | --- |
| `--bg` | page background |
| `--card` | cards, input, stage background |
| `--tx` | main text and active tab |
| `--mut` | secondary text |
| `--ac` / `--on-ac` | primary button and its text colour |
| `--ok` / `--bad` | correct and wrong feedback |
| `--land` / `--sea` | map land and sea |
| `--hl` | highlighted country |
| `--ring` | ring marker |
| `--line` | borders |

### Fonts

The app uses the operating system's own fonts (a system font stack in `--font-body` and `--font-head` at the top of `web/css/style.css`), so it needs no network access. Upstream loaded Bricolage Grotesque and Inter from Google Fonts; that link was removed to keep the app fully offline.

### Continent view boxes

If a zoomed continent view feels off, adjust its box in `CONTINENT_BOX` in `web/js/map.js`. The format is `[west, south, east, north]` in degrees.

## Updating the data

The bundled files were generated from these npm packages:

| Package | Version | Provides |
| --- | --- | --- |
| `world-atlas` | 2.0.2 | `countries-50m.json`, copied to `web/data/world.js` |
| `world-countries` | 5.1.0 | names, alternative spellings, codes, region, coordinates |
| `flag-icons` | 7.5.0 | `flags/4x3/*.svg`, copied to `web/flags/` |

`web/data/countries.js` was produced from `world-countries` with this logic:

- Keep countries where `independent` is true, plus Palestine (`PS`) and Kosovo (`XK`).
- `code` is `cca2` in lowercase, and `id` is `ccn3`.
- `name` is `name.common`.
- `names` is `name.common`, `name.official` and every `altSpellings` entry longer than 2 characters, without duplicates.
- `ll` is `latlng`.
- `continent` is the `region` field, except that the Americas are split into **South America** (subregion `South America`) and **North America** (everything else).

Then each country's flag is copied from `flag-icons/flags/4x3/<code>.svg` into `web/flags/`.

`web/data/world.js` is `countries-50m.json` wrapped as `window.WORLD = { ... };`. The 50m resolution is used because the lower-resolution files leave out many small countries.

## Credits and licenses

- **Original app:** [world-quizz](https://github.com/dianabali/world-quizz) by dianabali (MIT). This project is a fork of it.
- **Map shapes:** [world-atlas](https://github.com/topojson/world-atlas) (ISC), built from [Natural Earth](https://www.naturalearthdata.com/) data, which is in the public domain.
- **Country data:** [world-countries](https://github.com/mledoze/countries), licensed under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1.0/). If you redistribute the data, keep the attribution.
- **Flags:** [flag-icons](https://github.com/lipis/flag-icons) (MIT).
- **Libraries:** [d3](https://d3js.org/) (ISC) and [topojson-client](https://github.com/topojson/topojson-client) (ISC).
- **Fonts:** none bundled; the app uses system fonts. (Upstream used [Bricolage Grotesque](https://fonts.google.com/specimen/Bricolage+Grotesque) and [Inter](https://fonts.google.com/specimen/Inter) from Google Fonts, both SIL Open Font License.)

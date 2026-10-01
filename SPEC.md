# Map Game — Build Spec

A fully offline, locally run desktop game for learning the countries of the world and where they are on the map, with a spaced-repetition memory algorithm (FSRS) deciding what to practice.

**Starting point:** a fork of [dianabali/world-quizz](https://github.com/dianabali/world-quizz) (MIT). It already provides a zoomable/pannable d3 world map, 196 countries, typed-answer matching, flags, and continent filtering. This spec adds a local Python server with SQLite progress, a memory algorithm, nine game modes, a native app window (pywebview), and finally a double-clickable packaged app (PyInstaller).

**This repository:** [jolkydoodle/jmap_game](https://github.com/jolkydoodle/jmap_game), forked from dianabali/world-quizz and cloned locally as `jmap_game/`. `origin` points to the fork. Keep the upstream credit and "forked from" attribution intact.

---

## 0. Instructions for Claude Code

- Read this whole spec and the upstream `README.md` before writing code.
- Work **one milestone at a time** (Section 9). Each milestone must end in a runnable app and passing tests. Commit at the end of each milestone, then stop and summarize for me before starting the next.
- Keep the stack small:
  - **Frontend:** vanilla JS (ES modules), d3, topojson-client. No framework, no bundler, no build step.
  - **Backend:** Python 3.11+ standard library (`http.server`, `sqlite3`, `json`) plus exactly two runtime dependencies: `fsrs` (py-fsrs, pinned `fsrs==6.3.2`) and `pywebview` (pinned `pywebview==6.2.1`). No Flask.
  - **Build-only:** `pyinstaller` (pinned `pyinstaller==6.22.3`), used only in the final milestone. Not a runtime dependency.
  - **Tests:** `pytest` for the backend.
- The app must make **zero network requests** at runtime. Verify this at the end of each milestone by running with `--browser` and checking the browser's network tab.
- If something in this spec turns out to be wrong or impractical once you see the code, say so and propose an alternative rather than silently deviating.

---

## 1. Decisions already made

| Decision | Choice |
|---|---|
| Where progress lives | Tiny local Python server, SQLite file |
| Offline | Remove the Google Fonts `<link>`; use a system font stack |
| Memory algorithm | FSRS, scheduled server-side with py-fsrs |
| Unit of memory | A **card** = (country, card kind). Each has its own schedule |
| Game modes | All nine in Section 5 |
| App window | Native window via pywebview (default); `--browser` flag for development |
| Packaging | Double-clickable app via PyInstaller, as the final milestone |

---

## 2. Project layout

Restructure the repository root (`jmap_game/`) into:

```
jmap_game/
├── SPEC.md                  this file
├── CLAUDE.md                short conventions file (create in Milestone 0)
├── README.md                updated: how to run, credits/licenses kept from upstream
├── requirements.txt         fsrs==6.3.2, pywebview==6.2.1
├── requirements-dev.txt     pytest, pyinstaller==6.22.3
├── run.py                   entry point: starts server, opens the app window
├── server/
│   ├── app.py               HTTP handler: static files + /api routes
│   ├── db.py                SQLite schema, migrations, queries
│   ├── scheduling.py        FSRS wrapper, outcome→rating mapping, session building
│   ├── settings.py          defaults + load/save
│   ├── paths.py             resolves web/ and the database location (source vs. packaged)
│   ├── desktop.py           pywebview window + native file dialogs (js_api)
│   └── tests/               pytest
├── packaging/               (final milestone)
│   ├── map_game.spec        PyInstaller spec file
│   ├── build.py             one-command build for the current OS
│   └── icon/                icon.png source + generated .ico / .icns
├── tools/
│   ├── build_data.py        regenerates web/data/countries.js from raw data
│   └── raw/                 world-countries countries.json (committed, ODbL)
├── web/
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── main.js          screen routing
│   │   ├── api.js           fetch wrappers for /api
│   │   ├── map.js           shared map: draw, zoom/pan, highlight, ring, fit-to-country
│   │   ├── answer.js        normalize(), matching, typo tolerance
│   │   ├── distractors.js   smart multiple-choice options
│   │   ├── geo.js           distances, centroids, silhouette part filtering
│   │   └── modes/           one file per mode (review.js, identify.js, locate.js, ...)
│   ├── data/                countries.js, world.js
│   ├── flags/
│   └── vendor/              d3, topojson-client
└── progress.db              created at first run when running from source, gitignored
```

The existing `js/app.js` (about 350 lines) gets split into the modules above. Preserve its map drawing, zoom/pan, ring marker, and `normalize()` logic; they work.

**All file paths go through `server/paths.py`.** Never build paths from the current working directory. This matters in the final milestone, when the web files live inside a read-only app bundle and the database must live elsewhere.

---

## 3. Running it

```
pip install -r requirements.txt
python run.py              # opens the app in its own window
python run.py --browser    # opens it in the default web browser instead (for development)
python run.py --debug      # app window with the web inspector enabled
```

### 3.1 Server
- Binds to `127.0.0.1` only, never `0.0.0.0`. Default port 8765; if it's in use, try the next few ports.
- Runs in a **daemon thread**, so closing the app window ends the whole process.
- `run.py` waits until `/api/health` responds before opening the window or browser, so the user never sees a "can't connect" page.

### 3.2 App window (default)
- `server/desktop.py` opens the UI with `webview.create_window(...)` then `webview.start(...)`:
  - Title "Map Game", sensible default size (e.g., 1280×800), a minimum size so the map stays usable (e.g., 900×600), resizable.
  - `--debug` passes `debug=True` to `webview.start` to enable the inspector.
- pywebview uses the operating system's built-in web engine: Edge WebView2 on Windows (preinstalled on Windows 10/11), WebKit on macOS. On Linux it needs a GTK or Qt backend; document that in the README but don't spend effort on Linux.
- **Native file dialogs.** Browser-style downloads and file inputs are unreliable inside an embedded web view, so export/import must not depend on them in window mode:
  - Expose a small `js_api` object from Python with `export_progress()` and `import_progress()`. These open native save/open dialogs (`window.create_file_dialog`), then read/write the JSON file directly through the same functions the `/api/export` and `/api/import` endpoints use.
  - The frontend detects window mode (`window.pywebview` exists) and calls the `js_api`; in `--browser` mode it falls back to a normal download / file input.
- Remember the window's last size and position in `settings` (nice to have; skip if it fights the platform).

### 3.3 Browser mode (`--browser`)
- Opens the default browser with `webbrowser.open`. Ctrl+C shuts down cleanly.
- This exists for development: browser dev tools and the network tab are easier to work with than the embedded inspector.

### 3.4 Where progress is stored
- **Running from source:** `progress.db` next to `run.py` (easy to inspect while developing).
- **Packaged app (final milestone):** the per-user data folder: `%APPDATA%\MapGame\progress.db` on Windows, `~/Library/Application Support/MapGame/progress.db` on macOS. Never inside the app bundle, so rebuilding or replacing the app doesn't touch progress.
- `--db PATH` overrides either.

---

## 4. Data

### 4.1 Rebuild `countries.js` with more fields

The current `data/countries.js` has `code, id, name, continent, ll, names`. Several modes need more. Write `tools/build_data.py` to regenerate it from the `world-countries` 5.1.0 `countries.json` (same source upstream used; commit the raw file under `tools/raw/`). Keep upstream's filtering rules: `independent == true`, plus Palestine (`PS`) and Kosovo (`XK`). Result: 196 countries.

Add these fields to each record:

| Field | Source | Used by |
|---|---|---|
| `cca3` | `cca3` | joining borders |
| `capital` | `capital` (list) | Capital mode; accept any listed capital |
| `capitalNames` | capital + common alternate spellings, if any | answer matching |
| `borders` | `borders`, converted from cca3 to our `code` | Neighbors mode, distractors |
| `area` | `area` | ordering new cards (bigger first) |
| `subregion` | `subregion` | distractors, Explore info card |

Notes:
- `borders` in this dataset covers land borders of the main territory only (France borders Spain, Belgium, etc., not Brazil). That's the behavior we want.
- Countries with empty `borders` (island nations) are excluded from Neighbors mode.
- `build_data.py` should print a summary and fail loudly on mismatches: total count, countries missing a map shape, borders that point to a country not in our list (drop those, but list them).

### 4.2 Map data

Keep `world.js` (Natural Earth 1:50m via world-atlas). Known quirks to handle:
- Tuvalu has no shape. It works today as a ring-only marker; keep that, and in click-based modes accept a click within the ring.
- Some countries' shapes include far-flung territories (e.g., France's shape may include overseas parts). Silhouette mode must handle this (Section 5.6).

---

## 5. Game modes

There are two families:

- **Card kinds** are scheduled by FSRS. Every answer writes a review and moves the card's due date.
- **Practice modes** are free play. They log attempts and mix-ups for stats, but **do not change the FSRS schedule**. (Reason: FSRS assumes reviews happen when it schedules them; unscheduled extra reviews distort its estimates. If this proves annoying in use, revisit.)

### Card kinds (scheduled)

#### 5.1 Identify — highlighted country → name
- The map shows one country highlighted and ringed, zoomed so its neighbors are visible (reuse upstream's view logic).
- **Two stages, chosen automatically by the card's FSRS stability:**
  - Stability < `mc_graduation_days` (default 3): **multiple choice**, 4 options (Section 6).
  - Otherwise: **typed answer**.
- The user can always pan and zoom while answering.

#### 5.2 Locate — name → click the country
- Show a country name; the user clicks on the map.
- Correct if the click lands inside the country's shape, or within the ring for tiny/shapeless countries.
- Wrong click: flash the clicked country's name, then reveal the correct one, then record a mix-up (Section 7).
- Map starts at the world view (or the continent view if a continent filter is active), so finding it is part of the task.

#### 5.3 Neighbors — click all bordering countries
- Highlight a country; the user clicks each country that borders it, then presses **Done**.
- Correct clicks turn green; wrong clicks turn red (and are not mix-ups; they're just wrong).
- On Done, reveal any missed neighbors.
- Only for countries with a non-empty `borders` list.
- **Unlocks** per country once its Identify card's stability ≥ `unlock_days` (default 7). Same for 5.4–5.6.

#### 5.4 Capital — country → capital
- Show the country highlighted on the map with its name. Answer the capital.
- MC → typed staging, same as Identify. Accept any capital in `capitalNames`.

#### 5.5 Flag — flag → country name
- Show the flag only. MC → typed staging. After answering, show the country on the map.

#### 5.6 Silhouette — outline alone → country name
- Draw only that country's shape, filling the frame (`projection.fitExtent`), no map around it, no labels.
- Drop polygon parts that are far from the main body: keep the largest polygon plus any part whose centroid is within 1,500 km of it. (Otherwise France shows up as France plus specks in the Caribbean and Indian Ocean.)
- Use a local projection centered on the country (e.g., `d3.geoAzimuthalEqualArea().rotate([-lon, -lat])`) so high-latitude countries aren't distorted.
- MC → typed staging. After answering, show it in place on the world map.

### Practice modes (not scheduled)

#### 5.7 Blank-map sweep
- Pick a continent (or the world). Map has no labels.
- Prompts each country in that region in random order; the user clicks it. Up to 3 tries per country; after the third miss, reveal it in red.
- Found countries stay colored (green on first try, yellow after retries, red if revealed).
- Timer runs throughout. Results: time, accuracy, list of misses. Store best times per region.

#### 5.8 Pin drop
- Show a country name; the user clicks where they think it is.
- Score by distance: 0 km if inside the country; otherwise great-circle distance from the click to the nearest point of the country's outline (nearest vertex is accurate enough).
- Show a line from the click to the country with the distance labeled.
- A round is 10 countries; total score is shown at the end. Points per question: `max(0, 1000 − km/2)`, rounded.

#### 5.9 Explore
- No questions. Hover shows the country name; click opens an info card: name, flag, capital, subregion, neighbors (clickable to jump), and the user's status on each card kind (new / learning / due date / retrievability).

#### 5.10 Mix-up drill
- Lists the user's most frequent confusion pairs (Section 7).
- Drill: alternating Identify-style questions between the two countries in a pair, shown side by side on the map after each answer so the difference sticks.

### Daily review (the main screen)

- One mixed session pulling **due cards across all card kinds**, plus new cards up to the daily limit.
- Due cards are served in due-date order, interleaving kinds so the session doesn't do 20 Locate cards in a row.
- FSRS's short learning steps (1 min, 10 min) mean failed cards come back later in the same session. The client re-requests the queue after each answer, rather than holding a fixed list.
- Show remaining count and a progress bar. End screen summarizes: reviewed, accuracy, new cards learned, next due time.
- Optional filter: limit the session to one continent.

---

## 6. Smart multiple choice

`distractors.js` builds 3 wrong options for a target country. Pick in this priority, skipping duplicates:

1. Countries the user has previously confused with the target (from mix-ups, either direction).
2. Bordering countries.
3. Nearest countries by centroid distance.
4. Same subregion.

Shuffle the final 4 options. For Capital mode, the options are the capitals of those distractor countries.

---

## 7. Answer handling, mix-ups, and ratings

### 7.1 Typed answers
- Keep upstream's `normalize()` and accepted-names matching.
- Add typo tolerance: if no exact match, but the normalized input is within edit distance 1 of an accepted name (and the name is ≥ 6 characters), count it as **correct with typo**.
- If the input exactly matches a **different** country's accepted name, it's wrong **and** a mix-up.

### 7.2 Mix-ups
Record a mix-up `(target, given)` whenever the user answers with a different real country: a wrong MC option, a typed name of another country, or a click on another country in Locate/sweep/pin drop. Store counts per ordered pair.

### 7.3 Outcome → FSRS rating
The **client sends the raw outcome; the server maps it to a rating.** Keeping this mapping in Python means it lives in one place and is unit-tested.

Outcome payload:
```json
{
  "card_id": 123,
  "correct": true,
  "stage": "mc" | "typed" | "click" | "neighbors",
  "typo": false,
  "revealed": false,
  "response_ms": 4200,
  "neighbors_found": 3, "neighbors_total": 4, "neighbors_wrong": 0,
  "given": "sk"
}
```

Mapping (thresholds live in settings):

| Situation | Rating |
|---|---|
| Wrong, or user pressed "I don't know" | Again |
| Correct with typo | Hard |
| Correct, slow (response_ms > `slow_ms`, default 15 s) | Hard |
| Correct typed, fast (response_ms < `fast_ms`, default 3 s) | Easy |
| Any other correct | Good |
| Neighbors: all found, no wrong clicks | Good (Easy if fast) |
| Neighbors: ≥ 75% found, ≤ 1 wrong | Hard |
| Neighbors: otherwise | Again |

MC correct answers never get Easy.

---

## 8. Backend

### 8.1 SQLite schema

```sql
CREATE TABLE cards (
  id            INTEGER PRIMARY KEY,
  country       TEXT NOT NULL,       -- country code, e.g. 'de'
  kind          TEXT NOT NULL,       -- identify|locate|neighbors|capital|flag|silhouette
  fsrs          TEXT NOT NULL,       -- JSON from fsrs Card.to_dict()
  due           TEXT NOT NULL,       -- ISO UTC, denormalized for queries
  stability     REAL,                -- denormalized for gating/staging
  state         INTEGER,             -- denormalized FSRS state
  introduced_at TEXT NOT NULL,
  UNIQUE(country, kind)
);
CREATE INDEX idx_cards_due ON cards(due);

CREATE TABLE reviews (
  id          INTEGER PRIMARY KEY,
  card_id     INTEGER NOT NULL REFERENCES cards(id),
  ts          TEXT NOT NULL,
  rating      INTEGER NOT NULL,
  outcome     TEXT NOT NULL,         -- raw outcome JSON
  review_log  TEXT NOT NULL          -- JSON from fsrs ReviewLog
);

CREATE TABLE attempts (              -- practice modes
  id       INTEGER PRIMARY KEY,
  ts       TEXT NOT NULL,
  mode     TEXT NOT NULL,            -- sweep|pindrop|drill
  country  TEXT NOT NULL,
  correct  INTEGER NOT NULL,
  detail   TEXT                      -- JSON (km, tries, ...)
);

CREATE TABLE mixups (
  target   TEXT NOT NULL,
  given    TEXT NOT NULL,
  count    INTEGER NOT NULL DEFAULT 1,
  last_ts  TEXT NOT NULL,
  PRIMARY KEY (target, given)
);

CREATE TABLE sweeps (
  id        INTEGER PRIMARY KEY,
  ts        TEXT NOT NULL,
  region    TEXT NOT NULL,
  seconds   REAL NOT NULL,
  mistakes  INTEGER NOT NULL
);

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);  -- schema_version
```

Store the full FSRS card as JSON and use the denormalized columns only for querying. Include a simple `schema_version` migration mechanism from the start.

### 8.2 Scheduling (`scheduling.py`)

- Use `fsrs.Scheduler(desired_retention=settings.desired_retention)`; default 0.90. Keep fuzzing on.
- `review(card_id, outcome, now)` → map outcome to rating, call `scheduler.review_card`, save card + review log + mix-up if any, return the updated card summary.
- **Introducing new cards:**
  - Each day, introduce up to `new_countries_per_day` (default 8) new countries. Introducing a country creates its **Identify** and **Locate** cards.
  - Order: by continent filter if set, then **largest area first** (big, central countries become landmarks for placing small ones later).
  - Neighbors/Capital/Flag/Silhouette cards are created automatically once that country's Identify stability ≥ `unlock_days`, and these don't count against the daily new limit.
  - "Today" uses local time with a day boundary at 4 a.m. (setting).
- `session(continent=None)` → returns the next card to show plus counts (due now, new remaining today, total today). For each card, include the **stage** (MC or typed), decided by stability vs `mc_graduation_days`.
- Retrievability for the stats map: `scheduler.get_card_retrievability(card, now)`.

### 8.3 API

All JSON. All under `/api`. Everything else is served as static files from `web/`.

| Method & path | Purpose |
|---|---|
| `GET /api/health` | `{ok: true, version}` |
| `GET /api/next?continent=` | next card in today's session (or `{done: true}` with next due time) |
| `POST /api/review` | outcome payload → updated card |
| `POST /api/attempt` | practice-mode attempt (+ mix-up if any) |
| `POST /api/sweep` | sweep result |
| `GET /api/mixups?limit=` | top confusion pairs |
| `GET /api/stats` | per-card-kind counts, reviews per day, retrievability per country per kind |
| `GET /api/country/<code>` | per-kind status for Explore's info card |
| `GET/POST /api/settings` | read/update settings |
| `GET /api/export` | full JSON backup of all tables |
| `POST /api/import` | restore from that JSON (asks for confirmation in the UI first) |

Validate inputs; return clear 400 errors. Use a single SQLite connection per request with `PRAGMA journal_mode=WAL`.

### 8.4 Settings (defaults)

| Key | Default |
|---|---|
| `desired_retention` | 0.90 |
| `new_countries_per_day` | 8 |
| `mc_graduation_days` | 3 |
| `unlock_days` | 7 |
| `fast_ms` / `slow_ms` | 3000 / 15000 |
| `day_starts_hour` | 4 |
| `enabled_kinds` | all six |

All editable on a Settings screen.

### 8.5 Tests (pytest)
At minimum:
- Outcome → rating mapping, every row of the table in 7.3.
- New-card introduction: daily limit, area ordering, continent filter, day boundary.
- Unlock gating at `unlock_days`.
- MC vs typed stage selection.
- Mix-up recording from reviews and attempts.
- Export → import round trip yields identical data.
- Use a temp database and a fixed "now" so tests are deterministic.

---

## 9. Milestones

Each milestone ends runnable, tested, and committed. Stop after each and summarize.

**M0 — Fork cleanup.** Restructure into the layout above (backend can be stubs). Remove the Google Fonts `<link>`; switch CSS to a system font stack. Confirm the existing quiz still works when served by `python -m http.server` from `web/`. Write `CLAUDE.md` summarizing the conventions from Section 0. Update `.gitignore` (`progress.db`, `__pycache__`, `.venv`, `build/`, `dist/`).
*Done when:* the original quiz works unchanged, with zero network requests.

**M1 — Server skeleton + app window.** `run.py` with `--browser`, `--debug`, `--db`; `server/paths.py`; static file serving; `/api/health`; schema creation; settings load/save; migrations scaffold; `server/desktop.py` opening the pywebview window.
*Done when:* `python run.py` opens the working quiz in its own window, and closing the window exits the process; `python run.py --browser` opens it in the browser; `progress.db` is created; tests run.

**M2 — Data build.** `tools/build_data.py` produces the enriched `countries.js`.
*Done when:* 196 countries, every field in 4.1 present, mismatch report printed and reviewed, existing quiz still works.

**M3 — Scheduling core.** `scheduling.py`, `/api/next`, `/api/review`, settings integration, full test suite from 8.5.
*Done when:* all tests pass; a scripted run of reviews through the API produces sensible due dates.

**M4 — Daily review: Identify + Locate.** Main screen, session flow, MC→typed staging, typo tolerance, re-queuing of failed cards, end-of-session summary. Progress survives restarting the server.
*Done when:* I can do a real session, quit, restart, and see correct due cards.

**M5 — Smart MC + mix-ups.** `distractors.js`, mix-up recording everywhere, Mix-up drill mode.
*Done when:* distractors visibly come from neighbors/past confusions; drill works.

**M6 — Remaining card kinds.** Neighbors, Capital, Flag, Silhouette, with unlock gating.
*Done when:* each works in the daily review once unlocked; silhouettes look right for France, Russia, the US, Chile, Indonesia, and Kiribati.

**M7 — Practice modes.** Blank-map sweep, Pin drop, Explore.
*Done when:* all three work and log to the database; sweep best times persist.

**M8 — Stats, settings, backup.** Stats screen with a **mastery map** (world map colored by retrievability, selectable per card kind; gray for not yet introduced), reviews-per-day chart, counts by state. Settings screen. Export/import, using native file dialogs in the app window and download/upload in `--browser` mode (Section 3.2).
*Done when:* stats match the database; export → wipe → import restores everything, in both the app window and browser mode.

**M9 — Double-clickable app.** Package with PyInstaller for the OS Claude Code is running on (PyInstaller can't cross-build; Windows and macOS are each built on their own machine).
- **One-folder build, windowed** (no console window). Avoid one-file mode: it unpacks to a temp folder on every launch, which is slow.
- A committed `packaging/map_game.spec` that bundles `web/` as data; `server/paths.py` finds it via `sys._MEIPASS` when frozen.
- Database in the per-user data folder (Section 3.4), created on first launch.
- An original, simple app icon (e.g., a stylized globe; not a copy of any existing logo or brand). Keep a source `icon.png` and generate `.ico` (Windows) and `.icns` (macOS) from it.
- `python packaging/build.py` runs the whole build and prints where the app ended up (`dist/MapGame/MapGame.exe` on Windows, `dist/MapGame.app` on macOS).
- README section: how to build, where progress is stored, and the first-launch security prompt. The app is unsigned, so Windows SmartScreen shows "More info → Run anyway", and macOS requires right-click → Open the first time.

*Done when:* double-clicking the app opens the game with no terminal; it works with Wi-Fi turned off; progress persists across quitting, relaunching, **and rebuilding** the app; `python run.py` from source still works.

---

## 10. Out of scope (for now)

- Sub-national maps (US states, provinces).
- Overseas territories and dependencies (only the 196 countries).
- Accounts, sync, or any network features.
- Mobile layout polish (laptop/desktop window first).
- FSRS parameter optimization from review history (py-fsrs supports it; maybe later).
- Code signing, macOS notarization, installers (.msi / .dmg), and auto-updates.
- Linux packaging.

---

## 11. Credits and licenses

Keep upstream's credits section in the README and add:
- Original app: world-quizz by dianabali (MIT).
- Map shapes: world-atlas (ISC), from Natural Earth (public domain).
- Country data: world-countries (ODbL 1.0). Keep attribution.
- Flags: flag-icons (MIT).
- Scheduling: py-fsrs (MIT).
- App window: pywebview (BSD-3-Clause).
- Packaging: PyInstaller (GPL-2.0 with a bootloader exception that permits bundling apps under any license).

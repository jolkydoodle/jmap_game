# CLAUDE.md

Map Game: an offline desktop game for learning the world's countries, with FSRS spaced repetition.
Forked from dianabali/world-quizz (MIT); keep the upstream credit and "forked from" attribution.
`SPEC.md` is the source of truth. Read it before working.

## Workflow
- Work one milestone at a time (SPEC Section 9). Each ends runnable, with passing tests, and committed.
  Then stop and summarize before starting the next.
- If the spec looks wrong or impractical, say so and propose an alternative. Don't silently deviate.

## Stack (keep it small)
- Frontend: vanilla JS ES modules, d3, topojson-client, under `web/`. No framework, bundler or build step.
- Backend: Python 3.11+ stdlib (`http.server`, `sqlite3`, `json`) under `server/`. No Flask.
- Runtime deps, exactly two: `fsrs==6.3.2`, `pywebview==6.2.1` (`requirements.txt`).
- Build/dev only: `pytest`, `pyinstaller==6.22.3` (`requirements-dev.txt`).

## Rules
- Zero network requests at runtime. No CDNs, web fonts or remote URLs. Verify with `--browser` and the network tab.
- All file paths go through `server/paths.py`. Never build paths from the current working directory.
- Server binds to `127.0.0.1` only.
- The client sends raw outcomes; the server maps them to FSRS ratings.
- Practice modes never change the FSRS schedule.

## Commands
- Tests: `python -m pytest`
- Serve the frontend alone: `python -m http.server --directory web`
- App (from Milestone 1): `python run.py` / `--browser` / `--debug` / `--db PATH`

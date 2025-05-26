# Repo Agent Instructions

## Code Style
- Follow PEP8 with 4-space indentation.
- Document public functions and classes with concise docstrings.
- Prefer standard library modules over external dependencies when possible.

## Files to avoid committing
- `domain.json`, `config.json` and everything under `history_files/` are local data and must not be committed.

## Testing
- Run `pytest` before committing.
- Add or update unit tests in `tests/` for any new functionality.

## Pull Request
- The PR description must contain **Summary** and **Testing** sections explaining the changes and test results.

## Architecture
- The main application logic resides in `webapp.py`, `alerts_api.py` and the modules under `modules/`.
- For more details on request handling, see [docs/request-flow.md](docs/request-flow.md).

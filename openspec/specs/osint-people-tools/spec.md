## Requirements

### Requirement: Sherlock username search callable
The system SHALL provide a `sherlock_search` Python callable in `osint/osint.py` that searches for accounts matching a username across 400+ platforms using the `sherlock-project` library. The callable SHALL be referenced by `osint/people.yaml` (group: `people`).

#### Scenario: Username found on multiple platforms
- **WHEN** `sherlock_search` is called with `username="johnsmith"`
- **THEN** the callable returns a dict mapping platform names to profile URLs for all found accounts

#### Scenario: Username not found
- **WHEN** `sherlock_search` is called with a username that has no matches
- **THEN** the callable returns an empty dict

#### Scenario: Missing optional dep
- **WHEN** `sherlock_search` is called but `sherlock-project` is not installed
- **THEN** the callable raises `ImportError` with a message directing the user to `pip install mcc[osint]`

### Requirement: osint[people] package extra
The system SHALL declare a `mcc[osint]` optional dependency group in `pyproject.toml` that includes `sherlock-project` so users can install people-search support with `pip install mcc[osint]`.

#### Scenario: Install osint extra
- **WHEN** a user runs `pip install mcc[osint]`
- **THEN** `sherlock-project` and `gdeltdoc` are installed as dependencies

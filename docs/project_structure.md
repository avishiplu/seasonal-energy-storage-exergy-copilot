# Project File Structure Overview

This document describes the structure of the Seasonal Energy Storage Exergy Copilot project.

## Root level
- src/        : Application source code
- tests/      : Automated tests (pytest)
- docs/       : Project documentation
- data/       : Input data, caches, indices

## src/core
Core domain logic and safety rules.
- values.py            : ValueSpec, source tagging
- refusal.py           : RefusalError definitions
- guardrails.py        : Physics and boundary guards
- scenario.py          : Scenario definition and validation
- science_config.py    : Frozen scientific configuration

## src/tools
Deterministic calculation tools (NO agent logic).
- exergy_core.py                     : Exergy of heat calculation
- exergy_efficiency.py               : Exergy efficiency (dimensionless)
- exergy_destruction_balance_full.py : Full exergy destruction balance
- units.py                           : Unit normalization and safety

## src/simulation
System structure and roll-up logic.
- stage.py                : Stage data model
- stage_chain.py          : Ordered system of stages
- compute_stage.py        : Stage-level computation
- compute_chain_totals.py : System-level aggregation

## src/agent
Agent orchestration layer (no physics).

## src/ui
User interface (Streamlit).
- streamlit_app.py        : Main UI entrypoint

## tests
Automated test suite validating physics safety and tools.

## Design principles
- Physics lives only in tools/
- Agent never performs calculations
- All computations are deterministic and reproducible
- Non-physical cases are refused explicitly

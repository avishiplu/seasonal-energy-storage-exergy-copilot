# Project File Structure Overview
Seasonal Energy Storage Exergy Copilot

This document describes the final, Phase-4-complete structure of the project.
It serves as a single source of truth for navigation, responsibility boundaries,
and audit-safe understanding of where logic lives.

---------------------------------------------------------------------
ROOT LEVEL
---------------------------------------------------------------------

- src/        : Application source code (domain logic, tools, orchestration, UI)
- tests/      : Automated tests (pytest) validating physics safety and determinism
- docs/       : Project documentation, scope freezes, and handover notes
- data/       : Input data, caches, and indices (non-code assets)

---------------------------------------------------------------------
src/core — CORE DOMAIN & SAFETY
---------------------------------------------------------------------

Core domain definitions and safety enforcement.
No numerical physics is implemented here.

- values.py
  Defines ValueSpec, source tagging (EVIDENCE / COMPUTED / ASSUMPTION / EXTERNAL),
  and enforces traceability of all numerical values.

- refusal.py
  Defines RefusalError.
  All non-physical, incomplete, or ambiguous situations must fail explicitly
  using this mechanism.

- guardrails.py
  High-level physics and boundary guards (second law protection, sanity checks).

- scenario.py
  Scenario definition and validation.
  Holds system intent, boundary metadata, and reference temperature (T0).

- science_config.py
  Frozen scientific configuration.
  Once validated, values here must never change silently.

---------------------------------------------------------------------
src/tools — DETERMINISTIC PHYSICS TOOLS (NO AGENT LOGIC)
---------------------------------------------------------------------

This folder contains all numerical physics.
Every function here must be deterministic and reproducible.

- exergy_core.py
  Exergy of heat calculation (temperature-dependent, Kelvin-only).

- exergy_efficiency.py
  Dimensionless exergy efficiency:
  η = Ex_out / Ex_in
  Includes refusal for invalid inputs.

- exergy_destruction_balance_full.py
  Full exergy destruction balance enforcing the second law.

- units.py
  Unit normalization and safety (Wh/kWh/MWh → J, °C → K, validation).

Rule:
- Physics lives ONLY in src/tools
- No UI, no agent, no guessing

---------------------------------------------------------------------
src/simulation — SYSTEM STRUCTURE & ROLL-UP
---------------------------------------------------------------------

Defines how individual tools are composed into a system.

- stage.py
  Stage data model (inputs, outputs, losses, computed results).
  Stages are immutable once computed.

- stage_chain.py
  Ordered list of stages representing the full system.
  Enforces structural validity (e.g., last stage must be DELIVER).

- compute_stage.py
  Stage-level bookkeeping:
  - Energy totals and balance
  - Exergy totals
  - Exergy destruction (Ex_dest)
  Uses deterministic tools only.

- compute_chain_totals.py
  System-level aggregation:
  - Total energy losses
  - Total exergy destruction
  - System exergy efficiency (grid → deliver boundary)

---------------------------------------------------------------------
src/agent — ORCHESTRATION (NO PHYSICS)
---------------------------------------------------------------------

Agent logic and orchestration layer.

Responsibilities:
- Validate Scenario and StageChain
- Ask for missing information
- Call compute_stage and compute_chain_totals in correct order
- Propagate RefusalError transparently

Forbidden:
- Any physics calculation
- Any unit conversion
- Any guessing

---------------------------------------------------------------------
src/ui — USER INTERFACE
---------------------------------------------------------------------

User-facing interface layer.

- streamlit_app.py
  Streamlit entry point.
  Handles user interaction and visualization only.
  Must never bypass tools or guardrails.

---------------------------------------------------------------------
tests — AUTOMATED VERIFICATION
---------------------------------------------------------------------

Pytest-based test suite ensuring:
- Physics safety
- Determinism
- Correct refusal behavior
- Correct stage and chain aggregation

Key tests:
- test_units_phase3.py
- test_exergy_of_heat_validity.py
- test_exergy_efficiency.py
- test_exergy_destruction_balance_full.py
- test_compute_stage_and_chain.py

---------------------------------------------------------------------
DESIGN PRINCIPLES (NON-NEGOTIABLE)
---------------------------------------------------------------------

- Physics lives only in src/tools
- Simulation composes tools, never reimplements physics
- Agent/UI never performs calculations
- All computations are deterministic and reproducible
- All non-physical cases fail explicitly (no silent fixes)

---------------------------------------------------------------------
END OF PROJECT STRUCTURE
---------------------------------------------------------------------

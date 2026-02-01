# Scope Freeze — Phase 1

This document freezes what is IN scope and what is OUT of scope
for the minimum thesis-grade build.

---

## Must-have (Thesis submission)
These are REQUIRED before the thesis submission is valid:
- Explicit functional unit (1 MWh useful heat delivered to DH boundary)
- Explicit system boundary definition
- Explicit T0 (reference environment) policy
- Exergy-based metrics (system-level + stage-level)
- Deterministic calculations with ValueSpec traceability
- Refusal of ambiguous or physically invalid computations
- Clear comparison tables and plots
- All assumptions explicitly documented

### Simulation & graphs (REQUIRED)
- A time-step simulation loop that produces time-series outputs
- A time-series dataset (time, stage, variable, value, unit, source_type)
- A UI section for simulation graphs:
  - user selects multiple variables
  - same time axis
  - unit-agnostic visualization (trend-focused)
  - export plotted data (CSV) and graphs (PNG)

---

## Optional (Nice-to-have)
These may be added only AFTER must-haves are complete:
- Cost proxy indicators
- UI polish and convenience features
- Additional storage technologies beyond initial set
- Scenario presets

---

## Out of scope (Future work)
These are NOT part of the current thesis build:
- Optimization / automated design search
- Multi-objective Pareto analysis
- Advanced control strategy optimization (beyond a basic rule-based controller)
- Policy optimization modules

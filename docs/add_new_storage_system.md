# How to Add a New Energy Storage System
(Extension Guide — Mandatory Process)

This document defines the ONLY allowed way to add a new energy storage
system to this project.

This is NOT a feature description.
This is a RULED PROCESS that ensures:
- fair comparison
- no hidden assumptions
- physics validity
- consistency across systems

No core scientific rules may be changed when adding a new system.

---------------------------------------------------------------------

STEP 0 — READ FIRST (MANDATORY)

Before adding any new storage system, the following documents are
FROZEN and MUST NOT be modified:

- docs/functional_unit.md
- docs/system_boundary.md
- docs/t0_policy.md
- docs/exergy_of_heat_validity.md
- docs/scope_freeze.md

If your new system requires changing any of the above,
STOP.
This system is outside the current scientific scope.

---------------------------------------------------------------------

STEP 1 — DEFINE THE SYSTEM IN ONE SENTENCE

Write a one-line description of the system.

Required:
- system name
- how it ultimately delivers useful heat to the DH boundary

Example:
System name: Seasonal Battery + Electric Heater
Purpose: Stores electricity and delivers useful heat to district heating

If this cannot be written in one sentence,
the system is not yet well-defined.

---------------------------------------------------------------------

STEP 2 — LIST WHAT IS REQUIRED TO DELIVER HEAT

Answer the question:

What components are strictly required to deliver useful heat
to the district heating boundary?

Create a simple list.

Examples of components:
- energy input unit
- storage medium
- conversion to heat
- transport (pump / cable / compressor)
- heat exchanger to DH
- auxiliary electricity

Do NOT include:
- policy assumptions
- future grid scenarios
- cost arguments

This step is descriptive only.
No code is written here.

---------------------------------------------------------------------

STEP 3 — APPLY THE SYSTEM BOUNDARY RULE

Using docs/system_boundary.md, classify each component as:

INSIDE the system boundary:
- required to deliver useful heat
- produces losses or consumes auxiliary energy

OUTSIDE the system boundary:
- not required for physical heat delivery
- political, economic, or narrative context

RULE:
If a component is required for heat delivery,
it MUST be INSIDE the boundary.

If unsure, classify it as INSIDE.

---------------------------------------------------------------------

STEP 4 — DEFINE REQUIRED INPUTS (NO HIDING)

List the minimum inputs required to simulate this system.

All inputs MUST be provided using ValueSpec objects.

Typical required inputs:
- reference environment temperature (T0)
- delivery temperature (Tb)
- delivered heat amount
- auxiliary electricity consumption
- conversion efficiencies or losses

RULES:
- no input may be assumed silently
- missing inputs must cause a refusal
- units and energy type must be explicit

Inputs will be validated by:
- src/core/scenario.py
- src/core/validate_values.py
- refusal rules in src/core/guardrails.py

---------------------------------------------------------------------

STEP 5 — IMPLEMENT AS A STAGECHAIN

When coding begins, the system must be represented ONLY as:

- an ordered StageChain
- composed of generic stages (CHARGE, STORE, CONVERT, DELIVER)

RULES:
- the chain MUST end with a DELIVER stage
- no technology name may appear in core logic
- all losses must be attached to stages

Relevant code locations:
- src/simulation/
- src/core/
- src/tools/

---------------------------------------------------------------------

STEP 6 — RUN TIME-STEP SIMULATION

The system must produce time-series outputs.

Minimum required outputs:
- time
- stage name
- variable name
- value
- unit
- source type

Static single-value comparison is NOT allowed.

---------------------------------------------------------------------

STEP 7 — VERIFY REFUSAL BEHAVIOUR

Before accepting the new system, verify that:

- missing T0 causes refusal
- invalid temperatures cause refusal
- missing boundary elements cause refusal

Relevant enforcement locations:
- src/core/guardrails.py
- src/tools/exergy_core.py
- tests/

If a physically invalid system does NOT refuse,
the implementation is incorrect.

---------------------------------------------------------------------

FINAL RULE (NON-NEGOTIABLE)

Adding a new storage system means:
- adding a new StageChain
- adding new input data
- running simulation

It does NOT mean:
- changing scientific rules
- bypassing refusal logic
- adding hidden assumptions

All systems must obey the same scientific contract.

# T0 Policy (Frozen)

T0 (reference environment temperature) is a modeling assumption.

Rules:
- T0 MUST be explicitly provided.
- T0 is NOT a hidden default.
- T0 is stored in scenario configuration.
- Weather data may inform T0 choice but MUST NOT auto-overwrite it.

Refusal rule:
- If T0 is missing, exergy computation must refuse.

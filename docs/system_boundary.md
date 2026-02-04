NOTE:
The technology-specific lists below are EXAMPLES.
The boundary rule itself is TECHNOLOGY-AGNOSTIC
and applies to any present or future energy storage system.

# System Boundary (Frozen)

## Boundary rule (global)
Everything required to deliver useful DH heat is INSIDE the system boundary.

Meaning:
- Any component or energy/work flow that is necessary to produce and deliver the DH heat at the delivery boundary is counted.
- We do not compare "partial systems" that hide upstream/downstream losses.

---

## INSIDE boundary: Hydrogen route checklist
Count these INSIDE:
- Electrolyzer
- Compression / liquefaction (as applicable)
- Storage vessel / cavern / tank
- Conversion back to heat (fuel cell / burner / boiler)
- Heat exchanger to DH delivery boundary
- Auxiliary electricity inside the chain (pumps, controls, compressors, balance-of-plant)
- Standing losses / leakage (where applicable)

---

## INSIDE boundary: Thermal route checklist
Count these INSIDE:
- Heat source (heat pump / resistive heater / boiler interface)
- Thermal storage unit (tank / PTES / other thermal store)
- Pumps / valves / controls (aux electricity)
- Heat exchanger to DH delivery boundary
- Standing losses (heat loss to ambient)
- Control losses / parasitic consumption

---

## OUTSIDE boundary: examples (not counted)
Do NOT count these as part of the system:
- Policy, subsidies, taxes, penalties (unless explicitly modeled separately)
- "Future grid decarbonization" narrative without an EXTERNAL dataset and time range
- External narrative assumptions not tied to a ValueSpec
- Ambient environment itself (it is the reference/sink/source, not a component)
- Unspecified upstream processes not required for DH delivery boundary

---

## Boundary clarity examples
Example A (INSIDE):
- If pump power is needed to push heat through HX into DH boundary, include that pump power.

Example B (OUTSIDE):
- If you discuss "grid mix impact" without a specific external time-series/source, it stays outside and must be declared separately.

# Phase 6 — Inputs derived from supervisor discussions

## Electrolyzer

What goes IN:
- Electricity (power)
- Water

What comes OUT:
- Hydrogen
- Heat

Required parameters:
- Electrical efficiency (η_el)
- Outlet pressure
- Outlet temperature

Notes from supervisor:
- Electricity is pure exergy
- Water can be treated as environmental (no exergy)
- Hydrogen exergy must include pressure correction
- Heat exergy depends on Carnot factor (T, T0)

Source:
- Supervisor meeting transcripts

## Metal Hydride

Processes:
- Absorption (charging)
- Desorption (discharging)

Required parameters:
- Hydrogen mass flow
- Absorption temperature
- Desorption temperature
- Heat released / required

Important notes:
- Absorption and desorption temperatures are different
- Heat during absorption may be useful or waste
- Desorption requires heat input (exergy input)
- Reaction rate should be limited by technical boundaries, not Arrhenius only


## Fuel Cell

What goes IN:
- Hydrogen
- Air (can be treated as environmental)

What comes OUT:
- Electricity
- Heat

Required parameters:
- Electrical efficiency
- Heat output temperature

Notes:
- Electricity output is pure exergy
- Heat output exergy depends on temperature level


## Heat Pump / District Heating

What goes IN:
- Electricity
- Possibly heat from fuel cell or storage

What comes OUT:
- District heat

Required parameters:
- COP
- Supply temperature
- Ambient/reference temperature

Notes:
- Exergy of heat calculated using Carnot factor
- Reference environment: same as supervisor paper (T0, p0)

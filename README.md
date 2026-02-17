Seasonal Energy Storage Exergy Copilot
Sprint 3 – Agent-Based Application

------------------------------------------------------------
1. What This Application Does
------------------------------------------------------------

This application compares different seasonal energy storage
systems using exergy analysis.

Instead of manually collecting equations and guessing inputs,
the system:

1) Reads scientific PDFs
2) Extracts equations and parameter hints
3) Detects which inputs are missing
4) Asks the user for only the missing values
5) Stores user inputs as “Assumptions”
6) Runs deterministic exergy calculations
7) Displays structured and transparent results

The goal is to make system comparison:

- Transparent
- Reproducible
- Evidence-aware
- Structured


------------------------------------------------------------
2. Systems That Can Be Compared
------------------------------------------------------------

Examples:

- Metal Hydride seasonal storage
- PTES (Pumped Thermal Energy Storage)
- Electrolyzer → Hydrogen → Fuel Cell chain

Each system is treated as a stage-based chain.

The agent identifies what information is required
for each component automatically.


------------------------------------------------------------
3. How The Agent Works (Simple Explanation)
------------------------------------------------------------

The application runs in steps.

STEP 1 – Upload PDFs (required)
The user uploads scientific papers.

STEP 2 – Run Analysis
The agent:
    - Builds a search index
    - Extracts equation-like lines
    - Tags reliability (VALID / AMBIGUOUS / CONFLICT)
    - Checks required inputs
    - Generates a missing input list

STEP 3 – Provide Missing Inputs
If something is missing:
    - The UI shows only those variables
    - User enters values
    - Values are stored as “Assumptions”

STEP 4 – Run Again
When no inputs are missing:
    - Deterministic exergy tools are executed
    - Results are calculated

STEP 5 – Results Display
The UI shows:

    - System exergy efficiency
    - Total exergy destruction
    - Stage-by-stage breakdown
    - Assumptions used
    - Equation reliability summary


------------------------------------------------------------
4. Important Design Rules
------------------------------------------------------------

1) The system does NOT invent physics.
2) All thermodynamic calculations are deterministic.
3) Every user input is labeled as Assumption.
4) Extracted equations are reliability-tagged.
5) Results are fully structured and inspectable.


------------------------------------------------------------
5. Why This Is An Agent
------------------------------------------------------------

This application is not just a calculator.

It:

- Reacts to new PDFs
- Detects missing data
- Changes behavior depending on state
- Stores memory (assumptions)
- Continues execution after user interaction

The workflow is conditional:

If missing inputs exist → ask user  
If no missing inputs → compute  
If new PDFs uploaded → reset and re-run retrieval  

This conditional multi-step behavior defines the agent.


------------------------------------------------------------
6. What Makes This Useful For Comparison
------------------------------------------------------------

When comparing seasonal storage systems, the challenge is:

- Different papers use different assumptions
- Parameters are often missing
- Equations may be incomplete
- Efficiency numbers are not directly comparable

This system solves that by:

- Explicitly identifying required inputs
- Separating evidence from assumptions
- Running all systems through the same deterministic engine
- Showing stage-by-stage exergy destruction


------------------------------------------------------------
7. Limitations (Transparent)
------------------------------------------------------------

- Equation extraction is heuristic-based
- Citation precision depends on PDF quality
- The current stage chain is minimal but extensible
- User-provided assumptions are not range-validated


------------------------------------------------------------
8. How To Run
------------------------------------------------------------

From project root:

    streamlit run src/ui/streamlit_app.py

Then:

Upload PDFs → Run Analysis → Fill Missing Inputs → Run Again


------------------------------------------------------------
9. Sprint 3 Compliance Summary
------------------------------------------------------------

This application demonstrates:

- Agent-based conditional workflow
- User-interactive state loop
- Structured retrieval + validation
- Deterministic computation tools
- Reliability metadata
- Persistent agent memory

It satisfies Sprint 3 requirements for
an applied AI agent system.

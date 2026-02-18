"""
src/ui/streamlit_app.py

Seasonal Energy Storage Exergy Copilot — Minimal Streamlit UI (Upload-required)

UX goals:
- User MUST upload PDFs (no visible raw folder paths)
- ONE main button: "Run Analysis"
- Minimal buttons: Upload + Run + Reset
- Agent-driven: status NEED_INPUT / DONE controls what UI shows
- No blocking input(); no CLI style loops

Backend behavior:
- Uploaded PDFs are saved into data/raw_papers/ (hidden from user)
- Agent state stored in data/cache/phase7_agent_state.json
"""

from __future__ import annotations

# ----------------------------
# PATH FIX FOR STREAMLIT
# ----------------------------
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ----------------------------
# STANDARD LIBS
# ----------------------------
import json
from typing import Any, Dict, Optional

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

# ----------------------------
# PROJECT IMPORTS
# ----------------------------
from src.core.refusal import RefusalError
from src.core.scenario import Scenario
from src.core.values import assumption_value

# Preferred agent API (UI-friendly)
AGENT_OK = True
try:
    # Must exist: def run_phase7_step(system_name: str, scenario: Scenario, state: dict, pdf_dir: str) -> dict
    from src.agent.phase7_agent import run_phase7_step  # type: ignore
except Exception:
    AGENT_OK = False
    run_phase7_step = None  # type: ignore


# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Seasonal Energy Storage Exergy Copilot", layout="centered")

STATE_PATH = Path("data/cache/phase7_agent_state.json")
PDF_SAVE_DIR = Path("data/raw_papers")  # hidden from user; required by your indexing/retrieval pipeline

SYSTEM_CHOICES = [
    "MH seasonal storage to DH",
    "PTES seasonal storage to DH",
    "Electrolyzer -> H2 -> Fuel cell -> DH",
]


# ----------------------------
# HELPERS
# ----------------------------
def load_state_file() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state_file(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ensure_assumptions(state: Dict[str, Any]) -> None:
    if "assumptions" not in state or not isinstance(state.get("assumptions"), dict):
        state["assumptions"] = {}


def save_uploaded_pdfs(uploaded_files) -> int:
    PDF_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0
    for uf in uploaded_files:
        out_path = PDF_SAVE_DIR / uf.name
        out_path.write_bytes(uf.getbuffer())
        saved += 1
    return saved


def show_error_box(msg: str) -> None:
    st.error(msg)
    st.stop()


# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "phase7_state" not in st.session_state:
    st.session_state.phase7_state = load_state_file()

if "agent_result" not in st.session_state:
    st.session_state.agent_result = None

if "uploaded_ready" not in st.session_state:
    st.session_state.uploaded_ready = False

if "uploader_key" not in st.session_state:
    # used to reset file_uploader so it stops showing old file list
    st.session_state.uploader_key = 0

if "missing_drafts" not in st.session_state:
    # temporary UI inputs before "Save all"
    st.session_state.missing_drafts = {}



# ----------------------------
# HEADER
# ----------------------------
st.title("Seasonal Energy Storage Exergy Copilot")
st.caption("Upload PDFs → Run Analysis → Answer Missing Inputs → Run Again → Results")


# ----------------------------
# SIDEBAR (MINIMAL)
# ----------------------------
st.sidebar.header("Upload PDFs (required)")

with st.sidebar.expander("Upload one or more PDF papers", expanded=True):
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"pdf_uploader_{st.session_state.uploader_key}",
    )

    if uploaded_files:
        saved = save_uploaded_pdfs(uploaded_files)
        st.session_state.uploaded_ready = True
        st.session_state.last_saved_pdf_count = saved
        st.success(f"Saved {saved} PDF(s).")

        # NEW UPLOAD = start fresh (avoid auto-DONE from old assumptions)
        st.session_state.phase7_state = {}
        st.session_state.agent_result = None

        # reset uploader so Streamlit stops showing the uploaded file list
        st.session_state.uploader_key += 1
        st.rerun()



# Reset session (single button)
if st.sidebar.button("Reset Session"):
    st.session_state.clear()
    st.rerun()

# If agent API missing, show clear message (no confusing fallback)
if not AGENT_OK:
    show_error_box(
        "Agent API not available.\n\n"
        "Please implement `run_phase7_step()` in `src/agent/phase7_agent.py`.\n"
        "UI requires a structured return dict with status NEED_INPUT / DONE."
    )


# ----------------------------
# SYSTEM + SCENARIO (MINIMAL)
# ----------------------------
st.subheader("System & Scenario")

system_name = st.selectbox("Select system", options=SYSTEM_CHOICES, index=0)

c1, c2, c3 = st.columns(3)
with c1:
    T0 = st.number_input("T0 (K)", value=293.15, step=0.1)
with c2:
    Ts = st.number_input("Ts supply (K)", value=353.15, step=0.1)
with c3:
    Tr = st.number_input("Tr return (K)", value=333.15, step=0.1)

scenario = Scenario(
    name="streamlit_run",
    location="Hamburg",
    time_start="2022-01-01",
    time_end="2022-01-02",
    analysis_intent="teaching",
    T0_K=assumption_value(float(T0), "K", meta={"note": "UI input"}),
    Ts_K=assumption_value(float(Ts), "K", meta={"note": "UI input"}),
    Tr_K=assumption_value(float(Tr), "K", meta={"note": "UI input"}),
)
scenario.validate()


# ----------------------------
# UPLOAD ENFORCEMENT
# ----------------------------
if not st.session_state.uploaded_ready:
    st.warning("Please upload at least one PDF in the sidebar before running analysis.")
    st.stop()


# ----------------------------
# MAIN ACTION (ONE BUTTON)
# ----------------------------
st.subheader("Run")

run_clicked = st.button("Run Analysis")

def run_agent_step() -> Dict[str, Any]:
    # One step call; agent decides NEED_INPUT vs DONE
    return run_phase7_step(
        system_name=system_name,
        scenario=scenario,
        state=st.session_state.phase7_state,
        pdf_dir=str(PDF_SAVE_DIR),
    )

if run_clicked:
    try:
        res = run_agent_step()
        st.session_state.agent_result = res
        # persist updated state from agent
        save_state_file(st.session_state.phase7_state)
    except RefusalError as e:
        st.error(f"RefusalError: {e.user_message}")
        if hasattr(e, "why") and e.why:
            st.caption(f"Why: {e.why}")
        if hasattr(e, "details") and isinstance(e.details, dict) and e.details:
            with st.expander("Refusal details (debug)", expanded=True):
                st.json(e.details)
        st.stop()

    except Exception as e:
        st.exception(e)
        st.stop()


# ----------------------------
# RENDER RESULTS / QUESTIONS
# ----------------------------
res: Optional[Dict[str, Any]] = st.session_state.agent_result

if res is None:
    st.info("Click **Run Analysis** to start.")
    st.stop()

status = res.get("status", "UNKNOWN")
st.markdown(f"### Status: **{status}**")

# Reliability (if provided)
if isinstance(res.get("reliability"), dict):
    with st.expander("Equation reliability (optional)"):
        st.json(res["reliability"])

# NEED_INPUT => show missing questions
if status == "NEED_INPUT":
    st.markdown("### Missing inputs (fill these, then press **Run Analysis** again)")

    missing = res.get("missing") or []
    if not missing:
        st.warning("Agent returned NEED_INPUT but missing list is empty.")
        st.stop()

    ensure_assumptions(st.session_state.phase7_state)

    for item in missing:
        key = item.get("key")
        unit = item.get("unit")
        comp = item.get("component")
        critical = item.get("critical")
        cite_pdf = item.get("citation_pdf")
        cite_page = item.get("citation_page")

        title = f"{comp}: {key} ({unit}) | critical={critical}"
        with st.expander(title, expanded=bool(critical)):

            if cite_pdf:
                st.caption(f"Citation hint: {cite_pdf} : page {cite_page}")

            existing = st.session_state.phase7_state["assumptions"].get(key, {})
            existing_val = existing.get("value", "")

            input_key = f"missval_{comp}_{key}"

            val_str = st.text_input(
                f"Value for {key} ({unit})",
                value=str(existing_val) if existing_val != "" else "",
                key=input_key,
            )

    st.markdown("---")

    save_all = st.button("Save all missing inputs")

    if save_all:
        errors = []
        ensure_assumptions(st.session_state.phase7_state)

        for item in missing:
            key = item.get("key")
            unit = item.get("unit")
            comp = item.get("component")
            cite_pdf = item.get("citation_pdf")
            cite_page = item.get("citation_page")

            input_key = f"missval_{comp}_{key}"
            raw_val = st.session_state.get(input_key, "")

            try:
                v = float(raw_val)
            except Exception:
                errors.append(f"{key} must be a number ({unit})")
                continue

            st.session_state.phase7_state["assumptions"][key] = {
                "value": v,
                "unit": unit,
                "source": "Assumption",
                "meta": {
                    "component": comp,
                    "note": "Provided via Streamlit UI (Save all)",
                    "citation_hint": f"{cite_pdf}:{cite_page}" if cite_pdf else None,
                },
            }

        if errors:
            st.error("Fix these inputs first:\n- " + "\n- ".join(errors))
        else:
            save_state_file(st.session_state.phase7_state)
            st.success("All missing inputs saved as assumptions.")


    st.info("Now press **Run Analysis** again to continue the agent.")

# DONE => show results
elif status == "DONE":
    st.markdown("### Results")

    results = res.get("results")
    if results is None:
        st.warning("Agent returned DONE but results is empty. (Agent output mismatch)")
    else:
        st.json(results)

    stages = res.get("stages") or []
    if stages:
        st.markdown("### Stage breakdown")
        for s in stages:
            name = s.get("name", "Stage")
            with st.expander(name):
                st.json(s)

    st.markdown("### Assumptions used")
    ensure_assumptions(st.session_state.phase7_state)
    st.json(st.session_state.phase7_state["assumptions"])

else:
    st.warning("Unknown agent status. Check agent output format.")

# Optional minimal diagnostics (hidden)
with st.expander("Diagnostics (optional)", expanded=False):
    st.markdown("**Agent raw output**")
    st.json(res)

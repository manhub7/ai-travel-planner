# app.py

import asyncio

import streamlit as st

from workflow import run_travel_workflow


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
)


# ============================================================
# UI
# ============================================================

st.title("✈️ AI Travel Planner")

st.write(
    "Build a travel plan using a multi-stage AI workflow."
)


user_request = st.text_area(
    "Describe your trip",

    placeholder=(
        "Example:\n"
        "I want to visit Turkey for 7 days "
        "with a total budget of $1500."
    ),

    height=150,
)


# ============================================================
# Run workflow
# ============================================================

if st.button(
    "Plan My Trip",
    type="primary",
):

    if not user_request.strip():

        st.warning(
            "Please describe your trip first."
        )

        st.stop()

    try:

        with st.spinner(
            "AI agents are planning your trip..."
        ):

            state = asyncio.run(
                run_travel_workflow(
                    user_request
                )
            )

        st.success(
            "Travel planning completed!"
        )

        # ----------------------------------------------------
        # Requirements
        # ----------------------------------------------------

        with st.expander(
            "1️⃣ Parsed Requirements",
            expanded=False,
        ):

            st.json(
                state.requirements
            )

        # ----------------------------------------------------
        # Logistics
        # ----------------------------------------------------

        with st.expander(
            "2️⃣ Logistics",
            expanded=False,
        ):

            st.json(
                state.logistics
            )

        # ----------------------------------------------------
        # Excursions
        # ----------------------------------------------------

        with st.expander(
            "3️⃣ Excursions",
            expanded=False,
        ):

            st.json(
                state.excursions
            )

        # ----------------------------------------------------
        # Budget
        # ----------------------------------------------------

        st.subheader(
            "💰 Budget"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Budget",
            f"{state.budget.get('budget_limit', 0)} "
            f"{state.budget.get('currency', 'USD')}"
        )

        col2.metric(
            "Estimated Cost",
            f"{state.budget.get('estimated_total', 0)} "
            f"{state.budget.get('currency', 'USD')}"
        )

        col3.metric(
            "Remaining",
            f"{state.budget.get('remaining', 0)} "
            f"{state.budget.get('currency', 'USD')}"
        )

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        st.subheader(
            "🛡️ Budget Validation"
        )

        status = state.validation.get(
            "status",
            "UNKNOWN"
        )

        if status == "PASS":

            st.success(
                "Budget validation PASSED."
            )

        else:

            st.error(
                "Budget validation FAILED."
            )

        st.json(
            state.validation
        )

        # ----------------------------------------------------
        # Final itinerary
        # ----------------------------------------------------

        if state.itinerary:

            st.subheader(
                "🗺️ Your Itinerary"
            )

            st.json(
                state.itinerary
            )

    except Exception as error:

        st.error(
            "Something went wrong."
        )

        st.exception(error)
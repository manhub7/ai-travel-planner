# workflow.py

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from groq import AsyncGroq
from dotenv import load_dotenv

from prompts import (
    INTENT_ROUTER_PROMPT,
    LOGISTICS_AGENT_PROMPT,
    EXCURSIONS_AGENT_PROMPT,
    BUDGET_VALIDATOR_PROMPT,
    ITINERARY_FORMATTER_PROMPT,
)

load_dotenv()


# ============================================================
# Configuration
# ============================================================

MODEL = "openai/gpt-oss-20b"

MAX_REPLAN_ATTEMPTS = 3


# ============================================================
# Groq Client
# ============================================================

client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ============================================================
# State
# ============================================================

@dataclass
class TripState:

    user_request: str

    requirements: dict[str, Any] = field(
        default_factory=dict
    )

    logistics: dict[str, Any] = field(
        default_factory=dict
    )

    excursions: dict[str, Any] = field(
        default_factory=dict
    )

    budget: dict[str, Any] = field(
        default_factory=dict
    )

    validation: dict[str, Any] = field(
        default_factory=dict
    )

    itinerary: dict[str, Any] = field(
        default_factory=dict
    )

    iteration: int = 0


# ============================================================
# Helper: Groq JSON call
# ============================================================

async def ask_groq(
    system_prompt: str,
    user_prompt: str,
) -> dict:

    response = await client.chat.completions.create(

        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        response_format={
            "type": "json_object"
        },

        temperature=0.2,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Groq returned an empty response."
        )

    return json.loads(content)


# ============================================================
# Stage 1
# ============================================================

async def intent_router(
    state: TripState
) -> TripState:

    print("[Router] Starting")

    result = await ask_groq(
        INTENT_ROUTER_PROMPT,
        state.user_request,
    )

    state.requirements = result

    print("[Router] Complete")

    return state


# ============================================================
# Stage 2A
# ============================================================

async def logistics_agent(
    state: TripState
) -> dict:

    print("[Logistics] Starting")

    prompt = json.dumps(
        state.requirements,
        indent=2
    )

    result = await ask_groq(
        LOGISTICS_AGENT_PROMPT,
        prompt,
    )

    print("[Logistics] Complete")

    return result


# ============================================================
# Stage 2B
# ============================================================

async def excursions_agent(
    state: TripState
) -> dict:

    print("[Excursions] Starting")

    prompt = json.dumps(
        state.requirements,
        indent=2
    )

    result = await ask_groq(
        EXCURSIONS_AGENT_PROMPT,
        prompt,
    )

    print("[Excursions] Complete")

    return result


# ============================================================
# Parallel execution
# ============================================================

async def run_parallel_agents(
    state: TripState
):

    print("[Workflow] Starting parallel agents")

    logistics_task = logistics_agent(state)

    excursions_task = excursions_agent(state)

    logistics_result, excursions_result = await asyncio.gather(
        logistics_task,
        excursions_task
    )

    print("[Workflow] Parallel agents complete")

    return (
        logistics_result,
        excursions_result
    )


# ============================================================
# State merging
# ============================================================

def merge_agent_results(
    state: TripState,
    logistics_result: dict,
    excursions_result: dict,
) -> TripState:

    print("[State] Merging results")

    state.logistics = logistics_result

    state.excursions = excursions_result

    return state


# ============================================================
# Deterministic budget calculation
# ============================================================

def calculate_costs(
    state: TripState
) -> float:

    total = 0.0

    # Flights
    for flight in state.logistics.get(
        "flights", []
    ):

        total += float(
            flight.get("cost", 0)
        )

    # Hotels
    for hotel in state.logistics.get(
        "hotels", []
    ):

        total += float(
            hotel.get("total_cost", 0)
        )

    # Transportation
    for transport in state.logistics.get(
        "transportation", []
    ):

        total += float(
            transport.get("cost", 0)
        )

    # Activities
    for activity in state.excursions.get(
        "activities", []
    ):

        total += float(
            activity.get("cost", 0)
        )

    return round(total, 2)


# ============================================================
# Stage 3
# ============================================================

async def budget_validator(
    state: TripState
) -> TripState:

    print("[Budget] Starting")

    total_cost = calculate_costs(state)

    budget_limit = float(
        state.requirements.get(
            "budget",
            0
        )
    )

    remaining = round(
        budget_limit - total_cost,
        2
    )

    state.budget = {

        "budget_limit": budget_limit,

        "estimated_total": total_cost,

        "remaining": remaining,

        "currency": state.requirements.get(
            "currency",
            "USD"
        ),
    }

    validation_prompt = json.dumps(
        {
            "requirements": state.requirements,

            "budget": state.budget,

            "logistics": state.logistics,

            "excursions": state.excursions,
        },
        indent=2
    )

    result = await ask_groq(
        BUDGET_VALIDATOR_PROMPT,
        validation_prompt,
    )

    state.validation = result

    # Deterministic safety gate.
    # The LLM cannot override the actual arithmetic.

    if total_cost <= budget_limit:

        state.validation["status"] = "PASS"

    else:

        state.validation["status"] = "FAIL"

    print(
        f"[Budget] {state.validation['status']}"
    )

    return state


# ============================================================
# Stage 4
# ============================================================

async def itinerary_formatter(
    state: TripState
) -> TripState:

    print("[Formatter] Starting")

    formatter_input = json.dumps(
        {
            "requirements": state.requirements,

            "logistics": state.logistics,

            "excursions": state.excursions,

            "budget": state.budget,

            "validation": state.validation,
        },
        indent=2
    )

    result = await ask_groq(
        ITINERARY_FORMATTER_PROMPT,
        formatter_input,
    )

    state.itinerary = result

    print("[Formatter] Complete")

    return state


# ============================================================
# Main workflow
# ============================================================

async def run_travel_workflow(
    user_request: str
) -> TripState:

    print("\n==============================")
    print("TRAVEL WORKFLOW START")
    print("==============================")

    state = TripState(
        user_request=user_request
    )

    # --------------------------------------------------------
    # Stage 1
    # --------------------------------------------------------

    state = await intent_router(state)

    # --------------------------------------------------------
    # Stage 2
    # --------------------------------------------------------

    (
        logistics_result,
        excursions_result,
    ) = await run_parallel_agents(state)

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    state = merge_agent_results(
        state,
        logistics_result,
        excursions_result,
    )

    # --------------------------------------------------------
    # Stage 3 + Replanning
    # --------------------------------------------------------

    for attempt in range(
        MAX_REPLAN_ATTEMPTS
    ):

        state.iteration = attempt + 1

        state = await budget_validator(
            state
        )

        if (
            state.validation.get("status")
            == "PASS"
        ):

            break

        print(
            f"[Workflow] Budget failed "
            f"(attempt {attempt + 1})"
        )

        # Replanning will be added here.
        #
        # For the first implementation,
        # stop instead of creating an
        # uncontrolled recursive loop.

        break

    # --------------------------------------------------------
    # Stage 4
    # --------------------------------------------------------

    if (
        state.validation.get("status")
        == "PASS"
    ):

        state = await itinerary_formatter(
            state
        )

    else:

        print(
            "[Workflow] Itinerary not generated "
            "because budget validation failed."
        )

    print("\n==============================")
    print("TRAVEL WORKFLOW END")
    print("==============================")

    return state
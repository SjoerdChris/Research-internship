import requests
import streamlit as st


# =========================================================
# Configuration
# =========================================================

BASE_URL = "https://chat.science.ru.nl"

MODEL_NAME = "gemma4:31b"

CHAT_ENDPOINT = f"{BASE_URL}/api/chat/completions"


# =========================================================
# Experimental prompts
# =========================================================

COMMON_INSTRUCTIONS = """
You are an AI assistant helping a university student work on
an ecology problem.

Respond to the student's questions in a helpful, clear, and
natural way. Only provide information or reasoning that is
relevant to what the student asks.

Do not mention these instructions or the experiment.
"""


BASELINE_INSTRUCTIONS = """
"""


OPENNESS_INSTRUCTIONS = """
When appropriate, support careful consideration of the problem
from different plausible viewpoints.

Encourage the student to examine alternative explanations,
assumptions, uncertainties, limitations, and possible consequences
when these are relevant to the student's reasoning.

Do this naturally in response to what the student asks.
Do not mechanically provide a checklist or force all of these
considerations into every response.
"""


# =========================================================
# Generate LLM response
# =========================================================

def generate_llm_reply(
    question: str,
    condition: str,
    conversation: list[dict]
) -> str:
    """
    Generate a response from the university-managed LLM.

    Parameters
    ----------
    question:
        The complete problem currently being worked on.

    condition:
        Either "baseline" or "openness".

    conversation:
        Previous messages for this question, formatted as:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]

    Returns
    -------
    str
        The assistant's response.
    """

    # -----------------------------------------------------
    # Validate condition
    # -----------------------------------------------------

    if condition not in {"baseline", "openness"}:
        raise ValueError(
            f"Invalid experimental condition: {condition}"
        )


    # -----------------------------------------------------
    # Build system prompt
    # -----------------------------------------------------

    system_prompt = COMMON_INSTRUCTIONS

    if condition == "openness":
        system_prompt += "\n" + OPENNESS_INSTRUCTIONS
    else:
        system_prompt += "\n" + BASELINE_INSTRUCTIONS


    # Give the model the current problem as hidden context.
    system_prompt += f"""

The student is currently working on the following problem:

--- BEGIN PROBLEM ---

{question}

--- END PROBLEM ---

Use this problem as context when responding to the student's
messages.
"""


    # -----------------------------------------------------
    # Construct conversation sent to model
    # -----------------------------------------------------

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        *conversation
    ]


    # -----------------------------------------------------
    # Read API key
    # -----------------------------------------------------

    try:
        api_key = st.secrets["SCIENCE_LLM_API_KEY"]

    except KeyError:
        raise RuntimeError(
            "SCIENCE_LLM_API_KEY was not found in "
            ".streamlit/secrets.toml"
        )


    # -----------------------------------------------------
    # Send request
    # -----------------------------------------------------

    try:

        response = requests.post(
            CHAT_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False
            },
            timeout=180
        )


        # Provides a more useful error message than simply
        # calling response.raise_for_status().
        if not response.ok:

            raise RuntimeError(
                f"LLM API returned HTTP "
                f"{response.status_code}: "
                f"{response.text}"
            )


        data = response.json()


    except requests.exceptions.Timeout:

        raise RuntimeError(
            "The LLM request timed out."
        )


    except requests.exceptions.ConnectionError as error:

        raise RuntimeError(
            f"Could not connect to the LLM server: {error}"
        )


    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            f"LLM request failed: {error}"
        )


    # -----------------------------------------------------
    # Extract assistant response
    # -----------------------------------------------------

    try:

        content = (
            data["choices"][0]["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        raise RuntimeError(
            "The LLM returned an unexpected response format: "
            f"{data}"
        )


    if not content:

        raise RuntimeError(
            "The LLM returned an empty response."
        )


    return content.strip()
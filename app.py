import random
import uuid

import streamlit as st

from database import (
    init_database,
    register_participant,
    save_question_assignment,
    save_llm_exchange,
    save_submission,
    save_questionnaire_response,
    mark_participant_completed,
)
from llm import generate_llm_reply


# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="LLM Openness Experiment",
    layout="wide",
)

st.title("LLM Openness Experiment")


# =========================================================
# Experiment configuration
# =========================================================

TASK_INSTRUCTION = """
Develop a strategy for managing this ecosystem.
Explain why you chose this strategy and justify your reasoning.
"""


# Condition depends on the position in the experiment,
# not on which ecological problem was randomly selected.
CONDITION_BY_QUESTION_INDEX = {
    0: "baseline",
    1: "openness",
}


QUESTIONNAIRE_OPTIONS = [
    "Much more in Question 1",
    "Slightly more in Question 1",
    "About the same",
    "Slightly more in Question 2",
    "Much more in Question 2",
]


# =========================================================
# Questions
# =========================================================

QUESTION_BANK = [
    {
        "id": "kelp",
        "text": """
Along a temperate coastline, kelp forests support fish,
invertebrates and seabirds. Kelp forms the main source of
primary production. Sea urchins consume kelp, several large
fish species feed on urchins and smaller animals, and seabirds
mainly feed on small fish. Dead kelp also provides an important
energy source for detritivores.

During the last decade, large predatory fish have become less
abundant because of fishing, while sea urchins have increased.
At the same time, several unusually warm summers have reduced
kelp growth. Some locations have lost most of their kelp,
whereas apparently similar locations remain relatively intact.
Surprisingly, total fish abundance has not decreased equally
at all sites.

Local authorities want to restore the ecosystem. Proposed
measures include restricting fishing of large predatory fish,
directly removing sea urchins, creating areas where fishing is
excluded, or focusing resources on protecting the remaining
kelp. Fishing communities depend economically on several of
the species involved, and the available budget does not allow
all measures to be implemented simultaneously. The strengths
of several feeding relationships and their responses to future
warming remain uncertain.
""",
    },
    {
        "id": "dunes",
        "text": """
A coastal dune reserve contains a mixture of dry grasslands,
moist depressions and shrub-dominated areas. Historically,
these habitats supported many plant species with different
distributions across the landscape.

During the last twenty years, nitrogen availability has
increased and several wet depressions have become drier.
A few common plant species have expanded strongly, while
several less abundant species have disappeared from some
locations. However, apparently suitable patches sometimes
remain unoccupied, and similar patches can contain rather
different communities.

Managers want to reverse the biodiversity decline. Suggested
measures include reducing nutrient availability, restoring
groundwater levels, increasing grazing, creating greater
small-scale variation in environmental conditions, or actively
reintroducing species into apparently suitable patches.
Each measure is costly, and some may conflict with maintaining
accessibility of the dunes for recreation.

It is unclear to what extent the present species distributions
reflect environmental conditions, competition between species,
limitations on colonisation, or simply historical and stochastic
changes in abundance.
""",
    },
]


# =========================================================
# Database initialization
# =========================================================

@st.cache_resource
def setup_database():
    init_database()
    return True


try:
    setup_database()
except Exception as error:
    print("Database initialization error:", repr(error))
    st.error(
        "The experiment database could not be initialized. "
        "Please inform the researcher."
    )
    st.stop()


# =========================================================
# Initialize participant/session
# =========================================================

if "participant_id" not in st.session_state:
    st.session_state.participant_id = uuid.uuid4().hex


if "question_order" not in st.session_state:
    st.session_state.question_order = random.sample(
        QUESTION_BANK,
        k=len(QUESTION_BANK),
    )


if "current_question" not in st.session_state:
    st.session_state.current_question = 0


if "answers" not in st.session_state:
    st.session_state.answers = {
        question_nr: ""
        for question_nr in range(
            len(st.session_state.question_order)
        )
    }


if "llm_messages" not in st.session_state:
    st.session_state.llm_messages = {
        question_nr: []
        for question_nr in range(
            len(st.session_state.question_order)
        )
    }


# Tracks whether the pre-LLM answer snapshot has already
# been saved for each question.
if "initial_submission_saved" not in st.session_state:
    st.session_state.initial_submission_saved = {
        question_nr: False
        for question_nr in range(
            len(st.session_state.question_order)
        )
    }


if "questionnaire" not in st.session_state:
    st.session_state.questionnaire = None


if "stage" not in st.session_state:
    st.session_state.stage = "questions"


participant_id = st.session_state.participant_id
QUESTIONS = st.session_state.question_order


# =========================================================
# Helper functions
# =========================================================

def get_condition(question_index: int) -> str:
    try:
        return CONDITION_BY_QUESTION_INDEX[question_index]
    except KeyError as error:
        raise ValueError(
            "No experimental condition configured for "
            f"question index {question_index}."
        ) from error


def save_final_answer(question_index: int) -> None:
    """
    Save the current final answer for one question.
    Upsert semantics in database.py allow later edits.
    """
    save_submission(
        participant_id=participant_id,
        question_nr=question_index + 1,
        response_type="final",
        content=st.session_state.answers[
            question_index
        ].strip(),
    )


def save_initial_answer_if_needed(
    question_index: int,
) -> None:
    """
    Save a snapshot of the participant's answer immediately
    before their first LLM interaction for this question.
    """
    if st.session_state.initial_submission_saved[
        question_index
    ]:
        return

    save_submission(
        participant_id=participant_id,
        question_nr=question_index + 1,
        response_type="initial",
        content=st.session_state.answers[
            question_index
        ].strip(),
    )

    st.session_state.initial_submission_saved[
        question_index
    ] = True


# =========================================================
# Register participant and randomized question assignment
# =========================================================

if "participant_registered" not in st.session_state:
    try:
        register_participant(
            participant_id=participant_id,
            condition=None,
        )

        for question_index, question in enumerate(
            QUESTIONS
        ):
            save_question_assignment(
                participant_id=participant_id,
                question_nr=question_index + 1,
                question_id=question["id"],
                condition=get_condition(question_index),
            )

    except Exception as error:
        print(
            "Database error while registering participant:",
            repr(error),
        )

        st.error(
            "Your participant session could not be "
            "registered. Please inform the researcher."
        )
        st.stop()

    st.session_state.participant_registered = True


# =========================================================
# Completed screen
# =========================================================

if st.session_state.stage == "completed":
    st.success(
        "Your responses have been submitted successfully."
    )

    st.write(
        "Thank you for participating."
    )

    st.stop()


# =========================================================
# Questionnaire stage
# =========================================================

if st.session_state.stage == "questionnaire":
    st.progress(
        1.0,
        text="Questionnaire",
    )

    st.header("Questionnaire")

    st.write(
        "Please compare your experience with the LLM "
        "during the two questions."
    )

    with st.form("questionnaire_form"):
        perspectives = st.radio(
            (
                "During which question did the LLM "
                "encourage you more to consider different "
                "perspectives, explanations, or possible "
                "approaches?"
            ),
            QUESTIONNAIRE_OPTIONS,
            index=None,
            key="questionnaire_perspectives",
        )

        steering = st.radio(
            (
                "During which question did the LLM seem "
                "more likely to steer your reasoning toward "
                "one particular conclusion or point of view?"
            ),
            QUESTIONNAIRE_OPTIONS,
            index=None,
            key="questionnaire_steering",
        )

        uncertainty = st.radio(
            (
                "During which question did the LLM "
                "encourage you more to consider uncertainty, "
                "limitations, or information that was not "
                "known?"
            ),
            QUESTIONNAIRE_OPTIONS,
            index=None,
            key="questionnaire_uncertainty",
        )

        comments = st.text_area(
            (
                "Optional: Is there anything else you "
                "would like to mention about your "
                "experience with the LLM?"
            ),
            key="questionnaire_comments",
        )

        questionnaire_submitted = (
            st.form_submit_button(
                "Submit experiment",
                type="primary",
                use_container_width=True,
            )
        )

    if questionnaire_submitted:
        if (
            perspectives is None
            or steering is None
            or uncertainty is None
        ):
            st.error(
                "Please answer all three questionnaire "
                "questions before submitting."
            )

        else:
            questionnaire = {
                "perspectives": perspectives,
                "steering_toward_conclusion": steering,
                "uncertainty_and_limitations": uncertainty,
                "comments": comments.strip(),
            }

            try:
                with st.spinner(
                    "Submitting your responses..."
                ):
                    # Save final answers once more at the
                    # point of final experiment submission.
                    for question_index in range(
                        len(QUESTIONS)
                    ):
                        save_final_answer(
                            question_index
                        )

                    save_questionnaire_response(
                        participant_id=participant_id,
                        perspectives=perspectives,
                        steering_toward_conclusion=steering,
                        uncertainty_and_limitations=uncertainty,
                        comments=comments.strip() or None,
                    )

                    mark_participant_completed(
                        participant_id
                    )

            except Exception as error:
                print(
                    "Database error while submitting experiment:",
                    repr(error),
                )

                st.error(
                    "Your responses could not be submitted. "
                    "Please try again or inform the researcher."
                )

            else:
                st.session_state.questionnaire = (
                    questionnaire
                )
                st.session_state.stage = "completed"
                st.rerun()

    st.stop()


# =========================================================
# Question stage
# =========================================================

question_index = st.session_state.current_question
condition = get_condition(question_index)
current_question = QUESTIONS[question_index]


# =========================================================
# Progress
# =========================================================

st.progress(
    (question_index + 1) / (len(QUESTIONS) + 1),
    text=(
        f"Question {question_index + 1} "
        f"of {len(QUESTIONS)}"
    ),
)


# =========================================================
# Display current question
# =========================================================

st.subheader(
    f"Question {question_index + 1}"
)

st.write(
    current_question["text"]
)

st.markdown("**Task**")

st.write(
    TASK_INSTRUCTION
)


full_problem = (
    current_question["text"]
    + "\n\n"
    + TASK_INSTRUCTION
)


# =========================================================
# Main layout
# =========================================================

answer_column, llm_column = st.columns(
    [1, 1],
    gap="large",
)


# =========================================================
# Participant answer
# =========================================================

with answer_column:
    st.markdown(
        "### Your answer"
    )

    st.caption(
        "Write your final answer here."
    )

    answer_widget_key = (
        f"answer_widget_{question_index}"
    )

    if answer_widget_key not in st.session_state:
        st.session_state[
            answer_widget_key
        ] = st.session_state.answers[
            question_index
        ]

    st.text_area(
        "Your response:",
        height=450,
        key=answer_widget_key,
        label_visibility="collapsed",
    )


# =========================================================
# LLM assistant
# =========================================================

with llm_column:
    st.markdown(
        "### LLM assistant"
    )

    st.caption(
        "You may use the LLM while working "
        "on the problem."

    )
    st.info(
    st.info(
        "Please do not share any personal information with the LLM."
    )
    conversation = (
        st.session_state.llm_messages[
            question_index
        ]
    )

    number_of_prompts = sum(
        1
        for message in conversation
        if message["role"] == "user"
    )

    if not conversation:
        st.info(
            "No messages yet. "
            "You can ask the LLM about the problem."
        )

    else:
        for message in conversation:
            with st.chat_message(
                message["role"]
            ):
                st.write(
                    message["content"]
                )

    with st.form(
        key=f"llm_form_{question_index}",
        clear_on_submit=True,
    ):
        llm_prompt = st.text_area(
            "Message the LLM:",
            height=100,
            placeholder="Type your message here...",
        )

        send_clicked = (
            st.form_submit_button(
                "Send",
                type="primary",
                use_container_width=True,
            )
        )

    if send_clicked:
        prompt = llm_prompt.strip()

        if not prompt:
            st.warning(
                "Please enter a message."
            )

        else:
            # Preserve the answer visible before the rerun.
            st.session_state.answers[
                question_index
            ] = st.session_state[
                answer_widget_key
            ]

            try:
                save_initial_answer_if_needed(
                    question_index
                )

            except Exception as error:
                print(
                    "Database error while saving initial answer:",
                    repr(error),
                )
                st.error(
                    "Your answer could not be saved. "
                    "Please inform the researcher."
                )
                st.stop()

            message_nr = (
                number_of_prompts + 1
            )

            user_message = {
                "role": "user",
                "content": prompt,
            }

            conversation.append(
                user_message
            )

            try:
                with st.spinner(
                    "Generating response..."
                ):
                    assistant_response = (
                        generate_llm_reply(
                            question=full_problem,
                            condition=condition,
                            conversation=conversation,
                        )
                    )

            except Exception as error:
                print(
                    "LLM API error:",
                    repr(error),
                )

                # Remove the user message because this
                # exchange was not completed.
                conversation.pop()

                st.error(
                    "The LLM could not respond. "
                    "Please try again."
                )

            else:
                try:
                    save_llm_exchange(
                        participant_id=participant_id,
                        question_nr=question_index + 1,
                        message_nr=message_nr,
                        user_content=prompt,
                        assistant_content=assistant_response,
                    )

                except Exception as error:
                    print(
                        "Database error while saving LLM exchange:",
                        repr(error),
                    )

                    # Keep session and database consistent:
                    # remove the unsaved user message.
                    conversation.pop()

                    st.error(
                        "The LLM interaction could not be "
                        "saved. Please inform the researcher."
                    )

                else:
                    conversation.append(
                        {
                            "role": "assistant",
                            "content": assistant_response,
                        }
                    )
                    st.rerun()


# =========================================================
# Temporarily save answer
# =========================================================

def temporarily_save_current_answer():
    st.session_state.answers[
        question_index
    ] = st.session_state[
        answer_widget_key
    ]


# =========================================================
# Navigation
# =========================================================

st.divider()

previous_column, middle_column, next_column = (
    st.columns(
        [1, 3, 1]
    )
)


with previous_column:
    previous_clicked = st.button(
        "← Previous question",
        disabled=(
            question_index == 0
        ),
        use_container_width=True,
    )


with next_column:
    if question_index < len(QUESTIONS) - 1:
        next_clicked = st.button(
            "Next question →",
            type="primary",
            use_container_width=True,
        )

        questionnaire_clicked = False

    else:
        next_clicked = False

        questionnaire_clicked = st.button(
            "Continue to questionnaire →",
            type="primary",
            use_container_width=True,
        )


# =========================================================
# Handle navigation
# =========================================================

if previous_clicked:
    temporarily_save_current_answer()

    try:
        save_final_answer(
            question_index
        )
    except Exception as error:
        print(
            "Database error while saving answer:",
            repr(error),
        )
        st.error(
            "Your answer could not be saved. "
            "Please inform the researcher."
        )
        st.stop()

    st.session_state.current_question -= 1
    st.rerun()


if next_clicked:
    temporarily_save_current_answer()

    if not st.session_state.answers[
        question_index
    ].strip():
        st.error(
            "Please answer this question before continuing."
        )
    else:
        try:
            save_final_answer(
                question_index
            )
        except Exception as error:
            print(
                "Database error while saving answer:",
                repr(error),
            )
            st.error(
                "Your answer could not be saved. "
                "Please inform the researcher."
            )
            st.stop()

        st.session_state.current_question += 1
        st.rerun()


if questionnaire_clicked:
    temporarily_save_current_answer()

    unanswered_questions = [
        question_nr + 1
        for question_nr, answer
        in st.session_state.answers.items()
        if not answer.strip()
    ]

    if unanswered_questions:
        unanswered_text = ", ".join(
            str(number)
            for number in unanswered_questions
        )

        st.error(
            "Please answer all questions before "
            "continuing. "
            f"Missing: question {unanswered_text}."
        )

    else:
        try:
            for question_index_to_save in range(
                len(QUESTIONS)
            ):
                save_final_answer(
                    question_index_to_save
                )

        except Exception as error:
            print(
                "Database error while saving final answers:",
                repr(error),
            )
            st.error(
                "Your answers could not be saved. "
                "Please inform the researcher."
            )

        else:
            st.session_state.stage = "questionnaire"
            st.rerun()


# =========================================================
# Answer progress
# =========================================================

with st.expander(
    "View answer progress"
):
    current_visible_answer = (
        st.session_state[
            answer_widget_key
        ]
    )

    for question_nr, answer in (
        st.session_state.answers.items()
    ):
        if question_nr == question_index:
            answer_for_status = (
                current_visible_answer
            )
        else:
            answer_for_status = answer

        status = (
            "Answered"
            if answer_for_status.strip()
            else "Not answered"
        )

        st.write(
            f"Question {question_nr + 1}: "
            f"**{status}**"
        )
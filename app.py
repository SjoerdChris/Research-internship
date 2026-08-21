import random
import uuid

import streamlit as st

from database import (
    init_database,
    register_participant,
    save_llm_message,
    save_submission,
    mark_participant_completed
)

from llm import generate_llm_reply


# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="LLM Openness Experiment",
    layout="wide"
)

st.title("LLM Openness Experiment")


# =========================================================
# Experiment configuration
# =========================================================

# Maximum number of messages a participant can send to
# the LLM for each question.
#
# Change this value if desired.



TASK_INSTRUCTION = """
Develop a strategy for managing this ecosystem.
Explain why you chose this strategy and justify your reasoning.
"""


# =========================================================
# Initialize PostgreSQL
# =========================================================

@st.cache_resource
def setup_database():
    init_database()
    return True


setup_database()


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
"""
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
"""
    }
]


# =========================================================
# Initialize participant
# =========================================================

if "participant_id" not in st.session_state:

    st.session_state.participant_id = (
        uuid.uuid4().hex
    )


participant_id = (
    st.session_state.participant_id
)


# =========================================================
# Assign experimental condition
# =========================================================

if "question_order" not in st.session_state:
    st.session_state.question_order = random.sample(
        QUESTION_BANK,
        k=len(QUESTION_BANK)
    )


QUESTIONS = st.session_state.question_order




# =========================================================
# Register participant
# =========================================================



register_participant(
    participant_id=participant_id,
    condition=None
)


# =========================================================
# Initialize experiment state
# =========================================================

if "current_question" not in st.session_state:

    st.session_state.current_question = 0


if "answers" not in st.session_state:

    st.session_state.answers = {
        question_nr: ""
        for question_nr
        in range(len(QUESTIONS))
    }


if "llm_messages" not in st.session_state:

    st.session_state.llm_messages = {
        question_nr: []
        for question_nr
        in range(len(QUESTIONS))
    }


if "submitted" not in st.session_state:

    st.session_state.submitted = False


question_index = (
    st.session_state.current_question
)
if question_index == 0:
    condition = "baseline"
else:
    condition = "openness"  

# =========================================================
# Completed screen
# =========================================================

if st.session_state.submitted:

    st.success(
        "Your answers have been submitted successfully."
    )

    st.write(
        "Thank you for participating."
    )

    st.stop()


# =========================================================
# Progress
# =========================================================

st.progress(
    (question_index + 1) / len(QUESTIONS),
    text=(
        f"Question {question_index + 1} "
        f"of {len(QUESTIONS)}"
    )
)


# =========================================================
# Display current question
# =========================================================
current_question = QUESTIONS[question_index]

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


# This is what the LLM receives as context.
# It contains both the scenario and the task.

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
    gap="large"
)


# =========================================================
# Participant answer
# =========================================================

with answer_column:

    st.markdown(
        "### Your answer"
    )

    st.caption(
        "Write your final answer here. "
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
        label_visibility="collapsed"
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


    conversation = (
        st.session_state.llm_messages[
            question_index
        ]
    )


    # -----------------------------------------------------
    # Count participant prompts
    # -----------------------------------------------------

    number_of_prompts = sum(
        1
        for message in conversation
        if message["role"] == "user"
    )






    # -----------------------------------------------------
    # Display conversation
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # LLM input
    # -----------------------------------------------------




    with st.form(
        key=(
            f"llm_form_"
            f"{question_index}"
        ),
        clear_on_submit=True
    ):

        llm_prompt = st.text_area(
            "Message the LLM:",
            height=100,
            placeholder=(
                "Type your message here..."
            )
        )

        send_clicked = (
            st.form_submit_button(
                "Send",
                type="primary",
                use_container_width=True
            )
        )


    # -----------------------------------------------------
    # Handle LLM request
    # -----------------------------------------------------

    if send_clicked:

        prompt = llm_prompt.strip()


        if not prompt:

            st.warning(
                "Please enter a message."
            )

        else:

            # Preserve the answer currently visible
            # in the answer box before rerunning.

            st.session_state.answers[
                question_index
            ] = st.session_state[
                answer_widget_key
            ]


            message_nr = (
                number_of_prompts + 1
            )


            # ---------------------------------------------
            # Add participant message to conversation
            # ---------------------------------------------

            user_message = {
                "role": "user",
                "content": prompt
            }


            conversation.append(
                user_message
            )


            # ---------------------------------------------
            # Save participant message to PostgreSQL
            # ---------------------------------------------

            try:

                save_llm_message(
                    participant_id=participant_id,
                    question_nr=(
                        question_index + 1
                    ),
                    message_nr=message_nr,
                    role="user",
                    content=prompt
                )

            except Exception as error:

                print(
                    "Database error while "
                    "saving user LLM message:",
                    repr(error)
                )

                # Remove message from local conversation
                # because database storage failed.

                conversation.pop()

                st.error(
                    "Your message could not be saved. "
                    "Please inform the researcher."
                )

                st.stop()


            # ---------------------------------------------
            # Generate assistant response
            # ---------------------------------------------

            try:

                with st.spinner(
                    "Generating response..."
                ):

                    assistant_response = (
                        generate_llm_reply(
                            question=full_problem,
                            condition=condition,
                            conversation=conversation
                        )
                    )


            except Exception as error:

                print(
                    "LLM API error:",
                    repr(error)
                )

                st.error(
                    "The LLM could not respond. "
                    "Please try again."
                )


            else:

                # -----------------------------------------
                # Add assistant message locally
                # -----------------------------------------

                assistant_message = {
                    "role": "assistant",
                    "content": assistant_response
                }


                conversation.append(
                    assistant_message
                )


                # -----------------------------------------
                # Save assistant response
                # -----------------------------------------

                try:

                    save_llm_message(
                        participant_id=participant_id,
                        question_nr=(
                            question_index + 1
                        ),
                        message_nr=message_nr,
                        role="assistant",
                        content=assistant_response
                    )

                except Exception as error:

                    print(
                        "Database error while "
                        "saving assistant message:",
                        repr(error)
                    )

                    st.error(
                        "The LLM response could not "
                        "be saved. Please inform "
                        "the researcher."
                    )

                else:

                    st.rerun()


# =========================================================
# Temporarily save answer
# =========================================================

def temporarily_save_current_answer():
    """
    Save the currently visible answer from the widget
    into the experiment's answer dictionary.
    """

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
        use_container_width=True
    )


with next_column:

    if question_index < len(QUESTIONS) - 1:

        next_clicked = st.button(
            "Next question →",
            type="primary",
            use_container_width=True
        )

        submit_clicked = False

    else:

        next_clicked = False

        submit_clicked = st.button(
            "Submit answers",
            type="primary",
            use_container_width=True
        )


# =========================================================
# Handle navigation
# =========================================================

if previous_clicked:

    temporarily_save_current_answer()

    st.session_state.current_question -= 1

    st.rerun()


if next_clicked:

    temporarily_save_current_answer()

    st.session_state.current_question += 1

    st.rerun()


# =========================================================
# Final submission
# =========================================================

if submit_clicked:

    temporarily_save_current_answer()


    unanswered_questions = [

        question_nr + 1

        for (
            question_nr,
            answer
        )
        in st.session_state.answers.items()

        if not answer.strip()
    ]


    if unanswered_questions:

        unanswered_text = ", ".join(
            str(number)
            for number
            in unanswered_questions
        )


        st.error(
            "Please answer all questions before "
            "submitting. "
            f"Missing: question {unanswered_text}."
        )


    else:

        try:

            for (
                question_nr,
                answer
            ) in st.session_state.answers.items():

                save_submission(
                    participant_id=participant_id,
                    question_nr=question_nr + 1,
                    response_type="final",
                    content=answer.strip()
                )


            mark_participant_completed(
                participant_id
            )


        except Exception as error:

            print(
                "Database save error:",
                repr(error)
            )

            st.error(
                "Your answers could not be saved. "
                "Please inform the researcher."
            )


        else:

            st.session_state.submitted = True

            st.rerun()


# =========================================================
# Answer progress
# =========================================================

with st.expander(
    "View answer progress"
):

    # Make sure the current visible answer
    # is represented correctly in the status display.

    current_visible_answer = (
        st.session_state[
            answer_widget_key
        ]
    )


    for (
        question_nr,
        answer
    ) in st.session_state.answers.items():

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
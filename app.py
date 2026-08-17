import uuid

import streamlit as st

from database import (
    init_database,
    register_participant,
    save_submission,
    mark_participant_completed
)


# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="LLM Openness Experiment",
    layout="wide"
)

st.title("LLM Openness Experiment")


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

QUESTIONS = [
    """
    A municipality is considering introducing a new environmental policy.
    Discuss the possible advantages, disadvantages, uncertainties, and
    perspectives that should be considered.
    """,

    """
    A nature reserve is considering limiting visitor access to protect
    biodiversity. Discuss the possible advantages, disadvantages,
    uncertainties, and perspectives that should be considered.
    """
]


# =========================================================
# Initialize participant
# =========================================================

if "participant_id" not in st.session_state:

    # Full UUID rather than only first 10 characters
    st.session_state.participant_id = uuid.uuid4().hex


participant_id = st.session_state.participant_id


# Ensure participant exists in PostgreSQL.
# This is safe to run repeatedly because register_participant()
# uses ON CONFLICT DO NOTHING.
register_participant(
    participant_id=participant_id
)


# =========================================================
# Initialize experiment state
# =========================================================

if "current_question" not in st.session_state:
    st.session_state.current_question = 0


if "answers" not in st.session_state:
    st.session_state.answers = {
        question_nr: ""
        for question_nr in range(len(QUESTIONS))
    }


if "submitted" not in st.session_state:
    st.session_state.submitted = False


question_index = st.session_state.current_question


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

st.subheader(
    f"Question {question_index + 1}"
)

st.write(
    QUESTIONS[question_index]
)


answer_widget_key = (
    f"answer_widget_{question_index}"
)


if answer_widget_key not in st.session_state:

    st.session_state[answer_widget_key] = (
        st.session_state.answers[question_index]
    )


st.text_area(
    "Describe your thoughts:",
    height=200,
    key=answer_widget_key
)


def temporarily_save_current_answer():
    """
    Save the visible answer to session state.
    """

    st.session_state.answers[question_index] = (
        st.session_state[answer_widget_key]
    )


# =========================================================
# Navigation
# =========================================================

previous_column, middle_column, next_column = (
    st.columns([1, 3, 1])
)


with previous_column:

    previous_clicked = st.button(
        "← Previous question",
        disabled=question_index == 0,
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
            "Please answer all questions before submitting. "
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

            # Technical details appear only in server logs.
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

    for (
        question_nr,
        answer
    ) in st.session_state.answers.items():

        status = (
            "Answered"
            if answer.strip()
            else "Not answered"
        )

        st.write(
            f"Question {question_nr + 1}: "
            f"**{status}**"
        )
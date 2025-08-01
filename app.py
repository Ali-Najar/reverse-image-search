import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import streamlit as st
from get_bio_markdown import get_markdown

# ------------ Page setup ------------
st.set_page_config(page_title="Reverse Image Search", page_icon="🔍", layout="centered")

st.markdown(
    """
    <style>
        /* Hide Streamlit default header */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        .chat-container {
            max-width: 700px;
            margin: 0 auto;
        }
        .msg {
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 12px;
            line-height: 1.6;
        }
        .user {
            background-color: transparent; /* Remove blue background */
            padding: 0;
            border: none;
            text-align: center;
        }
        .bot {
            background-color: #f0f0f0;
            color: #262730;
            border-bottom-left-radius: 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

history = st.session_state.history


with st.form(key="chat_form", clear_on_submit=True):
    url = st.text_input("Paste image URL and press Enter", placeholder="https://...")
    submitted = st.form_submit_button("Enter")


if submitted and url:
    st.session_state.history.clear()
    if "image_url" in st.session_state:
        del st.session_state.image_url

    # Show user message immediately
    history.append(("user", url))
    with st.spinner("Generating result …"):
        try:
            response_markdown = get_markdown(url)
        except Exception as e:
            response_markdown = f"**Error:** {e}"
    history.append(("assistant", response_markdown))
    st.session_state.image_url = url
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ------------ Generated Results Section ------------
assistant_messages = [msg for role, msg in history if role == "assistant"]
if assistant_messages:
    st.markdown("---")
    if "image_url" in st.session_state:
        left, center, right = st.columns([1, 2, 1])
        with center:
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <img src="{st.session_state.image_url}" width="200" />
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Biography")
    st.markdown(assistant_messages[-1], unsafe_allow_html=True) 
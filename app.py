import streamlit as st
from get_bio_markdown import get_markdown

# ------------ Page setup ------------
st.set_page_config(page_title="Reverse Image Search", page_icon="🔍", layout="centered")

# Inject a bit of CSS to mimic ChatGPT look & feel
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

# ------------ Helper & state ------------
if "history" not in st.session_state:
    # Each item: (role, content)
    st.session_state.history = []

history = st.session_state.history


# ------------ Input area ------------
with st.form(key="chat_form", clear_on_submit=True):
    url = st.text_input("Paste image URL and press Enter", placeholder="https://...")
    submitted = st.form_submit_button("Enter")

# ------------ Chat display ------------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for role, content in history:
    if role == "user":
        # Display the image instead of raw URL text
        st.markdown(
            f'<div class="msg user"><img src="{content}" style="width:200px; border-radius:8px;"/></div>',
            unsafe_allow_html=True,
        )
st.markdown('</div>', unsafe_allow_html=True)

if submitted and url:
    # Show user message immediately
    history.append(("user", url))
    with st.spinner("Generating result …"):
        try:
            response_markdown = get_markdown(url)
        except Exception as e:
            response_markdown = f"**Error:** {e}"
    history.append(("assistant", response_markdown))
    # Save current image URL for display below chat
    st.session_state.image_url = url
    # Trigger a fresh render; handle both new and legacy Streamlit APIs
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ------------ Generated Results Section ------------
assistant_messages = [msg for role, msg in history if role == "assistant"]
if assistant_messages:
    st.markdown("---")
    st.markdown("### Biography")
    # Display the latest assistant response
    st.markdown(assistant_messages[-1], unsafe_allow_html=True) 
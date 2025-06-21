# --- Imports ---
import os
import json
import streamlit as st
from streamlit import rerun
import speech_recognition as sr
import base64
from gtts import gTTS
from datetime import datetime
from collections import defaultdict
from langchain.memory import ConversationBufferWindowMemory
from deep_translator import GoogleTranslator
import re
import emoji
import uuid
from io import BytesIO
from openai import OpenAI
import time  # added for retry delay

# --- Constants ---
LANGUAGE_MAP = {
    "English": "en", "Assamese": "as", "Bengali": "bn", "Gujarati": "gu", "Hindi": "hi", "Kannada": "kn",
    "Malayalam": "ml", "Marathi": "mr", "Nepali": "ne", "Odia": "or", "Punjabi": "pa", "Sindhi": "sd",
    "Tamil": "ta", "Telugu": "te", "Urdu": "ur"
}

SPEECH_RECOGNITION_LANG_MAP = {
    "English": "en-IN", "Assamese": "as-IN", "Bengali": "bn-IN", "Gujarati": "gu-IN", "Hindi": "hi-IN",
    "Kannada": "kn-IN", "Malayalam": "ml-IN", "Marathi": "mr-IN", "Nepali": "ne-NP", "Odia": "or-IN",
    "Punjabi": "pa-IN", "Sindhi": "sd-IN", "Tamil": "ta-IN", "Telugu": "te-IN", "Urdu": "ur-IN"
}

# --- Initialize OpenAI client ---

# --- Utility Functions ---
def clean_text_for_speech(text, language):
    text = emoji.replace_emoji(text, replace='')
    return re.sub(r"[^\w\s.,!?]" if language == "English" else r"[\*\-\^\$#@!~_+=\[\]{}()<>]", "", text)

def speak_text(text, language):
    lang_code = LANGUAGE_MAP.get(language, "en")
    cleaned_text = clean_text_for_speech(text, language)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            tts = gTTS(text=cleaned_text, lang=lang_code)
            mp3_fp = BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            b64_audio = base64.b64encode(mp3_fp.read()).decode()

            st.markdown(
                f'<audio autoplay controls>'
                f'<source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">'
                f'</audio>',
                unsafe_allow_html=True
            )
            break  # success, exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)  # wait 2 seconds before retrying
            else:
                st.error(f"❌ Error in text-to-speech: {e}")

def load_user_data():
    if os.path.exists("user_data.json"):
        with open("user_data.json", "r") as f:
            return json.load(f)
    return {"history": [], "bookmarks": []}

def save_user_data(data):
    with open("user_data.json", "w") as f:
        json.dump(data, f, indent=4)

def get_response_online(prompt, context):
    system_message = (
        "🤖 As a legal chatbot specializing in the Indian Penal Code and Department of Justice services, provide accurate answers."
    )
    messages = [
        {"role": "system", "content": system_message},
        {"role": "system", "content": f"🏛 CONTEXT: {context}"},
        {"role": "user", "content": prompt},
    ]
    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=messages,
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",
                "X-Title": "<YOUR_SITE_NAME>",
            },
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ Error calling OpenAI API: {e}"

def reset_conversation():
    st.session_state.messages = []
    st.session_state.memory.clear()
    st.session_state.user_data["history"] = []
    st.session_state.last_response = ""
    save_user_data(st.session_state.user_data)
    rerun()

# --- UI Configuration ---
st.set_page_config(page_title="⚖️ CHATBOT", layout="wide")
st.header("🤖 AI-Based Interactive Chatbot for Law and Justice Services")

# --- Initialize Session State ---
if "user_data" not in st.session_state:
    st.session_state.user_data = load_user_data()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferWindowMemory(k=2, memory_key="chat_history", return_messages=True)
if "last_response" not in st.session_state:
    st.session_state.last_response = ""

user_data = st.session_state.user_data

# --- Sidebar ---
with st.sidebar:
    st.title("🧑‍⚖️ C.H.A.T.B.O.T")
    st.image("C:\\Users\\pravalika\\Chatbot_Major\\Chatbot\\images\\intro1.png", use_container_width=True)

    st.markdown("""
        <style>
        body, .stApp { background-color: #ffffff; color: black; }
        .sidebar .sidebar-content { background-color: #f7f7f7; }
        .stButton button, .stSelectbox div, .stRadio div {
            color: black; background-color: #e0e0e0;
        }
        .stButton:hover, .stSelectbox:hover, .stRadio:hover {
            background-color: #d0d0d0;
        }
        </style>
    """, unsafe_allow_html=True)

    model_mode = st.toggle("🌐 Online Mode", value=True)
    selected_language = st.selectbox("🌍 Select Language", list(LANGUAGE_MAP.keys()))

    if st.checkbox("📜 Chat History"):
        with st.expander("📂 View Chat History", expanded=False):
            st.write("### 📝 Past Conversations")
            grouped_history = defaultdict(list)
            for chat in user_data["history"]:
                date_key = chat.get("timestamp", "").split(" ")[0]
                grouped_history[date_key].append(chat)

            for date in sorted(grouped_history.keys(), reverse=True):
                st.markdown(f"#### 📅 {date}")
                for chat in grouped_history[date]:
                    st.markdown(f"*{chat['role'].capitalize()}* ({chat['timestamp']}): {chat['content']}")

        if st.button("⬇️ Download Chat History"):
            history_text = "\n\n".join(
                f"{chat.get('timestamp', '')} - {chat['role'].capitalize()}: {chat['content']}"
                for chat in user_data["history"]
            )
            st.download_button("📥 Save as .txt", history_text, file_name="chat_history.txt")

        if st.button("🧹 Clear Chat History"):
            user_data["history"] = []
            save_user_data(user_data)
            st.success("✅ Chat history cleared!")

    if st.checkbox("🔖 View Bookmarks"):
        st.write("### 📌 Bookmarked Responses")
        if user_data["bookmarks"]:
            for i, bookmark in enumerate(user_data["bookmarks"], 1):
                st.write(f"📍 {i}. {bookmark}")
        else:
            st.info("No bookmarks found.")
        if st.button("🧹 Clear All Bookmarks"):
            user_data["bookmarks"] = []
            save_user_data(user_data)
            st.success("✅ All bookmarks cleared!")

# --- Input Section ---
col1, col2 = st.columns([5, 1])
with col1:
    input_prompt = st.chat_input("💬 Ask a legal question in your selected language")

with col2:
    if st.button("🎤 Speak"):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎙️ Listening... Speak now!")
            recognizer.adjust_for_ambient_noise(source)
            try:
                speech_recog_lang = SPEECH_RECOGNITION_LANG_MAP.get(selected_language, "en-IN")
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
                input_prompt = recognizer.recognize_google(audio, language=speech_recog_lang)
                st.success(f"🗣️ Recognized: {input_prompt}")
            except sr.WaitTimeoutError:
                st.warning("⚠️ Listening timed out. Please speak clearly within 10 seconds.")
            except sr.UnknownValueError:
                st.warning("⚠️ Sorry, I couldn't understand. Please try again.")
            except sr.RequestError:
                st.error("❌ Error in recognizing speech.")

# --- Chat Processing ---
if input_prompt:
    if selected_language != "English":
        input_prompt = GoogleTranslator(source=selected_language.lower(), target="en").translate(input_prompt)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": input_prompt, "timestamp": timestamp})
    user_data["history"].append({"role": "user", "content": input_prompt, "timestamp": timestamp})
    save_user_data(user_data)

    with st.chat_message("user"):
        st.markdown(f"👤 {input_prompt} \n\n🕒 {timestamp}")

    with st.chat_message("assistant"):
        context = ""
        if model_mode:
            full_response = get_response_online(input_prompt, context)
        else:
            full_response = "⚡ Offline mode not ready."

        if selected_language != "English":
            full_response = GoogleTranslator(source="en", target=selected_language.lower()).translate(full_response)

        st.write(f"🤖 {full_response}")
        word_count = len(full_response.split())
        st.caption(f"📝 Word Count: {word_count}")
        speak_text(full_response, selected_language)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data["history"].append({
            "role": "assistant",
            "content": full_response,
            "timestamp": timestamp,
            "word_count": word_count
        })
        save_user_data(user_data)
        st.session_state.last_response = full_response

# --- Bookmarking and Reset ---
if st.session_state.last_response and st.button("🔖 Bookmark Response"):
    user_data["bookmarks"].append(st.session_state.last_response)
    save_user_data(user_data)
    st.success("✅ Response Bookmarked!")

if st.button("🗑️ Reset Conversation"):
    reset_conversation()

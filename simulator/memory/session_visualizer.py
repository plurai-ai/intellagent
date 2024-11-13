import streamlit as st
import pandas as pd
import sqlite3
import os
from pathlib import Path


def get_last_created_directory(path):
    # Convert path to Path object for convenience
    if not os.path.isdir(path):
        return None
    path = Path(path)

    # Get all directories in the specified path
    directories = [d for d in path.iterdir() if d.is_dir()]

    # Sort directories by creation time (newest first) and get the first one
    last_created_dir = max(directories, key=lambda d: d.stat().st_ctime, default=None)

    return last_created_dir

def get_last_db():
    # Get the last created db in the default result path
    last_dir = get_last_created_directory("./results")
    if last_dir is None:
        return None

    # Get the last created database file in the last created directory
    last_exp = get_last_created_directory(last_dir)
    if os.path.isfile(last_exp / "memory.db"):
        last_db = last_exp / "memory.db"
        return str(last_db)
    return None

def add_dataframe(self, df):
    """Add a DataFrame to the log display as a table."""
    html_table = df.to_html(classes='dataframe', index=False, escape=False)
    self.log_messages.append(f"<div style='color:lightgreen;'>{html_table}</div>")  # Styling for the table


class Logger:
    """A custom logging handler that outputs styled logs to a Streamlit markdown component."""

    def __init__(self, back_color= 'black'):
        self.log_messages = []
        self.back_color = back_color

    def log_message(self,message, mode):
        """Logs a message with the specified mode."""
        # Add HTML styling based on the mode
        if mode == 'debug':
            styled_entry = f'<span style="color:green;">{message}</span>'
        elif mode == 'info':
            styled_entry = f'<span style="color:#003366;">{message}</span>'
        elif mode == 'warning':
            styled_entry = f'<span style="color:orange;">{message}</span>'
        elif mode == 'error':
            styled_entry = f'<span style="color:red;">{message}</span>'
        elif mode == 'table':
            df = pd.read_json(message)
            html_table = df.to_html(classes='dataframe', index=False, escape=False)
            styled_entry = f"<div style='color:lightgreen;'>{html_table}</div>"  # Styling for the table
        else:
            styled_entry = message  # Default for other modes

        self.log_messages.append(styled_entry)

    def get_markdown(self):
        mk = f"<div style='background-color:{self.back_color}; padding:10px; height:500px; overflow:auto;' id='logDiv'>{'<br>'.join(self.log_messages)}<br></div>"
        return mk


def extract_threads(memory_path):
    # Extract unique thread ids from the database
    conn = sqlite3.connect(memory_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT thread_id FROM Dialog")
    unique_values = [row[0] for row in cursor.fetchall()]
    conn.close()
    return unique_values

def update_thread_list():
    # Update the thread list in the session state
    thread_list = extract_threads(st.session_state["memory_path"])
    st.session_state["threads"] = thread_list


def on_select_thread():
    conn = sqlite3.connect(st.session_state["memory_path"])
    cursor = conn.cursor()
    thread_id = st.session_state["selected_thread"]

    st.session_state["chatbot_log"] = "Updated Content for Selected Thread"

    with col2:
        cursor.execute("SELECT * FROM Dialog WHERE thread_id = ? ORDER BY time ASC", (thread_id,))
        rows = cursor.fetchall()
        for row in rows:
            if row[1] == 'AI':
                st.chat_message('AI').write(row[2])
            else:
                st.chat_message('User').write(row[2])
    with col1:
        cursor.execute("SELECT * FROM Tools WHERE thread_id = ? ORDER BY time ASC", (thread_id,))
        rows = cursor.fetchall()
        for row in rows:
            logger_chat.log_message(f"- Invoke function: {row[1]}", 'debug')
            logger_chat.log_message(f"+ Args: {row[2]}", 'info')
            if 'Error:' in row[3]:
                logger_chat.log_message(f'Response:<br>{row[3]}<br>----------<br>', 'error')
            else:
                logger_chat.log_message(f'Response:<br>{row[3]}<br>----------<br>', 'warning')
        mk = logger_chat.get_markdown()
        st.markdown(mk, unsafe_allow_html=True)

    with col3:
        cursor.execute("SELECT * FROM Thoughts WHERE thread_id = ? ORDER BY time ASC", (thread_id,))
        rows = cursor.fetchall()
        for row in rows:
            if row[1] == '':
                continue
            logger_user.log_message(row[1] + '<br>', 'info')
        mk = logger_user.get_markdown()
        st.markdown(mk, unsafe_allow_html=True)

st.set_page_config( layout="wide")


col1, divider1, col2, divider2, col3 = st.columns([100,5 ,200,5, 100])
logger_user = Logger(back_color='#D3D3D3')
logger_chat = Logger()
with divider1:
    st.markdown(
        """
        <div style='height: 100vh; width: 1px; background-color: gray;'></div>
        """,
        unsafe_allow_html=True
    )
with divider2:
    st.markdown(
        """
        <div style='height: 100vh; width: 1px; background-color: gray;'></div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        "<h1 style='text-align: center;'>"
        "🕵️ Plurai dialog</h1>",
        unsafe_allow_html=True
    )

with col1:
    st.markdown("<h1 style='font-size: 20px;'>ChatBot logging 📝</h1>", unsafe_allow_html=True)
    st.session_state["chatbot_log"] = st.empty()

with col3:
    st.markdown("<h1 style='font-size: 20px;'>User thoughts 🧠</h1>", unsafe_allow_html=True)
    st.session_state["user_log"] = st.empty()

if "threads" not in st.session_state:
    st.session_state["threads"] = []

def main():
    # Set the initial db path to the last run in the default results path
    last_db_path = get_last_db()

    st.text_input('Memory path', key='memory_path', on_change=update_thread_list,
                  value=last_db_path)
    st.session_state["threads"] = extract_threads(last_db_path)
    st.selectbox("Select a thread to visualized:", st.session_state["threads"],
                                  key="selected_thread",
                                  on_change=on_select_thread
                                  )
    # Store chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

if __name__ == "__main__":
    main()
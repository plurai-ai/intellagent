import streamlit as st
import pandas as pd
import sqlite3
import sys
from pathlib import Path
import os
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))
from simulator.utils.file_reading import get_last_db
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
    if memory_path is None:
        return [], []
    dir_name = os.path.dirname(memory_path)
    results_path = os.path.join(dir_name, 'results.csv')
    if not os.path.isfile(results_path):
        raise FileNotFoundError(f"Results file not found at {results_path}")
    df = pd.read_csv(results_path)
    df = df.sort_values(by='id', ascending=True, inplace=False)
    event_list = df['id'].tolist()
    event_list = [str(event) for event in event_list]
    thread_list = df['thread_id'].tolist()
    return event_list, thread_list

def update_thread_list():
    # Update the thread list in the session state
    st.session_state.updated = True
    event_id, thread_list = extract_threads(st.session_state["memory_path"])
    st.session_state["threads"] = thread_list
    st.session_state["event_id"] = event_id


def on_select_thread():
    conn = sqlite3.connect(st.session_state["memory_path"])
    cursor = conn.cursor()
    event_id = st.session_state["selected_event"]
    thread_id = st.session_state["threads"][st.session_state["event_id"].index(event_id)]

    if thread_id is None:
        st.error("Thread ID is None. Cannot execute the query.")
        return

    st.session_state["chatbot_log"] = "Updated Content for Selected Thread"

    try:
        with col2:
            cursor.execute("SELECT * FROM Dialog WHERE thread_id = ? ORDER BY time ASC", (thread_id,))
            rows = cursor.fetchall()
            for i,row in enumerate(rows):
                if row[1] == 'AI':
                    st.chat_message('AI').write(row[2])
                else:
                    # Skip the last message if it's a stop signal and not the end message
                    if '###STOP' in row[2] and i < len(rows)-1:
                        continue
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
    except sqlite3.Error as e:
        st.error(f"An error occurred while executing the query: {e}")
    finally:
        conn.close()

st.set_page_config(page_title="Session vizualization", page_icon="./docs/plurai_icon.png", layout="wide")



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
        "🕵️ IntellAgent dialog</h1>",
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
    st.session_state["event_id"] = []

def main():
    # Set the initial db path to the last run in the default results path
    last_db_path = get_last_db()
    if 'last_db_path' not in st.session_state:
        st.session_state.last_db_path = get_last_db()
        st.session_state["event_id"], st.session_state['threads'] = extract_threads(last_db_path)

    st.sidebar.text_input('Memory path', key='memory_path', on_change=update_thread_list,
                  value=st.session_state.last_db_path)

    st.sidebar.selectbox("Select an event to visualized:", st.session_state["event_id"],
                                  key="selected_event",
                                  on_change=on_select_thread
                                  )
    # Store chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

if __name__ == "__main__":
    main()

import sqlite3
import threading
from typing import Optional
import time
from simulator.healthcare_analytics import ExceptionEvent, track_event

class SqliteSaver:
    """A checkpoint saver that stores checkpoints in a SQLite database.
    This class is a inspired by:
    https://github.com/langchain-ai/langgraph/blob/a73f9affab7d7fb1cca477f055a4d503563332d8/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py
    """


    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.cursor = self.conn.cursor()
        self.init_tables()


    def init_tables(self):
        """
        Creates three tables: Dialog, Thoughts, and Tools in the specified SQLite database.

        Parameters:
        db_path (str): Path to the SQLite3 database file.
        """
        try:
            # Dialog table with a 'time' column to store Unix timestamps
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Dialog (
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    time INTEGER NOT NULL,
                    PRIMARY KEY (thread_id, message, time)
                )
            ''')

            # Thoughts table with a 'time' column for Unix timestamp
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Thoughts (
                    thread_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    time INTEGER NOT NULL,
                    PRIMARY KEY (thread_id, message, time)
                )
            ''')

            # Tools table with a 'time' column for Unix timestamp
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Tools (
                    thread_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    input TEXT,
                    output TEXT,
                    time INTEGER NOT NULL,
                    PRIMARY KEY (thread_id, tool_name, time)
                )
            ''')

            # Commit the transaction
            self.conn.commit()
            print("Tables created successfully.")

        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))

    def exit(self):
        # Commit any changes and close the connection when exiting the context
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()

    def insert_dialog(self, thread_id: str, role: str, message: str):
        try:
            with self.lock:
                current_time = int(time.time() * 1000) # in milliseconds
                self.cursor.execute(
                    "INSERT INTO Dialog (thread_id, role, message, time) VALUES (?, ?, ?, ?)",
                    (thread_id, role, message, current_time)
                )
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while inserting into Dialog: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))
            
    def insert_thought(self, thread_id: str, message: str):
        try:
            with self.lock:
                current_time = int(time.time() * 1000) # in milliseconds
                self.cursor.execute(
                    "INSERT INTO Thoughts (thread_id, message, time) VALUES (?, ?, ?)",
                    (thread_id, message, current_time)
                )
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while inserting into Thoughts: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))

    def insert_tool(self, thread_id: str, tool_name: str, input: Optional[str], output: Optional[str]):
        try:
            with self.lock:
                current_time = int(time.time() * 1000) # in milliseconds
                self.cursor.execute(
                    "INSERT INTO Tools (thread_id, tool_name, input, output, time) VALUES (?, ?, ?, ?, ?)",
                    (thread_id, tool_name, input, output, current_time)
                )
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while inserting into Tools: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))
            


    def read_dialog(self, thread_id: str):
        try:
            self.cursor.execute("SELECT thread_id, role, message FROM Dialog WHERE thread_id = ?", (thread_id,))
            rows = self.cursor.fetchall()
            return rows if rows else None  # Return None if no rows are found
        except sqlite3.Error as e:
            print(f"An error occurred while reading from Dialog: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))
            return None

    def read_thought(self, thread_id: str):
        try:
            self.cursor.execute("SELECT thread_id, message FROM Thoughts WHERE thread_id = ?", (thread_id,))
            rows = self.cursor.fetchall()
            return rows if rows else None  # Return None if no rows are found
        except sqlite3.Error as e:
            print(f"An error occurred while reading from Thoughts: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))
            return None

    def read_tool(self, thread_id: str):
        try:
            self.cursor.execute("SELECT * FROM Tools WHERE thread_id = ?", (thread_id,))
            rows = self.cursor.fetchall()
            return rows if rows else None  # Return None if no rows are found
        except sqlite3.Error as e:
            print(f"An error occurred while reading from Tools: {e}")
            track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=str(e)))
            return None

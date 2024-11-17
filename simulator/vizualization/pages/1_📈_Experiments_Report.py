import os

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))
from simulator.utils.file_reading import get_latest_dataset
import numpy as np

st.set_page_config(page_title="Experiments report", page_icon="📈")


def update_db_path():
    # Update the thread list in the session state
    thread_list = extract_threads(st.session_state["memory_path"])
    st.session_state["threads"] = thread_list


# Load or generate experimental data
def read_experiment_data(exp_path: str):
    df = pd.read_csv(exp_path + '/results.csv')
    scores = df['score'].tolist()
    challenge = df['challenge_level'].tolist()
    return scores, challenge


@st.cache_data
def load_data():
    database_path = st.session_state.get('database_path', None)
    if database_path is None:
        return pd.DataFrame()
    # Example data: replace this with your actual data
    parent_dir = os.path.dirname(os.path.dirname(database_path)) + '/experiments'
    database_name = database_path.split('/')[-1]
    experiments_list = [x for x in os.listdir(parent_dir) if database_name in x]
    experiments_data = {}
    for exp in experiments_list:
        exp_path = parent_dir + '/' + exp
        scores, challenge = read_experiment_data(exp_path)
        exp_name = exp_path.split(database_name + '__')[-1]
        experiments_data[exp_name] = {'scores': scores, 'challenge_level': challenge}
    graph_data = []
    for exp, data in experiments_data.items():
        unique_values, counts = np.unique(data['challenge_level'], return_counts=True)
        unique_values = np.sort(unique_values)
        for val in unique_values:
            cur_valid_score = [data['scores'][i] for i in range(len(data['scores']))
                               if data['challenge_level'][i] <= val]
            if len(cur_valid_score) < 5: #Not enough data points
                continue
            graph_data.append({'experiment': exp, 'Challenge level': val,
                               'Success rate': sum(cur_valid_score) / len(cur_valid_score)})
    return pd.DataFrame(graph_data)


def app1_main():
    last_db_path = get_latest_dataset()
    st.sidebar.text_input('Database path', key='database_path', on_change=load_data,
                          value=last_db_path)

    data = load_data()

    # Sidebar for experiment selection
    st.sidebar.title("Select Experiments")
    experiments = st.sidebar.multiselect(
        "Choose experiments to visualize:",
        options=data['experiment'].unique(),
        default=data['experiment'].unique()
    )

    st.title("Combined Line Graph for Experiments")

    if experiments:
        # Filter data for selected experiments
        filtered_data = data[data['experiment'].isin(experiments)]

        # Plot all selected experiments on the same graph
        fig = px.line(
            filtered_data,
            x='Challenge level',
            y='Success rate',
            color='experiment',
            title="Comparison of Experiments",
            labels={"value": "Measured Value", "time": "Time"},
        )
        st.plotly_chart(fig)
    else:
        st.write("Please select at least one experiment to display.")


app1_main()

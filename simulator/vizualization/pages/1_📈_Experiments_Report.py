import os

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path
import ast

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))
from simulator.utils.file_reading import get_latest_dataset
import numpy as np

st.set_page_config(page_title="Experiments report", page_icon="📈")

def _format_arrow(val):
    return f"{abs(val):.0f}%" if val == 0 else f"{'↑' if val > 0 else '↓'} {abs(val):.0f}%"

def _format_percentage(val):
    if val < 0:
        return None
    else:
        return f"{val:.0f}%"
def _color_arrow(val):
    return "color: green" if val > 0 else "color: red" if val < 0 else "color: black"

def update_db_path():
    # Update the thread list in the session state
    thread_list = extract_threads(st.session_state["memory_path"])
    st.session_state["threads"] = thread_list


# Load or generate experimental data
def read_experiment_data(exp_path: str):
    df = pd.read_csv(exp_path + '/results.csv')
    scores = df['score'].tolist()
    challenge = df['challenge_level'].tolist()
    all_policies_list = []
    for i, row in df.iterrows():
        policies = ast.literal_eval(row['policies'])
        for policy in policies:
            all_policies_list.append({'policy': policy['flow'] + ': ' + policy['policy'],
                                      'score': row['score'], 'challenge_level': row['challenge_level']})

    policies_names = list(set([name['policy'] for name in all_policies_list]))
    success_rate = []
    for name in policies_names:
        cur_policies = [policy for policy in all_policies_list if policy['policy'] == name]
        if len(cur_policies) < 3:
            success_rate.append(-1)
            continue
        success_rate.append(100*sum([policy['score'] for policy in cur_policies]) / len(cur_policies))
    return scores, challenge, policies_names, success_rate


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
    policies_datasets = []
    for exp in experiments_list:
        exp_path = parent_dir + '/' + exp
        scores, challenge, policies_names, success_rate = read_experiment_data(exp_path)
        exp_name = exp_path.split(database_name + '__')[-1]
        experiments_data[exp_name] = {'scores': scores, 'challenge_level': challenge}
        policies_datasets.append( pd.DataFrame({'policy': policies_names, f'{exp_name}_success_rate': success_rate}))
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
    merged_df = policies_datasets[0]
    for df in policies_datasets[1:]:
        merged_df = pd.merge(merged_df, df, on="policy", how="outer")

    score_columns = [col for col in merged_df.columns if "success_rate" in col]
    print(score_columns)
    score_columns = sorted(score_columns, key=lambda x: int(x.split('_')[1]))
    mean_scores = merged_df[score_columns].apply(lambda row: row[row >= 0].mean(), axis=1)
    styled_col = []
    for col in score_columns:
        new_col = f"{col.split('success_rate')[0]}Deviation_from_mean"  # Create the new column name
        styled_col.append(new_col)
        merged_df[new_col] = merged_df[col] - mean_scores
        # Set values to NaN where the original score is <= 0
        merged_df.loc[merged_df[col] < 0, new_col] = None
    # Iterate through the columns and calculate the differences
    for i in range(1, len(score_columns)):
        current_col = score_columns[i]
        prev_col = score_columns[i - 1]
        new_col_name = f"{current_col.split('success_rate')[0]}_diff_from_prev"
        merged_df[new_col_name] = merged_df.apply(
            lambda row: None if row[current_col] == -1 or row[prev_col] == -1 else row[current_col] - row[prev_col],
            axis=1
        )
        styled_col.append(new_col_name)
    merged_df[score_columns] = merged_df[score_columns].applymap(_format_percentage)
    return pd.DataFrame(graph_data), merged_df, styled_col


def app1_main():
    last_db_path = get_latest_dataset()
    st.sidebar.text_input('Database path', key='database_path', on_change=load_data,
                          value=last_db_path)

    data, df_s, styled_col = load_data()
    df_s = df_s.set_index('policy')
    df_s = df_s.sort_index()

    df_s = df_s.style.format(_format_arrow, subset=styled_col).applymap(_color_arrow, subset=styled_col)


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
        st.dataframe(df_s)
    else:
        st.write("Please select at least one experiment to display.")


app1_main()

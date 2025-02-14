import os

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path
import ast
import json
pd.options.mode.chained_assignment = None

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))
from simulator.utils.file_reading import get_latest_dataset
import numpy as np

st.set_page_config(page_title="Experiments report", page_icon="../../../docs/plurai_icon.png")


def _format_arrow(val):
    if pd.isna(val):
        return val
    return f"{abs(val):.0f}%" if val == 0 else f"{'↑' if val > 0 else '↓'} {abs(val):.0f}%"


def _format_percentage(val):
    if val < 0:
        return None
    else:
        return f"{val:.0f}%"


def _format_binary(val):
    if val < 0:
        return None
    else:
        return f"{val:.0f}"


def _color_arrow(val):
    if pd.isna(val):
        return "color: black"
    return "color: green" if val > 0 else "color: red" if val < 0 else "color: black"


def _color_binary(val):
    return "color: green" if val > 0 else "color: red" if val <= 0 else "color: black"


def extract_violated_policies_str(row):
    # Parse the policies and indices
    try:
        policies = ast.literal_eval(row['policies'])
        violated_policies_ind = ast.literal_eval(row['violated_policies'])
        # Extract the violated policies
        violated_policies = [policies[j]['flow'] + ': ' + policies[j]['policy'] for j in violated_policies_ind]
    except:
        violated_policies = []
    return violated_policies


# Load or generate experimental data
def read_experiment_data(exp_path: str):
    df = pd.read_csv(exp_path + '/results.csv')
    try:
        err_df = pd.read_csv(exp_path + '/err_events.csv')
    except:
        err_df = pd.DataFrame(columns=['score', 'challenge_level'])
    policies_info = json.load(open(exp_path + '/policies_info.json', 'r'))
    policies_info_list = []
    for flow, policies in policies_info.items():
        for policy in policies:
            policies_info_list.append({'name': flow + ': ' + policy['policy'], 'category': policy['category']})
    all_policies_list = []
    for i, row in df.iterrows():
        policies = ast.literal_eval(row['policies'])
        try:
            policies_sublist = ast.literal_eval(row['policies_in_dialog'])
            violated_policies = ast.literal_eval(row['violated_policies'])
        except:
            policies_sublist = []
            violated_policies = []
        for j in policies_sublist:
            if j > len(policies)-1:
                continue
            score = 0 if j in violated_policies else 1
            all_policies_list.append({'policy': policies[j]['flow'] + ': ' + policies[j]['policy'],
                                      'score': score, 'challenge_level': row['challenge_level']})

    success_rate = []
    scores = df['score'].tolist() + err_df['score'].tolist()
    challenge = df['challenge_level'].tolist() + err_df['challenge_level'].tolist()
    for policy_info in policies_info_list:
        cur_policies = [policy for policy in all_policies_list if policy['policy'] == policy_info['name']]
        if len(cur_policies) < 3:
            success_rate.append(-1)
            continue
        success_rate.append(100 * sum([policy['score'] for policy in cur_policies]) / len(cur_policies))
    graph_info = {'scores': scores, 'challenge_level': challenge}
    table_policies_info = {'policy': [policy['name'] for policy in policies_info_list],
                           'success_rate': success_rate,
                           'category': [policy['category'] for policy in policies_info_list]}
    df['violated_policies'] = df.apply(extract_violated_policies_str, axis=1)
    events_info = df[['id', 'scenario', 'score', 'reason', 'violated_policies']]
    events_info['score'] = events_info['score'].astype(float)
    return graph_info, table_policies_info, events_info


def change_data():
    database_path = st.session_state.get('database_path', None)
    data, policies_df, styled_col, events_df = load_data(database_path)


@st.cache_data
def load_data(database_path=None):
    if database_path is None:
        return pd.DataFrame(), pd.DataFrame(), [], pd.DataFrame()
    # Example data: replace this with your actual data

    parent_dir = os.path.dirname(os.path.dirname(database_path)) + '/experiments'
    database_name = database_path.split('/')[-1]
    experiments_list = [x for x in os.listdir(parent_dir) if database_name in x]
    experiments_data = {}
    policies_datasets = []
    events_df = None
    if not experiments_list:
        print('No experiments found in the database')
        return pd.DataFrame(), pd.DataFrame(), [], pd.DataFrame()

    for exp in experiments_list:
        exp_path = parent_dir + '/' + exp
        if not os.path.isfile(exp_path + '/results.csv'):
            continue
        graph_info, table_policies_info, events_info = read_experiment_data(exp_path)
        exp_name = exp_path.split(database_name + '__')[-1]
        experiments_data[exp_name] = graph_info
        events_info = events_info.rename(columns={"score": f'{exp_name}_score'})
        events_info = events_info.rename(columns={"reason": f'{exp_name}_reason'})
        events_info = events_info.rename(columns={"violated_policies": f'{exp_name}_violated_policies'})
        if events_df is None:
            events_df = events_info
        else:
            events_df = pd.merge(events_df, events_info, on=["id", "scenario"], how="outer")

        policies_datasets.append(pd.DataFrame({'policy': table_policies_info['policy'],
                                               'category': table_policies_info['category'],
                                               f'{exp_name}_success_rate': table_policies_info['success_rate']}))
    graph_data = []
    for exp, data in experiments_data.items():
        unique_values, counts = np.unique(data['challenge_level'], return_counts=True)
        unique_values = np.sort(unique_values)
        for val in unique_values:
            cur_valid_score = [data['scores'][i] for i in range(len(data['scores']))
                               if data['challenge_level'][i] >= val]
            if len(cur_valid_score) < 5:  # Not enough data points
                continue
            graph_data.append({'experiment': exp, 'Challenge level': val,
                               'Success rate': sum(cur_valid_score) / len(cur_valid_score)})
    merged_df = policies_datasets[0]
    for df in policies_datasets[1:]:
        merged_df = pd.merge(merged_df, df, on=["policy","category"], how="outer")
    score_columns = [col for col in merged_df.columns if "success_rate" in col]

    # Sort according to string order
    score_columns = sorted(score_columns, key=lambda x: x.split('_')[1])

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
    merged_df[score_columns] = merged_df[score_columns].map(_format_percentage)
    column_all_sort = []
    for c in score_columns:
        column_all_sort.append(c)
        cur_s = [s for s in styled_col if c.split('success_rate')[0] in s]
        column_all_sort += cur_s

    merged_df = merged_df[['category', 'policy'] + column_all_sort]
    return pd.DataFrame(graph_data), merged_df, styled_col, events_df


def main():
    last_db_path = get_latest_dataset()
    st.sidebar.text_input('Database path', key='database_path', on_change=change_data,
                          value=last_db_path)
    database_path = st.session_state.get('database_path', None)
    data, policies_df, styled_col, events_df = load_data(database_path)
    if data.empty:
        st.write("The database you selected does not contain any experiments. Please select another database.")
        return
    policies_df = policies_df.set_index('policy')
    events_df = events_df.rename(columns={"id": 'event_id'})
    events_df = events_df.set_index('event_id')
    events_df = events_df.sort_index()
    policies_df = policies_df.sort_index()

    # Sidebar for experiment selection
    st.sidebar.title("Select Experiments")
    experiments = st.sidebar.multiselect(
        "Choose experiments to visualize:",
        options=data['experiment'].unique(),
        default=data['experiment'].unique()
    )

    st.title("Experiments Report")

    if experiments:
        # Filter data for selected experiments
        filtered_data = data[data['experiment'].isin(experiments)]
        unique_exp = filtered_data['experiment'].unique()

        # Plot all selected experiments on the same graph
        fig = px.line(
            filtered_data,
            x='Challenge level',
            y='Success rate',
            color='experiment',
            title="Comparison of Experiments success rate",
            labels={"value": "Measured Value", "time": "Time"},
        )
        fig.update_layout(
            xaxis_title="Threshold Value (Challenge Level)",
            yaxis_title="Success rate above threshold (%)",
        )
        st.plotly_chart(fig)
        unique_exp = [exp + '_' for exp in unique_exp]
        valid_columns = ['category'] + [col for col in policies_df.columns if any(expr in col for expr in unique_exp)]
        filtered_df = policies_df[valid_columns]
        cur_styled_col = [col for col in styled_col if col in valid_columns]
        filtered_df = filtered_df.style.format(_format_arrow, subset=cur_styled_col).map(_color_arrow,
                                                                                         subset=cur_styled_col)

        score_columns_filter = [col for col in events_df.columns if
                                'score' in col and any(expr in col for expr in unique_exp)]

        exp_columns = [col for col in events_df.columns if ('_score' in col) or ('_reason' in col) or
                       ('_violated_policies' in col)]
        exp_columns_filter = [col for col in exp_columns if any(expr in col for expr in unique_exp)]
        cur_events_df = events_df.drop(columns=[col for col in exp_columns if col not in exp_columns_filter])
        cur_events_df = cur_events_df.style.format(_format_binary, subset=score_columns_filter).map(_color_binary,
                                                                                                    subset=score_columns_filter)
        st.markdown("#### A table of policies scores in the selected experiments")
        st.dataframe(filtered_df)
        st.markdown("#### A table of events score in the selected experiments")
        st.dataframe(cur_events_df)
    else:
        st.write("Please select at least one experiment to display.")


main()

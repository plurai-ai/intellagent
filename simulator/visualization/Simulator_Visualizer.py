import os.path
import streamlit as st
base_path = './' if os.path.isfile('Simulator_Visualizer.py') else './simulator/visualization/'
st.set_page_config(
    page_title="Simulator Visualizer",
    page_icon= base_path + "images/plurai_icon.png",
)

st.image(base_path + 'images/plurai_logo.png', use_column_width=True)  # Added line to display the Plurai logo
st.write("# Welcome to Plurai Chat-Agent-Simulator (CHAS)!")

st.markdown(
    """
    **CHat-Agent-Simulator (CHAS)** is an AI-powered diagnostic framework driven by Large Language Models (LLMs) and AI agents. 
    This demo allows you to explore the capabilities of Plurai's chatbot simulator, which simulates thousands of edge-case scenarios to evaluate chatbot agents comprehensively.
    
    ### Why CHAS?
    CHAS empowers you to discover the unknown, identify failure points, and optimize capabilities, enabling you to deploy chat agents with confidence.
    
    ### Want to learn more?
    - Check out [Plurai.ai](https://plurai.ai)
"""
)

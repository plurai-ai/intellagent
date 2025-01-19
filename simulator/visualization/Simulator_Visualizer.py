import os.path
import streamlit as st
import base64
base_path = './' if os.path.isfile('Simulator_Visualizer.py') else './simulator/visualization/'
st.set_page_config(
    page_title="Simulator Visualizer",
    page_icon= base_path + "images/plurai_icon.png",
)


# Path to your image
image_path = base_path + 'images/plurai_logo.png'

# Read and encode the image to base64
with open(image_path, "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode()

# Define the target URL
target_url = "https://plurai.ai/"

# Create the HTML code for the clickable image
html_code = f'''
    <a href="{target_url}" target="_blank">
        <img src="data:image/png;base64,{encoded_image}" width="30%" style="display: block; margin-left: 0; margin-right: auto;" />
    </a>
'''

# Display the clickable image in Streamlit
st.markdown(html_code, unsafe_allow_html=True)

#st.image(base_path + 'images/plurai_logo.png', width=300)  # Added line to display the Plurai logo
st.write("### Welcome to Plurai IntellAgent!")

st.markdown(
    """
   **IntellAgent** is a multi-agent framework designed to provide fine-grained diagnostics for Conversational AI systems.
    This demo allows you to explore the capabilities of Plurai's chat-agent simulator, which simulates thousands of edge-case scenarios to discover failure points, performance gaps, and inform optimization decisions for chat-agents.

    #### Want to optimize your chat-agent and take it to the next level?
    - Check out [Plurai Booster](https://plurai.ai/#products)

    #### Want to learn more? Or need help with integration?
    - Contact us [Plurai.ai](https://plurai.ai/contact-us)
"""
)
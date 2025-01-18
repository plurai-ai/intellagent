<h1 align="center">
  <img style="vertical-align:middle" height="200"
  src="./docs/figures/logo.png">
</h1>
<p align="center">
  <i>Know Your Chat-Agent to Unleash Its Full Potential</i>
</p>

<p align="center">
    <!-- community badges -->
    <a href="https://discord.gg/YWbT87vAau"><img src="https://img.shields.io/badge/Join-Discord-blue.svg"/></a>
    <!-- license badge -->
    <a href="https://github.com/plurai-ai/chas/blob/main/LICENSE">
        <img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-green.svg"></a>
</p>

<h4 align="center">
    <p>
        <a href="https://chas-doc.plurai.ai/">Documentation</a> |
        <a href="#fire-quickstart">Quick start</a> |
        <a href="https://plurai.substack.com/">NewsLetter</a> |
        <a href="https://plurai.ai/blog/chas-announcement">Paper</a>
 </p>
</h4>




<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->


**Chat-Agent-Simulator (CHAS)** is a cutting-edge multi-agent framework designed to provide In-depth automated diagnostics for advanced chatbot systems, particularly those integrated with databases and tools. It simulates thousands of edge-case scenarios to comprehensively evaluate chatbot agents. By stress-testing your agent from all angles in wide-range of complexity levels, CHAS helps identify potential failure points and provides detailed performance analysis to ensure reliable deployment.

Don't limit your chatbot's potential because of what you don't know. Use CHAS to know exactly what your agent can handle, fix what it can't, and deploy with confidence.

## Key Features

- 🔬 **Generate Thousands of Edge-Case Scenarios:**  
  Automatically generate highly realistic edge-case scenarios tailored specifically to your chat agent.

- 🤖 **Simulate Diverse User Interactions:**  
  Evaluate your agent across a wide spectrum of scenarios with varying complexity levels.

- 📊 **Comprehensive Performance Evaluations:**  
  Access detailed metrics, including success rates across policies, tools, and complexity tiers, to uncover strengths and areas for improvement.

- 💪 **Confident Deployment of Robust Chat Agents:**  
  Deploy chat agents that are reliable, resilient, and ready for real-world interactions.



> To understand the key concepts and how the CHAS system operates, refer to the [system overview guide](https://chas-doc.plurai.ai/How_it_Works/how-it-works/)

## 🔍 Demo

![simulator_recording](./docs/simulator_recording.gif)

## :fire: Quickstart

> For a more detailed and comprehensive guide, see the [Start Guide](https://chas-doc.plurai.ai/quick_start/installation/).









Chat-Agent-Simulator (CHAS) requires `python >= 3.9`
<br />

#### Step 1 - Download and install

```bash
git clone git@github.com:plurai-ai/chas.git
cd chas
```

You can use Conda or pip to install the dependencies.

Using pip: 
```bash
pip install -r requirements.txt
```


#### Step 2 - Set your LLM API Key

Edit the `config/llm_env.yml` file to set up your LLM configuration (OpenAI/Azure/Vertex/Anthropic):

```yaml
openai:
  OPENAI_API_KEY: "your-api-key-here"
```

To change the default LLM provider or model for either the CHAS system or the chatbot, you can easily update the configuration file. For instance, modify the `config/config_education.yml` file:


```yaml
llm_chas:
    type: 'azure'

llm_chat:
    type: 'azure'
```

To change the number of samples in the database you should modify the `num_samples` in the config file:
```yaml
dataset:
    num_samples: 30
```


####  Step 3 - Run the Simulator
If you're utilizing Azure OpenAI services for the `llm_chas`, ensure you [disable](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/content-filters) the default `jailbreak` filter before running the simulator.

For fast simple environment without a database, run the following command:
```bash
python run.py --output_path results/education --config_path ./config/config_education.yml 
```
For more complex (slower) environment with a database, run the following command:
```bash
python run.py --output_path results/airline --config_path ./config/config_airline.yml 
```

> **Troubleshooting**  
> - **rate limit messages** → Decrease `num_workers` variables in the `config_default` file.  
> - **Frequent timeout errors** → Increase the `timeout` values in the `config_default` file.


Explore the [Customization](https://chas-doc.plurai.ai/customization/custom_environment/) options to configure the simulation for your environment, or delve into the [examples](https://chas-doc.plurai.ai/examples/education/) we provide to learn more about its capabilities.
#### Step 4 - See the Results

To visualize the simulation results using streamlit, run:
```bash 
streamlit run simulator/visualization/Simulator_Visualizer.py
```
This will launch a[ Streamlit dashboard](./README.md#-demo) showing detailed analytics and visualizations of your simulation results.

## Roadmap

- [x] **Beta Release**
- [ ] Integration Agent Platforms
    - [X] LangGraph
    - [ ] CrewAI
    - [ ] AutoGen
- [ ] Enable Event Generation from Existing Databases
- [ ] Implement API Integration for External Chatbot Agents
- [ ] Add Personality Dimensions to User Agents
- [ ] Optimize Chatbot Performance Using Simulator Diagnostics (Available now with [premium](https://plurai.ai/contact-us) access)
    - [ ] System Prompt Optimization
    - [ ] Tools Optimization
    - [ ] Graph structure Optimization

**Join our [Discord community](https://discord.gg/YWbT87vAau) to shape our roadmap!**


## 🚀 Community & Contributing

Your contributions are greatly appreciated! If you're eager to contribute, kindly refer to our [Contributing Guidelines](docs/contributing.md)) for detailed information. We’re particularly keen on receiving new examples and environments to enrich the project.

If you wish to be part of our journey, join our [Discord Community](https://discord.gg/YWbT87vAau) and subscribe to our [Newsletter](https://plurai.substack.com/). Stay updated on the latest advancements, open-source releases, and cutting-edge tools driving the future of Conversational AI. We're excited to have you with us!

## Citation

If you have used our code in your research, please cite our [paper](https://plurai.ai/blog/chas-announcement):

```
@misc{TODO}
```



## 🔍 Open Analytics

We collect basic usage metrics to better understand our users' needs and improve our services. As a transparent startup, we are committed to open-sourcing all the data we collect. **Plurai does not track any information that can identify you or your company.** You can review the specific metrics we track in the [code](https://github.com/plurai-ai/chas/healthcare_analytics.py).

If you prefer not to have your usage tracked, you can disable this feature by setting the `PLURAI_DO_NOT_TRACK` flag to true.

## ✉️ Support / Contact us
- Join our Community for discussions, updates and announcements [Community Discord](https://discord.gg/YWbT87vAau)
- Contact us: [‫Plurai‬](https://plurai.ai/contact-us)
- [GitHub Issues](https://github.com/plurai-ai/chas/issues) for bug reports and feature requests



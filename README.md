<div align="center">
 <img src="./docs/figures/intellagent_logo.png" alt="IntellAgent Logo" width="200">
 
  <i>A Multi-Agent Framework to Diagnose your Conversational AI Agent</i>

 [![Discord](https://img.shields.io/badge/Join-Discord-blue.svg)](https://discord.gg/YWbT87vAau)
 [![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://github.com/plurai-ai/intellagent/blob/main/LICENSE)

 [Documentation](https://intellagent-doc.plurai.ai/) |
 [Quick Start](#fire-quickstart) |
 [Newsletter](https://plurai.substack.com/) |
 [Paper](https://plurai.substack.com/p/intellagent-an-open-source-multi)
</div>

Most conversational AI agents fail in production due to hallucinations, inconsistent responses, and policy violations - all stemming from small, manually curated test datasets. Without comprehensive testing, critical weaknesses remain hidden until they impact real users.

**This is where IntellAgent steps in.** IntellAgent's multi-agent framework helps you test your agent from every angle, uncover its weaknesses, and provide actionable insights for optimization and confident deployment.

### Key Features
- 🔬 **Edge-Case Generation**  
 Automatically create thousands of realistic test scenarios tailored to your agent's use cases and requirements

- 🤖 **User Interaction Simulation**  
 Test your agent against diverse user behaviors and conversation patterns across varying complexity levels

- 📊 **Performance Analytics**  
 Get detailed metrics and insights to identify weaknesses, track improvements, and optimize your agent's performance

- 💪 **Production-Ready Deployment**  
 Deploy with confidence knowing your agent has been thoroughly tested against real-world scenarios

Stop hoping your agent will work in production. Know it will. Start building robust conversational agents that your users can trust.


> To understand the key concepts and how the IntellAgent system operates, refer to the [system overview guide](https://intellagent-doc.plurai.ai/How_it_Works/how-it-works/)

## 🔍 Demo

![simulator_recording](./docs/simulator_recording.gif)

## :fire: Quickstart

> For a more detailed and comprehensive guide, see the [Start Guide](https://intellagent-doc.plurai.ai/quick_start/installation/).









IntellAgent requires `python >= 3.9`
<br />

#### Step 1 - Download and install

```bash
git clone git@github.com:plurai-ai/intellagent.git
cd intellagent
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

To change the default LLM provider or model for either the IntellAgent system or the chat-agent, you can easily update the configuration file. For instance, modify the `config/config_education.yml` file:


```yaml
llm_intellagent:
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
If you're utilizing Azure OpenAI services for the `llm_intellagent`, ensure you [disable](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/content-filters) the default `jailbreak` filter before running the simulator.

For fast simple environment without a database, run the following command:
```bash
python run.py --output_path results/education --config_path ./config/config_education.yml 
```
For more complex (slower) environment with a database, run the following command:
```bash
python run.py --output_path results/airline --config_path ./config/config_airline.yml 
```

> **Troubleshooting**  
> - **Rate limit messages** → Decrease `num_workers` variables in the `config_default` file.  
> - **Frequent timeout errors** → Increase the `timeout` values in the `config_default` file.


Explore the [Customization](https://intellagent-doc.plurai.ai/customization/custom_environment/) options to configure the simulation for your environment, or delve into the [examples](https://intellagent-doc.plurai.ai/examples/education/) we provide to learn more about its capabilities.
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
- [ ] Optimize Chat-Agent Performance Using Simulator Diagnostics (Available now with [premium](https://plurai.ai/contact-us) access)
    - [ ] System Prompt Optimization
    - [ ] Tools Optimization
    - [ ] Graph structure Optimization

**Join our [Discord community](https://discord.gg/YWbT87vAau) to shape our roadmap!**


## 🚀 Community & Contributing

Your contributions are greatly appreciated! If you're eager to contribute, kindly refer to our [Contributing Guidelines](docs/contributing.md)) for detailed information. We’re particularly keen on receiving new examples and environments to enrich the project.

If you wish to be part of our journey, join our [Discord Community](https://discord.gg/YWbT87vAau) and subscribe to our [Newsletter](https://plurai.substack.com/). Stay updated on the latest advancements, open-source releases, and cutting-edge tools driving the future of Reliable Conversational AI. We're excited to have you with us!

## Citation

If you have used our code in your research, please cite our [paper](https://plurai.substack.com/p/intellagent-an-open-source-multi):

```
@misc{TODO}
```



## 🔍 Open Analytics

We collect basic usage metrics to better understand our users' needs and improve our services. As a transparent startup, we are committed to open-sourcing all the data we collect. **Plurai does not track any information that can identify you or your company.** You can review the specific metrics we track in the [code](https://github.com/plurai-ai/intellagent/healthcare_analytics.py).

If you prefer not to have your usage tracked, you can disable this feature by setting the `PLURAI_DO_NOT_TRACK` flag to true.

## ✉️ Support / Contact us
- Join our Community for discussions, updates and announcements [Community Discord](https://discord.gg/YWbT87vAau)
- Contact us: [‫Plurai‬](https://plurai.ai/contact-us)
- [GitHub Issues](https://github.com/plurai-ai/intellagent/issues) for bug reports and feature requests



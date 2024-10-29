from typing import Annotated, Literal, TypedDict
from langchain_core.tools import tool, BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.language_models.llms import LLM


# Define the function that determines whether to continue or not
def should_continue(state: MessagesState):
    messages = state['messages']
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "tools" node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, we stop (reply to the user)
    return END


# Define the function that calls the model
def call_model(state: MessagesState):
    messages = state['messages']
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}



class AgentTools:
    # A tool based agent implementation using langgraph
    def __init__(self, llm: LLM, tools: list[BaseTool], save_memory: bool = False):
        """Initialize the agent with the LLM and tools
        :param llm (LLM): The LLM model
        :param tools (list[BaseTool]): The tools to use
        :param save_memory (bool, optional): Whether to use memory. Defaults to False.
        """
        self.llm = llm
        self.tools = tools
        self.checkpointer = None
        if save_memory:
            self.checkpointer = MemorySaver()
        self.graph = self.compile_agent()

    def compile_agent(self):
        # Define a graph and compile it
        workflow = StateGraph(MessagesState)
        tool_node = ToolNode(self.tools)

        # Define the two nodes we will cycle between
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)

        # Set the entrypoint as `agent`
        # This means that this node is the first one called
        workflow.add_edge(START, "agent")

        # We now add a conditional edge
        workflow.add_conditional_edges(
            # First, we define the start node. We use `agent`.
            # This means these are the edges taken after the `agent` node is called.
            "agent",
            # Next, we pass in the function that will determine which node is called next.
            should_continue,
        )

        # We now add a normal edge from `tools` to `agent`.
        # This means that after `tools` is called, `agent` node is called next.
        workflow.add_edge("tools", 'agent')
        return workflow.compile(checkpointer=self.checkpointer)

    def invoke(self, messages, config=None):
        """Invoke the agent with the messages
        :param messages: The messages to invoke the agent with
        :param config: The configuration for the agent"""
        return self.graph.invoke({'messages': messages}, config=config)


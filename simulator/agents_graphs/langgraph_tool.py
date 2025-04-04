from typing import Annotated, Literal, TypedDict
from langchain_core.tools import tool, BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph  # , MessagesState
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.memory import InMemoryStore
from langgraph.utils.runnable import RunnableCallable, RunnableConfig
from langchain_core.runnables.base import Runnable
from langgraph.graph.message import add_messages
from simulator.utils.llm_utils import convert_to_anthropic_tools, convert_to_oci_schema
import inspect
import copy
from langchain_core.runnables.utils import Input, Output

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolCall,
    ToolMessage,
)
from typing import (
    Callable,
    Sequence,
    Union,
    Any,
    Optional
)


class MessageGraph(StateGraph):
    """A StateGraph where every node receives a list of messages as input and returns one or more messages as output.

    MessageGraph is a subclass of StateGraph whose entire state is a single, append-only* list of messages.
    Each node in a MessageGraph takes a list of messages as input and returns zero or more
    messages as output. The `add_messages` function is used to merge the output messages from each node
    into the existing list of messages in the graph's state.
    """

    def __init__(self) -> None:
        super().__init__(Annotated[list[AnyMessage], add_messages])


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    args: dict[Any]


class ToolNode(RunnableCallable):
    def __init__(self, tools: Sequence[Union[BaseTool, Callable]]):
        super().__init__(self._func)
        self.tools_by_name = {tool.name: tool for tool in tools}

    def _func(self, state: MessagesState):
        result = []
        for tool_call in state["messages"][-1].tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            all_tool_args = list(inspect.signature(tool.func).parameters)
            function_args = copy.deepcopy(tool_call["args"])
            if state['args'] is not None:
                function_args.update({k: v for k, v in state['args'].items()
                                      if (k in all_tool_args) and (k not in function_args)})
            observation = tool.func(**function_args)
            result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
        return {"messages": result, 'args': state['args']}

    def invoke(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs: Any):
        result = self._func(input)
        return result


# Define the function that determines whether to continue or not
def should_continue(state: MessagesState):
    messages = state['messages']
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "tools" node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, we stop (reply to the user)
    return END


class AgentTools(Runnable):
    # A tool based agent implementation using langgraph
    def __init__(self, llm: BaseChatModel, tools: list[BaseTool], tools_schema: list[dict] = None,
                 save_memory: bool = False, system_prompt: list = None,
                 store: InMemoryStore = None):
        """Initialize the agent with the LLM and tools
        :param llm (BaseChatModel): The LLM model
        :param tools (list[BaseTool]): The tools to use
        :param tools_schema (list[dict], optional): The schema for the tools. If None infer the schema from the tools.
        :param store (InMemoryStore, optional): The store to use. Defaults to None.
        :param system_prompt (list, optional): The system prompt. Defaults to None.
        :param save_memory (bool, optional): Whether to use memory. Defaults to False.
        :param template (ChatPromptTemplate, optional): The template to use. Defaults to None.
        """
        if not tools:
            self.llm = llm
        elif tools_schema is None:
            self.llm = llm.bind_tools(tools)
        else:
            if 'anthropic-chat' in llm._llm_type:
                tools_schema = convert_to_anthropic_tools(tools_schema)
            if 'oci_' in llm._llm_type:
                oci_schema = convert_to_oci_schema(tools_schema)
                tools_schema = [llm._provider.convert_to_oci_tool(t) for t in oci_schema]
            self.llm = llm.bind(tools=tools_schema)
        self.tools = tools
        self.checkpointer = None
        self.store = store
        if save_memory:
            self.checkpointer = MemorySaver()
        else:
            self.checkpointer = None
        self.graph = self.compile_agent()
        self.system_prompt = system_prompt

    def get_call_model(self):
        def call_model(state: MessagesState):
            messages = state['messages']
            response = self.llm.invoke(messages)
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}

        return call_model

    def compile_agent(self):
        # Define a graph and compile it
        workflow = StateGraph(MessagesState)
        tool_node = ToolNode(self.tools)

        # Define the two nodes we will cycle between
        workflow.add_node("agent", self.get_call_model())
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
        return workflow.compile(checkpointer=self.checkpointer, store=self.store)

    def invoke(self, input: Input, config: Optional[RunnableConfig] = None, **kwargs: Any) -> Output:
        """Invoke the agent with the messages
        :param input: The input for the graph, should be a dictionary {'messages': messages, 'args': additional_args}
        :param config: The configuration for the agent
        """
        return self.graph.invoke(input=input, config=config)

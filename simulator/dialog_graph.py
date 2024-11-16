from langchain_core.runnables.base import Runnable
from typing import Callable
from langgraph.graph import END
from typing import Annotated
from langgraph.graph import StateGraph, START
from typing_extensions import TypedDict
from typing import Optional

from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage


class DialogState(TypedDict):
    user_messages: Annotated[list, add_messages]
    chatbot_messages: Annotated[list, add_messages]
    chatbot_args: Optional[dict]
    thread_id: str
    user_thoughts: Optional[list]


class Dialog:
    """
    Building the dialog graph that runs the convesration between the chatbot and the user
    """

    def __init__(self, user: Runnable, chatbot: Runnable, intermediate_processing: Callable = None,
                 memory=None):
        """
        Initialize the event generator.]
        :param user (Runnable): The user model
        :param chatbot (Runnable): The chatbot model
        :param intermediate_processing (optional): A function between that processes the output of the user and the
        chatbot at each step
        :param memory (optional): The memory to store the conversations artifacts
        """
        self.user = user
        self.chatbot = chatbot
        self.intermediate_processing = intermediate_processing  # TODO: Add default function
        self.memory = memory
        self.compile_graph()

    def get_end_condition(self):
        def should_end(state: DialogState):
            terminate = self.intermediate_processing(state)
            if terminate:
                return END
            else:
                return "chatbot"

        return should_end

    def get_user_node(self):
        def simulated_user_node(state):
            messages = state["user_messages"]
            # Call the simulated user
            response = self.user.invoke(messages)
            # This response is an AI message - we need to flip this to be a human message
            user_thoughts = state['user_thoughts']
            if self.memory is not None:
                if response['thought'] is not None:
                    self.memory.insert_thought(state['thread_id'], response['thought'])
                    user_thoughts.append(response['thought'])
                self.memory.insert_dialog(state['thread_id'], 'Human', response['response'])
            return {"chatbot_messages": [HumanMessage(content=response['response'])],
                    'user_messages': [AIMessage(content=response['response'])],
                    'user_thoughts': user_thoughts}

        return simulated_user_node

    def get_chatbot_node(self):
        def chat_bot_node(state):
            messages = state["chatbot_messages"]
            # Call the chatbot
            response = self.chatbot.invoke(messages=messages, additional_args=state['chatbot_args'])
            last_human_message = max([i for i, v in enumerate(response['messages']) if v.type == 'human'])
            all_tool_calls = {}
            if self.memory is not None:
                # Inserting tool calls into memory
                for message in response['messages'][last_human_message + 1:]:
                    if 'tool_calls' in message.additional_kwargs:
                        for tool_call in message.additional_kwargs['tool_calls']:
                            all_tool_calls[tool_call['id']] = tool_call['function']
                    if message.type == 'tool':
                        all_tool_calls[message.tool_call_id]['output'] = message.content
                for v in all_tool_calls.values():
                    self.memory.insert_tool(state['thread_id'], v['name'], v['arguments'], v['output'])
                # inserting the chatbot messages into memory
                self.memory.insert_dialog(state['thread_id'], 'AI', response['messages'][-1].content)
            return {"chatbot_messages": [AIMessage(content=response['messages'][-1].content)],
                    'user_messages': [HumanMessage(content=response['messages'][-1].content)]}

        return chat_bot_node

    def compile_graph(self):
        workflow = StateGraph(DialogState)
        workflow.add_node("user", self.get_user_node())
        workflow.add_node("chatbot", self.get_chatbot_node())
        workflow.add_edge(START, "user")
        workflow.add_conditional_edges(
            "user",
            self.get_end_condition(),
            ["chatbot", END],
        )
        workflow.add_edge("chatbot", "user")
        self.graph = workflow.compile()

    def invoke(self, **kwargs):
        """
        Invoke the agent with the messages
        :return:
        """
        return self.graph.invoke(**kwargs)

    def ainvoke(self, **kwargs):
        """
        async Invoke the agent with the messages
        :return:
        """
        return self.graph.ainvoke(**kwargs)

# app.py — MCP + Streamlit (Claude-like, fixed markdown + collapsed tools)

import asyncio
import json
import streamlit as st
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)

load_dotenv()

# -----------------------------------
# MCP Config
# -----------------------------------
SERVERS = {
    "expensefn": {
        "transport": "stdio",
        "command": "/home/anishfn/.local/share/mise/shims/uv",
        "args": [
            "run",
            "fastmcp",
            "run",
            "/home/anishfn/Desktop/code/expense-mcp/main.py",
        ],
    }
}

# -----------------------------------
# Agent
# -----------------------------------
async def run_agent(user_input, chat_history, stream_callback=None, tool_callback=None):
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()
    tool_map = {tool.name: tool for tool in tools}

    llm = ChatMistralAI(model="mistral-small-2506")
    llm = llm.bind_tools(tools, tool_choice="auto")

    system_prompt = SystemMessage(
        content="""
You are an AI assistant with access to tools.

RULES:
- ALWAYS use tools for expense queries
- NEVER say you don't have access
- Summarize results nicely
"""
    )

    messages = [system_prompt] + chat_history + [HumanMessage(content=user_input)]

    while True:
        response = await llm.ainvoke(messages)

        # FINAL ANSWER
        if not response.tool_calls:
            final_text = response.content or ""

            if stream_callback:
                # stream but DO NOT render markdown yet
                for token in final_text.split():
                    stream_callback(token + " ")
                    await asyncio.sleep(0.01)

            return final_text

        messages.append(response)

        # TOOL LOOP
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            tool_id = tool_call["id"]

            pretty_args = json.dumps(args, indent=2)

            if tool_callback:
                tool_callback(name, pretty_args, None)

            try:
                result = await tool_map[name].ainvoke(args)
            except Exception as e:
                result = {"error": str(e)}

            pretty_result = json.dumps(result, indent=2)

            if tool_callback:
                tool_callback(name, pretty_args, pretty_result)

            messages.append(
                ToolMessage(
                    content=pretty_result,
                    tool_name=name,
                    tool_call_id=tool_id,
                )
            )

# -----------------------------------
# UI
# -----------------------------------
st.set_page_config(page_title="Expense MCP Chat", layout="centered")
st.title("💸 Expense MCP Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render history
for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

# Input
user_input = st.chat_input("Ask about your expenses...")

if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        tool_container = st.container()

        streamed = []

        # STREAM TEXT (plain, not markdown yet)
        def stream_callback(token):
            streamed.append(token)
            text_placeholder.write("".join(streamed))  # 👈 key fix

        # TOOL UI (collapsed)
        def tool_callback(name, args, result):
            with tool_container:
                with st.expander(f"🔧 {name}", expanded=False):  # 👈 collapsed
                    st.markdown("**Input**")
                    st.code(args, language="json")

                    if result:
                        st.markdown("**Output**")
                        st.code(result, language="json")

        with st.spinner("Thinking..."):
            final = asyncio.run(
                run_agent(
                    user_input,
                    st.session_state.messages,
                    stream_callback=stream_callback,
                    tool_callback=tool_callback,
                )
            )

        # ✅ FINAL RENDER (proper markdown)
        text_placeholder.markdown(final)

    st.session_state.messages.append(AIMessage(content=final))
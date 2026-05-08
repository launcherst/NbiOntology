# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

from langchain.agents import AgentExecutor, create_react_agent
from langchain_ollama import ChatOllama
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from .query import query_sparql

# 构造本体摘要，帮助 LLM 理解结构
ONTOLOGY_SUMMARY = """
OTN Ontology (http://example.org/ontology/otn-ontology#)
Classes: NE (网元), Card (板卡), Port (端口), TopoLink (拓扑连接)
Object Properties:
- NE_has_Card (NE -> Card)
- Card_has_Port (Card -> Port)
- TopoLink_connects_Port (TopoLink -> Port)
Data Properties of Port:
- portRate (string, e.g., "400G")
- rmUID (string)
- nativeName (string)
... (列出关键属性)
"""

def create_agent(model_name: str = "gemma4:e2b", base_url: str = "http://localhost:11434"):
    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=0, # 确保输出稳定，适合执行工具
        num_predict=2048, # 最大生成长度，可根据需要调整
        )
    
    tools = [
        Tool(
            name="SPARQL_Query",
            func=query_sparql,
            description="Execute SPARQL query against the OTN knowledge graph.\
                  Input: a valid SPARQL query string. Output: query result as text."
        )
    ]
    
    prompt = PromptTemplate.from_template("""
You are an assistant that answers questions about an OTN network using its knowledge graph.
The knowledge graph has the following schema:
{ontology_summary}

You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")
    
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
        )
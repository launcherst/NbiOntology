# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.3

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import Tool
from .query import query_sparql, draw_topology, get_ontology_summary, load_graph


ONTOLOGY_SUMMARY = get_ontology_summary()


def create_otn_agent(
    model_name: str = "gemma4:e2b",
    base_url: str = "http://localhost:11434",
    temperature: float = 0,
    num_predict: int = 2048,
):
    """创建 OTN 知识图谱问答 Agent (langchain 1.x API)"""
    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=temperature,
        num_predict=num_predict,
    )

    tools = [
        Tool(
            name="SPARQL_Query",
            func=query_sparql,
            description=(
                "Execute a SPARQL query against the OTN knowledge graph. "
                "Use this to query resources, ports, cards, performance records, etc. "
                "Input must be a valid SPARQL query string with these prefixes: "
                "PREFIX ex: <http://example.org/ontology/otn-ontology#> "
                "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> "
                "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"
            ),
        ),
        Tool(
            name="Draw_Topology",
            func=draw_topology,
            description=(
                "Generate a Mermaid.js flowchart showing the OTN network topology. "
                "Nodes are NEs (network elements) and edges are TopoLinks between them. "
                "Use when asked to visualize, draw, or show network topology. "
                "Input: optional max_nodes integer, or leave empty for defaults."
            ),
        ),
    ]

    system_prompt = f"""You are a SPARQL expert for an OTN knowledge graph. Answer questions by writing and executing SPARQL queries.

{ONTOLOGY_SUMMARY}

TOOLS:
- SPARQL_Query: Execute a SPARQL query. Input is a SPARQL string with PREFIX declarations.
- Draw_Topology: Generate a Mermaid topology diagram. Use when asked to "draw" or "show" topology.

CRITICAL RULES:
1. ALWAYS include these 3 PREFIX lines at the top of every SPARQL query:
   PREFIX ex: <http://example.org/ontology/otn-ontology#>
   PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
   PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

2. Use rdf:type to filter by class:  ?x rdf:type ex:Port .
3. All properties need ex: prefix: ex:portRate, ex:metricName, ex:metricValue, ex:nativeName
4. When filtering string values, use quotes: "400G", "temperature"
5. When comparing numeric values, cast with xsd:float(?val)
6. For count queries, use (COUNT(?var) AS ?count)
7. If the first query fails, try a simpler version without OPTIONAL or GROUP BY
8. Answer in Chinese, in the same language as the question
9. Be concise: state the number directly, e.g. "全网共有115个100G端口" """

    agent = create_agent(llm, tools, system_prompt=system_prompt)
    return agent


def init_knowledge_graph(
    ontology_path: str = "output/otn_ontology_lib.rdf",
    instances_path: str = "output/instances.ttl",
):
    """初始化知识图谱 (在启动时调用)"""
    load_graph(ontology_path, instances_path)

# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

def load_graph():
    g = Graph()
    g.parse("output/otn_ontology.rdf", format="xml")  # 加载本体
    g.parse("output/instances.ttl", format="turtle")  # 加载实例
    return g

def query_sparql(sparql_str: str) -> str:
    g = load_graph()
    q = prepareQuery(sparql_str)
    results = g.query(q)
    # 格式化结果为文本
    if results.vars:
        rows = []
        for row in results:
            rows.append(", ".join(str(row[var]) for var in results.vars))
        return "\n".join(rows)
    else:
        return str(bool(results))  # ASK 查询
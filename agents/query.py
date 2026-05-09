# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.2

from pathlib import Path
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

_graph: Graph = None


def load_graph(
    ontology_path: str = "output/otn_ontology_lib.rdf",
    instances_path: str = "output/instances.ttl",
) -> Graph:
    """加载本体和实例, 合并为完整的知识图谱"""
    global _graph
    g = Graph()
    g.parse(ontology_path, format="xml")
    if Path(instances_path).exists():
        g.parse(instances_path, format="turtle")
    _graph = g
    return g


def query_sparql(sparql_str: str) -> str:
    """执行 SPARQL 查询, 返回格式化文本结果"""
    if _graph is None:
        load_graph()
    try:
        q = prepareQuery(sparql_str)
        results = _graph.query(q)
        if results.vars:
            rows = []
            for row in results:
                vals = []
                for var in results.vars:
                    v = row[var]
                    # 简化 URI 显示
                    if hasattr(v, "n3"):
                        s = v.n3(_graph.namespace_manager)
                        # 截断过长字符串
                        if len(s) > 120:
                            s = s[:120] + "..."
                        vals.append(s)
                    else:
                        vals.append(str(v))
                rows.append(", ".join(vals))
            if not rows:
                return "(无结果)"
            return "\n".join(rows[:200])  # 限制最大返回行数
        else:
            return str(bool(results))
    except Exception as e:
        return f"SPARQL 查询失败: {str(e)}"


def draw_topology(max_nodes: int = 50) -> str:
    """查询拓扑数据并生成 Mermaid flowchart"""
    if _graph is None:
        load_graph()

    q = prepareQuery("""
        PREFIX ex: <http://example.org/ontology/otn-ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?aNeUid ?zNeUid ?aNeName ?zNeName
        WHERE {
            ?link rdf:type ex:TopoLink .
            ?link ex:aEndNermUID ?aNeUid .
            ?link ex:zEndNermUID ?zNeUid .
            OPTIONAL {
                ?aNe rdf:type ex:NE ; ex:nativeName ?aNeName .
                FILTER(STR(?aNe) = CONCAT("http://example.org/ontology/otn-ontology#", ?aNeUid))
            }
            OPTIONAL {
                ?zNe rdf:type ex:NE ; ex:nativeName ?zNeName .
                FILTER(STR(?zNe) = CONCAT("http://example.org/ontology/otn-ontology#", ?zNeUid))
            }
        }
        LIMIT 200
    """)

    results = _graph.query(q)

    ne_names: dict = {}
    edges = []

    for row in results:
        a_ne_uid = str(row["aNeUid"])
        z_ne_uid = str(row["zNeUid"])
        a_name = str(row["aNeName"]) if row["aNeName"] else a_ne_uid[-20:]
        z_name = str(row["zNeName"]) if row["zNeName"] else z_ne_uid[-20:]

        a_short = a_name[-40:] if len(a_name) > 40 else a_name
        z_short = z_name[-40:] if len(z_name) > 40 else z_name

        if a_ne_uid not in ne_names:
            ne_names[a_ne_uid] = a_short
        if z_ne_uid not in ne_names:
            ne_names[z_ne_uid] = z_short

        edges.append((a_ne_uid, z_ne_uid))

    if not edges:
        return "graph TD\n  A[No topology data found]"

    # Limit to max_nodes NE nodes
    ne_list = list(ne_names.items())[:max_nodes]
    ne_set = {uid for uid, _ in ne_list}
    filtered_edges = [
        (s, t) for s, t in edges if s in ne_set and t in ne_set
    ][:max_nodes * 3]

    lines = ["graph TD"]
    for uid, name in ne_list:
        safe_name = name.replace('"', "'").replace("[", "(").replace("]", ")")
        lines.append(f'  {uid}["{safe_name}"]')

    for src, dst in filtered_edges:
        lines.append(f"  {src} --> {dst}")

    return "\n".join(lines)


def get_ontology_summary() -> str:
    """生成本体摘要, 供 LLM Agent 使用, 包含具体查询示例"""
    return """
OTN Ontology namespace: PREFIX ex: <http://example.org/ontology/otn-ontology#>
Standard prefixes: PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                  PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

Classes:
- ex:NE (网元) — 属性: ex:rmUID, ex:nativeName, ex:location, ex:productName, ex:vendor, ex:role
- ex:Card (板卡) — 属性: ex:rmUID, ex:nermUID, ex:nativeName, ex:cardType
- ex:Port (端口) — 属性: ex:rmUID, ex:cardrmUID, ex:nermUID, ex:portNo, ex:nativeName, ex:portRate
- ex:TopoLink (拓扑连接) — 属性: ex:rmUID, ex:aEndNermUID, ex:zEndNermUID, ex:aEndPortrmUID, ex:zEndPortrmUID
- ex:Location (位置) — 属性: ex:locationName
- ex:PerformanceRecord (性能记录) — 属性: ex:metricName, ex:metricValue, ex:timestamp

Object Properties (relationship triples):
- ex:NE_has_Card: links ex:NE -> ex:Card
- ex:Card_has_Port: links ex:Card -> ex:Port
- ex:TopoLink_connects_Port: links ex:TopoLink -> ex:Port
- ex:NE_locatedAt_Location: links ex:NE -> ex:Location
- ex:forResource: links ex:PerformanceRecord -> ex:NE or ex:Card or ex:Port

———— CONCRETE SPARQL EXAMPLES (copy the pattern) ————

Example 1 — Count ports with a specific rate:
SELECT (COUNT(?port) AS ?count) WHERE {
    ?port rdf:type ex:Port .
    ?port ex:portRate ?rate .
    FILTER(CONTAINS(?rate, "100G"))
}

Example 2 — List all port rates and their counts:
SELECT ?rate (COUNT(?port) AS ?count) WHERE {
    ?port rdf:type ex:Port .
    ?port ex:portRate ?rate .
} GROUP BY ?rate ORDER BY DESC(?count)

Example 3 — Find cards with temperature above threshold:
SELECT ?card ?cardName ?val WHERE {
    ?pr rdf:type ex:PerformanceRecord .
    ?pr ex:forResource ?card .
    ?card rdf:type ex:Card .
    ?pr ex:metricName "temperature" .
    ?pr ex:metricValue ?val .
    FILTER(xsd:float(?val) > 70)
    OPTIONAL { ?card ex:nativeName ?cardName . }
} LIMIT 10

Example 4 — Count NEs:
SELECT (COUNT(?ne) AS ?count) WHERE { ?ne rdf:type ex:NE . }

Example 5 — List NE names and locations:
SELECT ?neName ?locName WHERE {
    ?ne rdf:type ex:NE .
    ?ne ex:nativeName ?neName .
    ?ne ex:NE_locatedAt_Location ?loc .
    ?loc ex:locationName ?locName .
} LIMIT 10

Example 6 — Find all metric names in PerformanceRecords:
SELECT ?metric (COUNT(?pr) AS ?cnt) WHERE {
    ?pr rdf:type ex:PerformanceRecord .
    ?pr ex:metricName ?metric .
} GROUP BY ?metric
"""

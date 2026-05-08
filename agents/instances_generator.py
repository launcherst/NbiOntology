# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS

def generate_instances(resource_xlsx, output_ttl="output/instances.ttl"):
    g = Graph()
    ex = Namespace("http://example.org/ontology/otn-ontology#")
    g.bind("ex", ex)

    # 读取各sheet并实例化
    ne_df = pd.read_excel(resource_xlsx, sheet_name="NE")
    for _, row in ne_df.iterrows():
        ne_uri = ex[row["rmUID"]]
        g.add((ne_uri, RDF.type, ex.NE))
        g.add((ne_uri, ex.name, Literal(row["name"])))
        g.add((ne_uri, ex.shortName, Literal(row.get("shortName", ""))))
        # ... 其他属性

    card_df = pd.read_excel(resource_xlsx, sheet_name="Card")
    for _, row in card_df.iterrows():
        card_uri = ex[row["rmUID"]]
        g.add((card_uri, RDF.type, ex.Card))
        g.add((card_uri, ex.nermUID, Literal(row["ne_rmUID"])))
        # 连接 NE 和 Card
        ne_uri = ex[row["ne_rmUID"]]
        g.add((ne_uri, ex.has_Card, card_uri))

    port_df = pd.read_excel(resource_xlsx, sheet_name="Port")
    for _, row in port_df.iterrows():
        port_uri = ex[row["rmUID"]]
        g.add((port_uri, RDF.type, ex.Port))
        g.add((port_uri, ex.portRate, Literal(row["portRate"])))
        card_uri = ex[row["card_rmUID"]]
        g.add((card_uri, ex.has_Port, port_uri))
        # 可能还有 portNo 等

    # TopoLink 类似...

    g.serialize(destination=output_ttl, format="turtle")
    print(f"Instance graph saved to {output_ttl}")
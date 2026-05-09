# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.2

from typing import Dict, List, Any
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD


EX = Namespace("http://example.org/ontology/otn-ontology#")


def _safe_uri(text: str) -> str:
    """将字符串转换为安全的 URI 片段"""
    return text.replace(" ", "_").replace("/", "_").replace("\\", "_")


def generate_instances(
    instance_data: Dict[str, List[Dict]],
    performance_records: List[Dict] = None,
    output_ttl: str = "output/instances.ttl",
) -> Graph:
    """根据实例数据生成 RDF 实例图"""
    g = Graph()
    g.bind("ex", EX)
    g.bind("xsd", XSD)

    nes = instance_data.get("NE", [])
    cards = instance_data.get("Card", [])
    ports = instance_data.get("Port", [])
    links = instance_data.get("TopoLink", [])

    ne_set = {n["rmUID"] for n in nes}

    # 字典缓存已生成的 Location URI
    location_cache: Dict[str, URIRef] = {}

    # 1. 生成 NE 实例 & Location 实例
    for ne in nes:
        ne_uri = EX[ne["rmUID"]]
        g.add((ne_uri, RDF.type, EX.NE))
        for field, val in ne.items():
            if field == "rmUID" or not val or val == "--":
                continue
            pred = EX[field]
            g.add((ne_uri, pred, Literal(val)))

        # 处理 location: 创建 Location 实例并建立关系
        loc_str = ne.get("location", "").strip()
        if loc_str and loc_str != "--":
            if loc_str not in location_cache:
                loc_uri = EX["LOC_" + _safe_uri(loc_str)]
                location_cache[loc_str] = loc_uri
                g.add((loc_uri, RDF.type, EX.Location))
                g.add((loc_uri, EX.locationName, Literal(loc_str)))
            else:
                loc_uri = location_cache[loc_str]
            g.add((ne_uri, EX.NE_locatedAt_Location, loc_uri))

    # 2. 生成 Card 实例
    for card in cards:
        card_uri = EX[card["rmUID"]]
        g.add((card_uri, RDF.type, EX.Card))
        ne_uid = card.get("nermUID", "")
        for field, val in card.items():
            if field == "rmUID" or not val or val == "--":
                continue
            pred = EX[field]
            g.add((card_uri, pred, Literal(val)))
        if ne_uid and ne_uid in ne_set:
            ne_uri = EX[ne_uid]
            g.add((ne_uri, EX.NE_has_Card, card_uri))

    # 3. 生成 Port 实例
    for port in ports:
        port_uri = EX[port["rmUID"]]
        g.add((port_uri, RDF.type, EX.Port))
        card_uid = port.get("cardrmUID", "")
        for field, val in port.items():
            if field == "rmUID" or not val or val == "--":
                continue
            pred = EX[field]
            g.add((port_uri, pred, Literal(val)))
        if card_uid:
            card_uri = EX[card_uid]
            g.add((card_uri, EX.Card_has_Port, port_uri))

    # 4. 生成 TopoLink 实例
    for link in links:
        link_uri = EX[link["rmUID"]]
        g.add((link_uri, RDF.type, EX.TopoLink))
        a_port = link.get("aEndPortrmUID", "")
        z_port = link.get("zEndPortrmUID", "")
        for field, val in link.items():
            if field == "rmUID" or not val or val == "--":
                continue
            pred = EX[field]
            g.add((link_uri, pred, Literal(val)))
        if a_port:
            g.add((link_uri, EX.TopoLink_connects_Port, EX[a_port]))
        if z_port and z_port != a_port:
            g.add((link_uri, EX.TopoLink_connects_Port, EX[z_port]))

    # 5. 生成 PerformanceRecord 实例
    if performance_records:
        # 收集所有资源 UID
        all_resources = set()
        for ne in nes:
            all_resources.add(ne["rmUID"])
        for card in cards:
            all_resources.add(card["rmUID"])
        for port in ports:
            all_resources.add(port["rmUID"])

        for i, rec in enumerate(performance_records):
            rid = rec["resourceUID"]
            if rid not in all_resources:
                continue
            pr_uri = EX[f"PR_{i}_{_safe_uri(rid)}_{rec['metricName']}_{rec['timestamp'].replace(':','_').replace('-','_')}"]
            g.add((pr_uri, RDF.type, EX.PerformanceRecord))
            g.add((pr_uri, EX.forResource, EX[rid]))
            g.add((pr_uri, EX.metricName, Literal(rec["metricName"])))
            g.add((pr_uri, EX.metricValue, Literal(rec["metricValue"], datatype=XSD.float)))
            g.add((pr_uri, EX.timestamp, Literal(rec["timestamp"], datatype=XSD.dateTime)))

    output_path = Path(output_ttl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(output_path), format="turtle")
    print(f"  Instance graph saved to {output_path} ({len(g)} triples)")

    return g

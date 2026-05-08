# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

from typing import Dict, Any
import json
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD


class OntologyGenerator:
    """
    otn领域本体生成器
    输入: DataLoaderAgent 输出的标准化数据
    输出：结构化本体（类、数据属性、枚举约束、本体字典/JSON/OWL文本)
    """

    def __init__(self, standard_data: Dict[str, Any]):
        # 接收数据加载器输出的标准数据
        self.resource_map = standard_data["resource_map"]
        self.resource_attributes = standard_data["resource_attributes"]
        self.enum_dictionary = standard_data["enum_dictionary"]
        self.resource_en_names = standard_data["resource_en_names"]

        # 最终生成的本体结构
        self.ontology = {
            "domain": "otn_resource",
            "name_cn": "otn资源领域本体",
            "name_en": "OtnResourceOntology",
            "classes": {},  # 本体类（资源对象）
            "data_properties": {},  # 数据属性
            "rel_properties": {},  # 【新增】对象属性（类之间的关联关系）
            "enumerations": self.enum_dictionary,  # 枚举字典
        }

    def generate_ontology(self) -> Dict[str, Any]:
        """统一入口: 生成完整otn资源本体"""
        self._generate_classes()
        self._generate_data_properties()
        self._generate_rel_properties()  # 【新增】生成类关系
        return self.ontology

    def _generate_classes(self):
        """生成本体类（资源对象 = 本体类）"""
        for cls_name_cn, info in self.resource_map.items():
            cls_name_en = info["cls_name_en"]
            short_name = info["short_name"]

            # 类结构：英文类名作为key
            self.ontology["classes"][cls_name_en] = {
                "label": cls_name_en, # rdfs:label
                "short_name": short_name, # ont:shortName
                "comment": f"otn资源类: {cls_name_cn}", # rdfs:comment
                "data_properties": [],  # 该类拥有的数据属性列表

                # extended info for downstream usage
                "name": cls_name_cn, # rdfs:name
            }

    def _generate_data_properties(self):
        """为每个类绑定数据属性，并生成全局属性定义"""
        # 遍历每个资源类（英文名称）
        for class_en, attrs in self.resource_attributes.items():
            if class_en not in self.ontology["classes"]:
                continue

            # 遍历该类的所有属性
            for label in attrs:
                attr = attrs[label]

                # 1. 把属性加入类的属性列表
                self.ontology["classes"][class_en]["data_properties"].append(label)

                # 2. 构建全局数据属性定义
                self.ontology["data_properties"][class_en + '_' + label] = {
                    "label": label, # rdfs:label
                    "domain": class_en, # rdfs:domain
                    "range": attr["type"], # rdfs:range, TODO: integer, string, but enum should also be treated as string
                    "comment": attr["desc"], # rdfs:comment
                    "propertyType": attr["type"], #ont:propertyType and if has_enumeration then also ont:enumerationValues

                    # extended info for downstream usage
                    "name": attr["name_cn"],
                    "required": attr["required"],
                    "example": attr["example"],
                    "has_enumeration": class_en in self.enum_dictionary and label in self.enum_dictionary[class_en],
                    "enumeration_values": [enum["value"] for enum in self.enum_dictionary.get(class_en, {}).get(label, [])],
                }

    # ============================
    # 【核心新增】定义类之间的关联关系
    # ============================
    def _generate_rel_properties(self):
        """
        define object properties (relationships between classes)
        TODO: currently hardcoded, can be enhanced to auto-discover relationships based on data or naming patterns
        """
        object_props = {
            # 格式：
            # "属性英文名": {
            #   "label": 属性名称, # rdfs:label
            #   "domain": 定义域（从哪个类出发）, # rdfs:domain
            #   "range": 值域（指向哪个类）， # rdfs:range
            #   "comment": 关系描述, # rdfs:comment
            #   "cardinality": 关系的基数（如1..1, 0..*, 1..*等） # ont:cardinality
            # }
            # 板卡 归属于 设备
            "NE_has_Card": {
                "label": "has_Card",
                "domain": "NE",
                "range": "Card",
                "comment": "NE has one or more Cards",
                "cardinality": "1..*", # 1对多关系
            },
            # 端口 归属于 板卡
            "Card_has_Port": {
                "label": "has_Port",
                "domain": "Card",
                "range": "Port",
                "comment": "Card has one or more Ports",
                "cardinality": "1..*", # 1对多关系
            },
            # 拓扑连接 连接到 端口
            "TopoLink_connects_Port": {
                "label": "connects_Port",
                "domain": "TopoLink",
                "range": "Port",
                "comment": "TopoLink connects to two Ports",
                "cardinality": "2", # 1对2关系
            },
        }

        self.ontology["object_properties"] = object_props

    def to_dict(self) -> Dict[str, Any]:
        """返回本体字典结构"""
        return self.ontology

    def to_json(self, save_path: str = "output/otn_ontology_test.json"):
        """保存本体为 JSON 文件（可直接用于后续建模、图谱、知识库）"""
        save_path = Path(save_path)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.ontology, f, ensure_ascii=False, indent=2)
        print(f"✅ 本体 JSON 已保存至：{save_path}")

    def to_rdf_script(self, save_path: str = "output/otn_ontology_script.rdf"):
        """【可选】生成 RDF/Turtle 格式的本体文本（适合语义网工具）"""
        # 这里可以根据需要实现 RDF/Turtle 格式的输出
        # 初步测试通过，可以由microsoft ontology playground等工具成功导入
        # TODO: 但目前生成的RDF文件在一些工具中可能会有解析问题（如缺少必要的OWL公理或命名空间声明），需要进一步调整和完善生成逻辑以确保兼容性。
        rdf_content = []
        rdf_content.append(f'<?xml version="1.0" encoding="UTF-8"?>')
        rdf_content.append(f'<rdf:RDF')
        rdf_content.append(f'    xml:base="http://example.org/ontology/otn-ontology/"')
        rdf_content.append(f'    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        rdf_content.append(f'    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        rdf_content.append(f'    xmlns:owl="http://www.w3.org/2002/07/owl#"')
        rdf_content.append(f'    xmlns:xsd="http://www.w3.org/2001/XMLSchema#"')
        rdf_content.append(f'    xmlns:ont="http://example.org/ontology/otn-ontology#">')
        rdf_content.append(f'')

        rdf_content.append(f'    <owl:Ontology rdf:about="http://example.org/ontology/otn-ontology/">')
        rdf_content.append(f'        <rdfs:label>otn ontology</rdfs:label>')
        rdf_content.append(f'        <rdfs:comment>Generated ontology for otn resources</rdfs:comment>')
        rdf_content.append(f'    </owl:Ontology>')
        rdf_content.append(f'')

        # 写入类定义
        rdf_content.append(f'    <!-- ====================== -->')
        rdf_content.append(f'    <!-- Entity Types (Classes) -->')
        rdf_content.append(f'    <!-- ====================== -->')
        rdf_content.append(f'')
        for cls_en, cls_info in self.ontology["classes"].items():
            rdf_content.append(f'    <owl:Class rdf:about="http://example.org/ontology/otn-ontology#{cls_en}">')
            rdf_content.append(f'        <rdfs:label>{cls_en}</rdfs:label>')
            rdf_content.append(f'        <rdfs:name>{cls_info["name"]}</rdfs:name>')
            rdf_content.append(f'        <ont:shortName>{cls_info["short_name"]}</ont:shortName>')
            rdf_content.append(f'        <rdfs:comment>{cls_info["comment"]}</rdfs:comment>')
            rdf_content.append(f'    </owl:Class>')
        rdf_content.append(f'')

        # 写入数据属性定义
        rdf_content.append(f'    <!-- =============== -->')
        rdf_content.append(f'    <!-- Data Properties -->')
        rdf_content.append(f'    <!-- =============== -->')
        rdf_content.append(f'')
        for prop_en, prop_info in self.ontology["data_properties"].items():
            rdf_content.append(f'    <owl:DatatypeProperty rdf:about="http://example.org/ontology/otn-ontology#{prop_en}">')
            rdf_content.append(f'        <rdfs:label>{prop_en}</rdfs:label>')
            rdf_content.append(f'        <rdfs:name>{prop_info["name"]}</rdfs:name>')
            rdf_content.append(f'        <rdfs:domain rdf:resource="http://example.org/ontology/otn-ontology#{prop_info["domain"]}"/>')
            rdf_content.append(f'        <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#{prop_info["range"]}"/>')
            rdf_content.append(f'        <rdfs:comment>{prop_info["comment"]}</rdfs:comment>')
            if prop_info["has_enumeration"]:
                enum_values = ",".join(prop_info["enumeration_values"])
                rdf_content.append(f'        <ont:enumValues>{enum_values}</ont:enumValues>')
            rdf_content.append(f'    </owl:DatatypeProperty>')
        rdf_content.append(f'')

        # 写入对象属性定义
        rdf_content.append(f'    <!-- ================= -->')
        rdf_content.append(f'    <!-- Object Properties -->')
        rdf_content.append(f'    <!-- ================= -->')
        rdf_content.append(f'')
        # TODO: if the Object Property contains some other info like fromEntity, it should also be added to the RDF output
        for prop_en, prop_info in self.ontology["object_properties"].items():
            rdf_content.append(f'    <owl:ObjectProperty rdf:about="http://example.org/ontology/otn-ontology#{prop_en}">')
            rdf_content.append(f'        <rdfs:label>{prop_en}</rdfs:label>')
            rdf_content.append(f'        <rdfs:domain rdf:resource="http://example.org/ontology/otn-ontology#{prop_info["domain"]}"/>')
            rdf_content.append(f'        <rdfs:range rdf:resource="http://example.org/ontology/otn-ontology#{prop_info["range"]}"/>')
            rdf_content.append(f'        <rdfs:comment>{prop_info["comment"]}</rdfs:comment>')
            rdf_content.append(f'        <ont:cardinality>{prop_info["cardinality"]}</ont:cardinality>')
            rdf_content.append(f'    </owl:ObjectProperty>')

        rdf_content.append(f'</rdf:RDF>')
        rdf_content.append(f'')
        
        # TODO: 可以考虑使用专业的 RDF 库（如 rdflib）来生成更规范的 RDF 输出，目前这里是简化实现
        # TODO: 改为流式写入文件，避免内存占用过大
        with open(save_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(rdf_content))
        print(f"✅ 本体 RDF 已保存至：{save_path}")

    def to_rdf_lib(self, save_path: str = "output/otn_ontology_lib.rdf"):
        """使用RDFLib等库生成更规范的 RDF 输出（可选）"""
        # 初步测试通过，可以由microsoft ontology playground等工具成功导入

        # 定义命名空间
        g = Graph()
        ex = Namespace("http://example.org/ontology/otn-ontology#")
        ontology_uri = URIRef("http://example.org/ontology/otn-ontology")
        g.bind("ex", ex)
        g.bind("owl", OWL)
        g.bind("rdf", RDF)
        g.bind("rdfs", RDFS)
        g.bind("xsd", XSD)

        # 写入本体声明
        g.add((ontology_uri, RDF.type, OWL.Ontology))
        g.add((ontology_uri, RDFS.label, Literal("otn ontology")))
        g.add((ontology_uri, RDFS.comment, Literal("Generated ontology for otn resources")))

        # 声明自定义属性 (annotation properties)
        g.add((ex.shortName, RDF.type, OWL.AnnotationProperty))
        g.add((ex.shortName, RDFS.label, Literal("short name")))
        g.add((ex.name, RDF.type, OWL.AnnotationProperty))
        g.add((ex.name, RDFS.label, Literal("cn name")))
        g.add((ex.enumValues, RDF.type, OWL.AnnotationProperty))
        g.add((ex.enumValues, RDFS.label, Literal("enumeration values")))
        g.add((ex.cardinality, RDF.type, OWL.AnnotationProperty))
        g.add((ex.cardinality, RDFS.label, Literal("cardinality")))

        # 1. 写入类定义
        for cls_en, cls_info in self.ontology["classes"].items():
            class_uri = ex[cls_en]
            g.add((class_uri, RDF.type, OWL.Class))
            g.add((class_uri, RDFS.label, Literal(cls_info["label"])))
            g.add((class_uri, RDFS.comment, Literal(cls_info["comment"])))
            g.add((class_uri, ex.name, Literal(cls_info["name"])))
            g.add((class_uri, ex.shortName, Literal(cls_info["short_name"])))
        
        # 2. 写入数据属性定义
        for prop_en, prop_info in self.ontology["data_properties"].items():
            prop_uri = ex[prop_en]
            g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            g.add((prop_uri, RDFS.label, Literal(prop_info["label"])))
            g.add((prop_uri, RDFS.domain, ex[prop_info["domain"]]))
            
            # 处理 XSD 类型
            xsd_type = prop_info["range"]
            if xsd_type.startswith("xsd:"):
                xsd_type = xsd_type[4:]  # 去掉 "xsd:" 前缀, 得到如 "string", "integer" 等
            g.add((prop_uri, RDFS.range, XSD[xsd_type]))
            
            g.add((prop_uri, RDFS.comment, Literal(prop_info["comment"])))
            g.add((prop_uri, ex.name, Literal(prop_info["name"])))
            
            if prop_info["has_enumeration"]:
                enum_values = ",".join(prop_info["enumeration_values"])
                g.add((prop_uri, ex.enumValues, Literal(enum_values)))
        
        # 3. 写入对象属性定义
        for prop_en, prop_info in self.ontology["object_properties"].items():
            prop_uri = ex[prop_en]
            g.add((prop_uri, RDF.type, OWL.ObjectProperty))
            g.add((prop_uri, RDFS.label, Literal(prop_info["label"])))
            g.add((prop_uri, RDFS.domain, ex[prop_info["domain"]]))
            g.add((prop_uri, RDFS.range, ex[prop_info["range"]]))
            g.add((prop_uri, RDFS.comment, Literal(prop_info["comment"])))
            g.add((prop_uri, ex.cardinality, Literal(prop_info["cardinality"])))
        
        # 4. 其他 OWL 公理，如类之间的关系、属性的特性等，可以根据需要添加

        # 调试：打印图中三元组的数量
        print(f"Total triples: {len(g)}")
        # 检查是否有 OWL 类
        owl_classes = list(g.triples((None, RDF.type, OWL.Class)))
        print(f"OWL classes: {len(owl_classes)}")
        for c in owl_classes[:4]:
            print(f"  - {c[0]}")
        # 检查是否有本体声明
        ontologies = list(g.triples((None, RDF.type, OWL.Ontology)))
        print(f"Ontology declarations: {len(ontologies)}")
        
        # 5. 保存为 RDF 文件, 注意使用 pretty-xml 格式以提高可读性与兼容性
        g.serialize(destination=save_path, format="pretty-xml")

    def print_ontology_summary(self):
        """打印本体概览（方便调试、查看结果）"""
        print("=" * 60)
        print(f"📊 otn资源本体构建完成")
        print(f"领域：{self.ontology['name_cn']}({self.ontology['name_en']})")
        print(f"类总数：{len(self.ontology['classes'])}")
        print(f"数据属性总数：{len(self.ontology['data_properties'])}")
        print(f"枚举类型属性数：{len(self.enum_dictionary)}")
        print("=" * 60)

        # 展示前3个类示例
        for idx, (cls_en, cls_info) in enumerate(self.ontology["classes"].items()):
            if idx >= 3:
                print("...")
                break
            prop_count = len(cls_info["data_properties"])
            print(f"🔹 类：{cls_en} | {cls_info['name']} | 属性数：{prop_count}")

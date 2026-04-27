# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

from agents.data_loader import DataLoaderAgent
from agents.ontology_generator import OntologyGeneratorAgent
from agents.extractor import EntityRelationExtractorAgent
from agents.fusion import KnowledgeFusionAgent
from agents.kg_builder import KGConstructorAgent
from agents.storage import StorageAgent

# ======================
# 1. 配置项
# ======================
EXCEL_PATH = "data/资源数据模型.xlsx"
OWL_OUTPUT = "output/telecom_resource.owl"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")

# ======================
# 2. 启动 KG 构建流水线
# ======================
if __name__ == "__main__":
    # 1. 加载 Excel 资源模型
    loader = DataLoaderAgent(EXCEL_PATH)
    classes, attributes, relations, enums = loader.load()

    # 2. 自动生成 Ontology (OWL)
    ontology = OntologyGeneratorAgent.generate(classes, attributes, relations, enums)
    ontology.save(OWL_OUTPUT)

    # 3. 自动抽取实体 + 关系
    extractor = EntityRelationExtractorAgent(classes, attributes, relations)
    entities, relations_triples = extractor.extract()

    # 4. 知识融合（对齐/去重）
    fusion = KnowledgeFusionAgent()
    entities_clean, triples_clean = fusion.fuse(entities, relations_triples)

    # 5. 构建知识图谱
    kg_builder = KGConstructorAgent()
    kg = kg_builder.build(entities_clean, triples_clean)

    # 6. 存入 Neo4j + 可视化
    storage = StorageAgent(NEO4J_URI, NEO4J_AUTH)
    storage.save_to_neo4j(kg)

    print("✅ 电信资源知识图谱构建完成！")
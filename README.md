# NbiOntology
Transport Networks Knowledge Graph Based on NBI

## 技术栈
Python + `pandas`（读 Excel）+ `rdflib/owlready2`（生成 OWL）

## 核心能力
- 自动读取多 Sheet 北向 Excel
- 自动生成：本体类、数据属性、关联关系、枚举类
- 直接输出`.rdf/.owl`文件，可直接导入 Protege/Neo4j
- 支持增量更新、批量导入全网北向模型

## 流水线 6 大步骤
1. **Data Loadert**：加载运营商 Excel 北向资源模型
2. **Ontology Generator**：自动生成 OWL 本体
3. **Entity & Relation Extractor**：抽取实体 / 关系 / 属性
4. **Knowledge Fusion**：实体对齐、去重、标准化
5. **Constructor**：生成三元组 + 构建图
6. **Storage & Visualization**：存入 Neo4j / 输出 OWL

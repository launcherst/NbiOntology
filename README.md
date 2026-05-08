# NbiOntology
Transport Networks Knowledge Graph Based on NBI

## 技术栈
- Python
- `pandas`（读取 Excel）
- `rdflib`（生成 OWL）
- LLM：Ollama本地模型
- SPARQL 查询：rdflib.plugins.sparql 足够小型图谱。
- 可视化：Mermaid 流程图在浏览器端渲染，零依赖。

## 整体架构
<img width="3594" height="574" alt="deepseek_mermaid_20260508_ebc858" src="https://github.com/user-attachments/assets/e030d858-9c18-4d87-9ce3-a693eb69cae8" />

- 数据层：Excel 定义资源/性能模型，实例数据按模型组织为 RDF。
- 知识层：本体（TBox）+ 实例（ABox）构成完整知识图谱。
- 分析层：基于 LangChain 的 Agent，封装 SPARQL 查询工具，由 LLM 决策调用。
- 展示层：Streamlit 构建的轻量 Web 界面

## 流水线
Excel实例数据 → 生成RDF实例文件 → 加载图谱 → LLM Agent(SPARQL) → 返回答案

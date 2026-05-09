# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.3

import streamlit as st
import re
from pathlib import Path
from agents.llm_agent import create_otn_agent, init_knowledge_graph


st.set_page_config(page_title="OTN 知识图谱问答", page_icon="🔍", layout="wide")

st.title("OTN 网络知识图谱问答")
st.caption("基于 RDF 知识图谱 + LLM Agent 的 OTN 网络分析验证原型")

# ---- sidebar ----
with st.sidebar:
    st.header("配置")
    model_name = st.text_input("Ollama 模型名称", value="gemma4:e2b")
    ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")

    st.divider()
    onto_ok = Path("output/otn_ontology_lib.rdf").exists()
    inst_ok = Path("output/instances.ttl").exists()
    st.caption(f"本体文件: {'已生成' if onto_ok else '未生成'} otn_ontology_lib.rdf")
    st.caption(f"实例文件: {'已生成' if inst_ok else '未生成'} instances.ttl")

    if st.button("重新加载知识图谱"):
        with st.spinner("加载中..."):
            init_knowledge_graph()
        st.success("知识图谱已加载")

    st.divider()
    st.caption("验收查询示例:")
    st.code("全网有多少个400G端口？", language=None)
    st.code("画出网络拓扑图", language=None)
    st.code("温度超过70度的板卡有哪些？", language=None)
    st.code("网元位置分布情况怎么样？", language=None)

# ---- session state ----
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "graph_loaded" not in st.session_state:
    try:
        init_knowledge_graph()
        st.session_state.graph_loaded = True
    except Exception:
        st.session_state.graph_loaded = False

# ---- chat display ----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- input ----
if prompt := st.chat_input("输入问题, 例如: 全网有多少个400G端口？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not st.session_state.graph_loaded:
            st.error("知识图谱未加载, 请先运行 `python main.py` 生成本体和实例文件")
        else:
            if st.session_state.agent is None:
                with st.spinner("正在加载 LLM 模型 (首次加载较慢)..."):
                    try:
                        st.session_state.agent = create_otn_agent(
                            model_name=model_name, base_url=ollama_url
                        )
                    except Exception as e:
                        st.error(f"无法连接 Ollama: {e}\n请确保 Ollama 已启动且模型 {model_name} 已下载")
                        st.stop()

            agent = st.session_state.agent
            with st.spinner("思考中..."):
                try:
                    result = agent.invoke({
                        "messages": [{"role": "user", "content": prompt}]
                    })
                    messages = result.get("messages", [])
                    # extract last AI message
                    answer = ""
                    for m in reversed(messages):
                        if hasattr(m, "content") and m.type == "ai":
                            answer = m.content
                            break
                    if not answer and messages:
                        answer = str(messages[-1])
                    if isinstance(answer, (list, tuple)):
                        answer = "".join(str(x) for x in answer)
                except Exception as e:
                    answer = f"查询失败: {str(e)}"

            st.markdown(answer)

            # 提取并渲染 Mermaid 代码块
            mermaid_match = re.search(
                r"```mermaid\s*\n(.*?)```", answer, re.DOTALL | re.IGNORECASE
            )
            if mermaid_match:
                mermaid_code_patch = mermaid_match.group(1).strip()
                st.markdown(f"```mermaid\n{mermaid_code_patch}\n```")

            st.session_state.messages.append({"role": "assistant", "content": answer})

# ---- initial state ----
if not st.session_state.messages:
    if st.session_state.graph_loaded:
        st.info("知识图谱已就绪, 请在下方输入问题开始查询。")
    else:
        st.warning("知识图谱尚未生成, 请先运行以下命令:\n\n```bash\npython main.py\n```")

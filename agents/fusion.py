# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

class KnowledgeFusionAgent:
    def fuse(self, entities, triples):
        # 去重、实体对齐、标准化
        entities_clean = list({e["id"]: e for e in entities}.values())
        return entities_clean, triples
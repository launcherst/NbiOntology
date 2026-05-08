# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

class EntityRelationExtractor:
    def __init__(self, classes, attrs, rels):
        self.classes = classes
        self.attrs = attrs
        self.rels = rels

    def extract(self):
        entities = []
        triples = []

        # 抽取实体
        for _, row in self.classes.iterrows():
            pass

        # 抽取关系三元组
        for _, row in self.rels.iterrows():
            pass

        return entities, triples
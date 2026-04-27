# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

from owlready2 import *

class OntologyGeneratorAgent:
    @staticmethod
    def generate(classes, attrs, rels, enums):
        onto = get_ontology("http://telecom-kg/resource#")

        with onto:
            # 顶层类
            class TelecomResource(Thing): pass
            class Port(TelecomResource): pass
            class Equipment(TelecomResource): pass
            class Rack(TelecomResource): pass
            class Link(TelecomResource): pass

            # 自动创建类
            for _, row in classes.iterrows():
                cls_name = row["对象编码"]
                type(cls_name, (TelecomResource,), {})

            # 自动创建属性
            for _, row in attrs.iterrows():
                attr_name = row["字段编码"]
                DataProperty(attr_name)

            # 自动创建关系
            for _, row in rels.iterrows():
                rel_name = row["关系名称"]
                ObjectProperty(rel_name)

        return onto
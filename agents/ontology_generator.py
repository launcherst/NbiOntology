# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

from typing import Dict, List, Any
import json
from pathlib import Path


class OntologyGenerator:
    """
    电信领域本体生成器
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
        for cn_name, info in self.resource_map.items():
            en_name = info["en_name"]
            short_name = info["short_name"]

            # 类结构：英文类名作为key
            self.ontology["classes"][en_name] = {
                "name_en": en_name,
                "name_cn": cn_name,
                "short_name": short_name,
                "description": f"otn资源类: {cn_name}",
                "data_properties": [],  # 该类拥有的数据属性列表
            }

    def _generate_data_properties(self):
        """为每个类绑定数据属性，并生成全局属性定义"""
        # 遍历每个资源类（英文名称）
        for class_en, attrs in self.resource_attributes.items():
            if class_en not in self.ontology["classes"]:
                continue

            # 遍历该类的所有属性
            for attr in attrs:
                prop_en = attr["name_en"]
                prop_cn = attr["name_cn"]

                # 1. 把属性加入类的属性列表
                self.ontology["classes"][class_en]["data_properties"].append(prop_en)

                # 2. 构建全局数据属性定义
                self.ontology["data_properties"][prop_en] = {
                    "name_en": prop_en,
                    "name_cn": prop_cn,
                    "data_type": attr["type"],
                    "required": attr["required"],
                    "description": attr["desc"],
                    "example": attr["example"],
                    "has_enumeration": prop_cn
                    in self.enum_dictionary,  # 是否是枚举属性
                    "enumeration_values": self.enum_dictionary.get(prop_cn, []),
                }

    # ============================
    # 【核心新增】定义类之间的关联关系
    # ============================
    def _generate_rel_properties(self):
        """定义对象属性（类与类之间的关联关系）"""
        object_props = {
            # 格式：
            # "属性英文名": {
            #   "name_cn": 中文名,
            #   "domain": 定义域（从哪个类出发）,
            #   "range": 值域（指向哪个类）
            # }
            # 板卡 归属于 设备
            "belongToDevice": {
                "name_cn": "归属于设备",
                "domain": "Board",
                "range": "Device",
            },
            # 端口 归属于 板卡
            "belongToBoard": {
                "name_cn": "归属于板卡",
                "domain": "Port",
                "range": "Board",
            },
            # 光波道 包含 子网连接
            "containsSubnetConnection": {
                "name_cn": "包含子网连接",
                "domain": "LightPath",
                "range": "SubnetConnection",
            },
            # 子网连接 有顺序号
            "hasOrder": {
                "name_cn": "拥有顺序号",
                "domain": "SubnetConnection",
                "range": "Literal",  # 数值属性
            },
        }

        self.ontology["object_properties"] = object_props

    def to_dict(self) -> Dict[str, Any]:
        """返回本体字典结构"""
        return self.ontology

    def to_json(self, save_path: str = "otn_ontology.json"):
        """保存本体为 JSON 文件（可直接用于后续建模、图谱、知识库）"""
        save_path = Path(save_path)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.ontology, f, ensure_ascii=False, indent=2)
        print(f"✅ 本体 JSON 已保存至：{save_path}")

    def to_owl_text(self) -> str:
        """生成简易 OWL 本体文本（可导入 Protegé 等本体工具）"""
        owl_lines = [
            '<?xml version="1.0"?>',
            '<Ontology xmlns="http://www.w3.org/2002/07/owl#">',
            f"  <Annotation IRI=\"#name_cn\" value=\"{self.ontology['name_cn']}\"/>",
            f"  <Annotation IRI=\"#name_en\" value=\"{self.ontology['name_en']}\"/>",
            "",
        ]

        # 写入类
        owl_lines.append("  <!-- 电信资源类 -->")
        for cls_en, cls_info in self.ontology["classes"].items():
            owl_lines.extend(
                [
                    f'  <Class IRI="#{cls_en}">',
                    f"    <Annotation IRI=\"#label_cn\" value=\"{cls_info['name_cn']}\"/>",
                    f"    <Annotation IRI=\"#short_name\" value=\"{cls_info['short_name']}\"/>",
                    "  </Class>",
                ]
            )

        owl_lines.append("\n  <!-- 数据属性 -->")
        # 写入数据属性
        for prop_en, prop_info in self.ontology["data_properties"].items():
            has_enum = prop_info["has_enumeration"]
            enum_str = " | ".join(prop_info["enumeration_values"]) if has_enum else "无"

            owl_lines.extend(
                [
                    f'  <DataProperty IRI="#{prop_en}">',
                    f"    <Annotation IRI=\"#label_cn\" value=\"{prop_info['name_cn']}\"/>",
                    f"    <Annotation IRI=\"#data_type\" value=\"{prop_info['data_type']}\"/>",
                    f"    <Annotation IRI=\"#required\" value=\"{prop_info['required']}\"/>",
                    f'    <Annotation IRI="#enumeration" value="{enum_str}"/>',
                    "  </DataProperty>",
                ]
            )

        owl_lines.append("</Ontology>")
        return "\n".join(owl_lines)

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
            print(f"🔹 类：{cls_en} | {cls_info['name_cn']} | 属性数：{prop_count}")

# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

import pandas as pd
import re
from typing import Dict, List, Any
from pathlib import Path


class DataLoaderAgent:
    """
    从Excel加载数据, 输出标准化结构
    直接对接电信领域本体构建流水线
    """

    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)

        # 资源对象映射表（核心：中文 → 英文、简称）
        self.resource_map: Dict[str, Dict[str, str]] = {}

        # 最终输出数据（以 英文名称 为key）
        self.resource_attributes: Dict[str, List[Dict]] = {}
        self.enum_dictionary: Dict[str, Dict[str, str]] = {}

    def load_all(self) -> Dict[str, Any]:
        """统一入口：加载所有数据并返回标准结构"""
        self._load_resource_mapping()  # 加载清单：中文 → 英文、简称
        self._load_all_resource_attributes()  # 加载数字开头sheet的属性（英文key）
        self._load_enum_dictionary()  # 加载枚举字典
        _output = self._get_standard_output()  # 构建标准输出格式
        return _output

    def _load_resource_mapping(self):
        """
        加载【资源对象清单】
        建立映射：资源对象中文名称 → {英文名称, 简称}
        """
        df = pd.read_excel(self.excel_path, sheet_name="资源对象清单")

        """ # 读取【资源对象英文名称】列（本体构建用）
        self.resource_en_names = [
            str(x).strip() for x in df["资源对象英文名称"].dropna()
        ]

        # 读取【资源对象简称】列
        self.resource_short_names = [
            str(x).strip() for x in df["资源对象简称"].dropna()
        ]
        """

        # 按行构建映射（确保三列对应）
        for _, row in df.dropna(
            subset=["资源对象中文名称", "资源对象英文名称"]
        ).iterrows():
            cls_name_cn = str(row["资源对象中文名称"]).strip()
            cls_name_en = str(row["资源对象英文名称"]).strip()
            short_name = str(row["资源对象简称"]).strip()

            self.resource_map[cls_name_cn] = {"cls_name_en": cls_name_en, "short_name": short_name}

    def _extract_cn_name(self, sheet_name: str) -> str:
        """
        规则：
        1. 去掉【开头】的 数字 + 特殊符号（、,.\-_等）
        2. 保留【后面所有内容】，包括数字、字母、特殊符号
        3. 返回清理后的名称，用于匹配【资源对象中文名称】

        示例：
        "0、光网元" → "光网元"
        "1. OMC_123" → "OMC_123"
        "2-监控实例-A8" → "监控实例-A8"
        "3#端口@01" → "端口@01"
        """

        # 正则：匹配开头的 数字 + 所有非文字非字母符号，删除它们
        # ^ 表示开头
        # \d+ 表示一个或多个数字
        # [^\w\s]* 表示非字母、非数字、非文字的符号（、,.\-_#@%等）
        return re.sub(r"^\d+[^\w\s]*", "", sheet_name).strip()

    def _load_all_resource_attributes(self):
        """
        加载所有【数字开头】的sheet
        1. 提取纯中文
        2. 匹配清单 → 拿到英文名称
        3. 以英文名称为key存储属性
        """
        excel_file = pd.ExcelFile(self.excel_path)

        for sheet_name in excel_file.sheet_names:
            # 只处理：以 数字 开头 的sheet
            if not re.match(r"^\d", sheet_name):
                continue

            # 提取纯中文名称
            cls_name_cn = self._extract_cn_name(sheet_name)

            # 必须在资源清单中存在才加载
            if cls_name_cn not in self.resource_map:
                continue

            # 获取 英文名称（最终用这个做key）
            cls_name_en = self.resource_map[cls_name_cn]["cls_name_en"]

            # 读取属性
            try:
                df = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                df = df.dropna(subset=["属性英文名称"])
            except Exception:
                continue

            # 解析属性列表
            attr_list = []
            for _, row in df.iterrows():
                attr = {
                    "name_en": str(row["属性英文名称"]).strip(),
                    "name_cn": str(row["属性中文名称"]).strip(),
                    "type": str(row["字符类型"]).strip(),
                    "required": str(row["是否必填"]).strip() == "是",
                    "desc": (
                        str(row["取值范围及说明"]).strip()
                        if pd.notna(row["取值范围及说明"])
                        else ""
                    ),
                    "example": str(row["数据示例"]).strip(),
                }
                attr_list.append(attr)

            # ✅ 最终以【资源对象英文名称】为 key 存储
            self.resource_attributes[cls_name_en] = attr_list

    def _load_enum_dictionary(self):
        """
        加载【字典表】sheet: 枚举值定义
        构建枚举字典，结构如下：
        资源对象英文名称 → 属性英文名称 → [{value, desc}, ...]
        """
        df = pd.read_excel(self.excel_path, sheet_name="字典表")
        df = df.dropna(subset=["资源对象英文名称", "备注"])

        enum_map: Dict[str, Dict[str, List[Dict]]] = {}  # 资源对象 → 属性 → 枚举列表
        for _, row in df.iterrows():
            cls_name_en = str(row["资源对象英文名称"]).strip()
            attr_name_en = str(row["属性英文名称"]).strip()
            attr_name_cn = str(row["属性中文名称"]).strip()
            value = str(row["取值"]).strip()
            desc = str(row["备注"]).strip()

            # 层级1: 资源对象英文名称 -> 属性英文名称
            if cls_name_en not in enum_map:
                enum_map[cls_name_en] = {}
            # 层级2: 属性英文名称 -> 枚举列表
            if attr_name_en not in enum_map[cls_name_en]:
                enum_map[cls_name_en][attr_name_en] = []

            # 添加枚举值
            enum_map[cls_name_en][attr_name_en].append({"value": value, "desc": desc})

        self.enum_dictionary = enum_map

    def _get_standard_output(self) -> Dict[str, Any]:
        """
        构建流水线标准输出格式
        枚举字典按「资源对象英文名称→属性英文名称→枚举列表」层级返回
        """
        return {
            "resource_en_names": list(
                self.resource_attributes.keys()
            ),  # 所有资源英文名称
            "resource_map": self.resource_map,  # 中文→英文→简称映射
            "resource_attributes": self.resource_attributes,  # 英文名称→属性
            "enum_dictionary": self.enum_dictionary,  # 属性枚举
        }

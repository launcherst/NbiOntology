# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

import pandas as pd
import re
import random
import datetime
from typing import Dict, List, Any
from pathlib import Path


class DataLoaderAgent:
    """
    从Excel加载数据, 输出标准化结构
    直接对接otn本体构建流水线
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

        # 按行构建映射（确保三列对应）
        for _, row in df.dropna(
            subset=["资源对象中文名称", "资源对象英文名称"]
        ).iterrows():
            cls_name_cn = str(row["资源对象中文名称"]).strip()
            cls_name_en = str(row["资源对象英文名称"]).strip()
            short_name = str(row["资源对象简称"]).strip()

            self.resource_map[cls_name_cn] = {
                "cls_name_en": cls_name_en,
                "short_name": short_name,
            }

    def _extract_cn_name(self, sheet_name: str) -> str:
        """
        规则：
        1. 去掉【开头】的 数字 + 特殊符号（、,.\\-_等）
        2. 保留【后面所有内容】，包括数字、字母、特殊符号
        3. 返回清理后的名称，用于匹配【资源对象中文名称】

        示例：
        "0、光网元" → "光网元"
        "1. OMC_123" → "OMC_123"
        "2-监控实例-A8" → "监控实例-A8"
        "3#端口@01" → "端口@01"
        """

        # 正则：匹配开头的 数字 + 所有非文字非字母符号，删除它们
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
            attributes = {}
            for _, row in df.iterrows():
                attributes.update({
                    str(row.get("属性英文名称", "")).strip(): {
                        "name_cn": str(row.get("属性中文名称", "")).strip(),
                        "type": str(row.get("字符类型", "")).strip(),
                        "required": str(row.get("是否必填", "")).strip() == "是",
                        "desc": (
                            str(row.get("取值范围及说明", "")).strip()
                            if pd.notna(row.get("取值范围及说明", ""))
                            else ""
                        ),
                        "example": str(row.get("数据示例", "")).strip(),
                    },
                })

            # ✅ 最终以【资源对象英文名称】为 key 存储
            self.resource_attributes[cls_name_en] = attributes

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


class InstanceDataLoader:
    """从CSV文件加载NBI实例数据, 输出结构化字典供instances_generator使用"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def load_all(self, sample_ne: int = None) -> Dict[str, Any]:
        """加载所有实例数据, 可选按NE数量采样以减少图谱规模"""
        import random

        result = {}
        # 1. Load NE first
        ne_instances = self._load_csv("NE")
        if sample_ne and len(ne_instances) > sample_ne:
            random.seed(42)
            ne_instances = random.sample(ne_instances, sample_ne)
        result["NE"] = ne_instances
        ne_uids = {n["rmUID"] for n in ne_instances}

        # 2. Load Card - filter by sampled NE UIDs
        cards = self._load_csv("Card")
        cards = [c for c in cards if c.get("nermUID", "") in ne_uids]
        result["Card"] = cards
        card_uids = {c["rmUID"] for c in cards}

        # 3. Load Port - filter by sampled NE UIDs or Card UIDs
        ports = self._load_csv("Port")
        ports = [p for p in ports if p.get("nermUID", "") in ne_uids]
        result["Port"] = ports
        port_uids = {p["rmUID"] for p in ports}

        # 4. Load TopoLink - filter by sampled NE UIDs
        links = self._load_csv("TopoLink")
        links = [
            l for l in links
            if l.get("aEndNermUID", "") in ne_uids or l.get("zEndNermUID", "") in ne_uids
        ]
        result["TopoLink"] = links

        print(f"  Loaded: {len(ne_instances)} NE, {len(cards)} Card, "
              f"{len(ports)} Port, {len(links)} TopoLink")
        return result

    def _find_csv(self, cls_name: str) -> Path:
        """根据类名查找对应的CSV文件"""
        prefix_map = {
            "NE": "CM-OTN-NEL",
            "Card": "CM-OTN-CRD",
            "Port": "CM-OTN-PRT",
            "TopoLink": "CM-OTN-TPL",
        }
        prefix = prefix_map.get(cls_name, "")
        # prefer shorter filename (newer conversion format)
        candidates = sorted(self.data_dir.glob(f"{prefix}*.csv"))
        if not candidates:
            return None
        # pick the one with shortest name (most direct conversion)
        return min(candidates, key=lambda p: len(p.name))

    def _load_csv(self, cls_name: str) -> List[Dict[str, str]]:
        """加载某个类的CSV数据"""
        csv_path = self._find_csv(cls_name)
        if not csv_path:
            print(f"  [WARN] No CSV found for {cls_name}")
            return []
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        df = df.fillna("")
        return df.to_dict(orient="records")


class PerformanceDataLoader:
    """从性能Excel加载性能数据定义, 并为实例生成模拟性能数据"""

    def __init__(self, excel_path: str = "data/NbiExampleOtnPerformance.xlsx"):
        self.excel_path = Path(excel_path)
        self.performance_defs: Dict[str, List[Dict]] = {}

    def load_definitions(self) -> Dict[str, List[Dict]]:
        """加载性能指标定义"""
        xf = pd.ExcelFile(self.excel_path)
        cls_map = {"1.板卡": "Card", "8、网元": "NE", "9、端口": "Port"}

        for sheet_name in xf.sheet_names:
            if sheet_name not in cls_map:
                continue
            cls_en = cls_map[sheet_name]
            df = pd.read_excel(self.excel_path, sheet_name=sheet_name)
            df = df.dropna(subset=["英文名称"])
            metrics = []
            for _, row in df.iterrows():
                name_en = str(row["英文名称"]).strip()
                if name_en == "rmUID":
                    continue  # skip ID field
                metrics.append({
                    "name_en": name_en,
                    "name_cn": str(row.get("中文名称", "")).strip(),
                    "type": str(row.get("字符类型", "")).strip(),
                    "unit": str(row.get("单位", "")).strip() if pd.notna(row.get("单位", "")) else "",
                })
            self.performance_defs[cls_en] = metrics

        return self.performance_defs

    def generate_sample_records(
        self, instances: Dict[str, List[Dict]], records_per_resource: int = 2
    ) -> List[Dict]:
        """为实例生成模拟性能记录"""
        import random
        import datetime

        random.seed(42)
        records = []
        base_ts = datetime.datetime(2026, 5, 8, 12, 0, 0)

        for cls_en, metrics in self.performance_defs.items():
            if cls_en not in instances:
                continue
            for inst in instances[cls_en]:
                for _ in range(records_per_resource):
                    ts = base_ts + datetime.timedelta(minutes=random.randint(0, 1440))
                    for m in metrics:
                        val = self._simulate_value(m["name_en"])
                        records.append({
                            "resourceUID": inst["rmUID"],
                            "resourceType": cls_en,
                            "metricName": m["name_en"],
                            "metricValue": val,
                            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                        })
        print(f"  Generated {len(records)} sample PerformanceRecord instances")
        return records

    def _simulate_value(self, metric_name: str) -> float:
        """根据指标名模拟合理数值"""
        import random
        ranges = {
            "temperature": (20, 85),
            "cpu": (5, 95),
            "mem": (10, 90),
            "runtimePower": (100, 2000),
            "consumption": (0.5, 50),
            "consumptionReduce": (0, 10),
            "consumptionReduceTime": (0, 60),
        }
        lo, hi = ranges.get(metric_name, (0, 100))
        return round(random.uniform(lo, hi), 2)

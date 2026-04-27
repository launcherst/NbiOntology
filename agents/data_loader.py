# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.1

import pandas as pd

class DataLoaderAgent:
    def __init__(self, excel_path):
        self.path = excel_path

    def load(self):
        # 读取你的 4 个核心 sheet（运营商北向标准）
        df_classes = pd.read_excel(self.path, sheet_name="对象类")
        df_attrs = pd.read_excel(self.path, sheet_name="属性")
        df_rels = pd.read_excel(self.path, sheet_name="关系")
        df_enums = pd.read_excel(self.path, sheet_name="枚举")

        return df_classes, df_attrs, df_rels, df_enums
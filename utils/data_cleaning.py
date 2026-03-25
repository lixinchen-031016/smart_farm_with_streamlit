"""
数据清洗模块 - 独立可复用的数据清洗功能
提供异常值检测、缺失值处理、清洗规则模板等功能
"""

import json
from datetime import datetime
from typing import Dict, Tuple, Any

import numpy as np
import pandas as pd

from utils.anomaly_detection import (
    detect_outliers_iqr,
    detect_outliers_zscore,
    detect_outliers_isolation_forest,
    remove_anomalies,
    get_anomaly_summary
)


class DataCleaningRule:
    """数据清洗规则类

    用于定义和管理数据清洗规则，包括异常值检测、缺失值处理、重复行删除和列删除等配置。
    """
    
    def __init__(self, name: str, description: str = ""):
        """初始化数据清洗规则

        Args:
            name (str): 规则名称
            description (str, optional): 规则描述，默认为空字符串
        """
        self.name = name
        self.description = description
        self.created_at = datetime.now()
        self.rules = {
            'outlier_detection': None,  # 异常值检测配置
            'missing_value_handling': None,  # 缺失值处理配置
            'duplicate_removal': False,  # 是否删除重复行
            'column_dropping': []  # 要删除的列
        }
    
    def configure_outlier_detection(self, method: str, params: Dict[str, Any]):
        """配置异常值检测

        配置异常值检测方法和参数。

        Args:
            method (str): 异常值检测方法，如'iqr'、'zscore'或'isolation_forest'
            params (Dict[str, Any]): 检测方法的参数
        """
        self.rules['outlier_detection'] = {
            'method': method,
            'params': params
        }
    
    def configure_missing_value(self, column: str, method: str, fill_value: Any = None):
        """配置缺失值处理

        配置指定列的缺失值处理方法。

        Args:
            column (str): 列名
            method (str): 处理方法，如'delete'、'mean'、'median'或'mode'
            fill_value (Any, optional): 填充值，默认为None
        """
        if self.rules['missing_value_handling'] is None:
            self.rules['missing_value_handling'] = {}
        
        self.rules['missing_value_handling'][column] = {
            'method': method,
            'fill_value': fill_value
        }
    
    def set_duplicate_removal(self, enabled: bool):
        """设置是否删除重复行

        设置是否在清洗过程中删除重复行。

        Args:
            enabled (bool): 是否启用重复行删除
        """
        self.rules['duplicate_removal'] = enabled
    
    def add_column_to_drop(self, column: str):
        """添加要删除的列

        添加要在清洗过程中删除的列。

        Args:
            column (str): 列名
        """
        if column not in self.rules['column_dropping']:
            self.rules['column_dropping'].append(column)
    
    def to_dict(self) -> Dict:
        """转换为字典

        将规则对象转换为字典格式。

        Returns:
            Dict: 规则的字典表示
        """
        return {
            'name': self.name,
            'description': self.description,
            'created_at': str(self.created_at),
            'rules': self.rules
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DataCleaningRule':
        """从字典创建

        从字典创建规则对象。

        Args:
            data (Dict): 规则的字典表示

        Returns:
            DataCleaningRule: 创建的规则对象
        """
        rule = cls(data['name'], data.get('description', ''))
        rule.created_at = datetime.fromisoformat(data['created_at'])
        rule.rules = data['rules']
        return rule
    
    def save(self, filepath: str):
        """保存规则到文件

        将规则保存到指定文件。

        Args:
            filepath (str): 文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'DataCleaningRule':
        """从文件加载规则

        从指定文件加载规则。

        Args:
            filepath (str): 文件路径

        Returns:
            DataCleaningRule: 加载的规则对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class DataCleaner:
    """数据清洗器

    用于执行数据清洗操作，应用清洗规则并生成清洗报告。
    """
    
    def __init__(self):
        """初始化数据清洗器

        初始化清洗历史和统计信息。
        """
        self.cleaning_history = []
        self.statistics = {
            'total_operations': 0,
            'rows_removed': 0,
            'values_filled': 0,
            'outliers_removed': 0
        }
    
    def apply_rule(self, df: pd.DataFrame, rule: DataCleaningRule) -> Tuple[pd.DataFrame, Dict]:
        """应用清洗规则

        应用清洗规则到数据框，执行清洗操作并生成清洗报告。

        Args:
            df (pd.DataFrame): 要清洗的数据框
            rule (DataCleaningRule): 清洗规则

        Returns:
            Tuple[pd.DataFrame, Dict]: (清洗后的数据框, 清洗报告)
        """
        report = {
            'original_shape': df.shape,
            'operations': [],
            'quality_before': self._assess_data_quality(df),
            'quality_after': None
        }
        
        # 1. 删除重复行
        if rule.rules['duplicate_removal']:
            original_rows = len(df)
            df = df.drop_duplicates()
            removed = original_rows - len(df)
            if removed > 0:
                report['operations'].append({
                    'type': 'duplicate_removal',
                    'removed_rows': removed
                })
                self.statistics['rows_removed'] += removed
        
        # 2. 删除指定列
        if rule.rules['column_dropping']:
            df = df.drop(columns=rule.rules['column_dropping'])
            report['operations'].append({
                'type': 'column_dropping',
                'columns': rule.rules['column_dropping']
            })
        
        # 3. 处理缺失值
        if rule.rules['missing_value_handling']:
            for column, config in rule.rules['missing_value_handling'].items():
                if column not in df.columns:
                    continue
                
                method = config['method']
                if method == 'delete':
                    original_rows = len(df)
                    df = df.dropna(subset=[column])
                    removed = original_rows - len(df)
                    if removed > 0:
                        report['operations'].append({
                            'type': 'missing_value_deletion',
                            'column': column,
                            'removed_rows': removed
                        })
                        self.statistics['rows_removed'] += removed
                elif method in ['mean', 'median', 'mode']:
                    if method == 'mean':
                        fill_value = df[column].mean()
                    elif method == 'median':
                        fill_value = df[column].median()
                    else:
                        fill_value = df[column].mode()[0] if not df[column].mode().empty else 0
                    
                    missing_count = df[column].isnull().sum()
                    if missing_count > 0:
                        df[column] = df[column].fillna(fill_value)
                        report['operations'].append({
                            'type': 'missing_value_imputation',
                            'column': column,
                            'method': method,
                            'filled_count': missing_count,
                            'fill_value': fill_value
                        })
                        self.statistics['values_filled'] += missing_count
        
        # 4. 异常值检测与处理
        if rule.rules['outlier_detection']:
            outlier_config = rule.rules['outlier_detection']
            method = outlier_config['method']
            params = outlier_config['params']
            
            numeric_columns = params.get('columns', df.select_dtypes(include=[np.number]).columns.tolist())
            
            anomalies = {}
            if method == 'iqr':
                for col in numeric_columns:
                    if col in df.columns:
                        anomalies[col] = df[detect_outliers_iqr(df, col)].index.tolist()
            elif method == 'zscore':
                threshold = params.get('threshold', 3)
                for col in numeric_columns:
                    if col in df.columns:
                        anomalies[col] = df[detect_outliers_zscore(df, col, threshold)].index.tolist()
            elif method == 'isolation_forest':
                # 移除不属于 detect_outliers_isolation_forest 的参数
                if_params = {k: v for k, v in params.items() 
                            if k in ['contamination', 'n_estimators', 'max_samples', 'random_state']}
                outlier_series = detect_outliers_isolation_forest(
                    df, 
                    numeric_columns,
                    **if_params
                )
                for col in numeric_columns:
                    if col in df.columns:
                        anomalies[col] = df[outlier_series].index.tolist()
            
            if anomalies:
                # 如果配置了删除异常值
                if params.get('remove', False):
                    original_rows = len(df)
                    df = remove_anomalies(df, anomalies)
                    removed = original_rows - len(df)
                    report['operations'].append({
                        'type': 'outlier_removal',
                        'method': method,
                        'removed_rows': removed
                    })
                    self.statistics['outliers_removed'] += removed
                else:
                    # 仅标记异常值
                    report['outliers'] = anomalies
                    summary = get_anomaly_summary(anomalies)
                    report['outlier_summary'] = summary
        
        report['final_shape'] = df.shape
        report['quality_after'] = self._assess_data_quality(df)
        report['improvement'] = self._calculate_improvement(
            report['quality_before'], 
            report['quality_after']
        )
        
        self.cleaning_history.append(report)
        self.statistics['total_operations'] += 1
        
        return df, report
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict:
        """评估数据质量

        评估数据框的数据质量，包括缺失值统计等。

        Args:
            df (pd.DataFrame): 要评估的数据框

        Returns:
            Dict: 数据质量评估结果
        """
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        
        # 计算每列的缺失率
        missing_by_column = {}
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            missing_by_column[col] = {
                'count': int(missing_count),
                'percentage': float(missing_count / len(df) * 100) if len(df) > 0 else 0
            }
        
        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_cells': int(missing_cells),
            'missing_rate': float(missing_cells / total_cells * 100) if total_cells > 0 else 0,
            'completeness': float(100 - (missing_cells / total_cells * 100)) if total_cells > 0 else 100,
            'missing_by_column': missing_by_column
        }
    
    def _calculate_improvement(self, before: Dict, after: Dict) -> Dict:
        """计算清洗前后的改善情况

        计算数据清洗前后的数据质量改善情况。

        Args:
            before (Dict): 清洗前的数据质量评估结果
            after (Dict): 清洗后的数据质量评估结果

        Returns:
            Dict: 改善情况统计
        """
        completeness_improvement = after['completeness'] - before['completeness']
        missing_rate_reduction = before['missing_rate'] - after['missing_rate']
        
        return {
            'completeness_improvement': round(completeness_improvement, 2),
            'missing_rate_reduction': round(missing_rate_reduction, 2),
            'rows_removed': before['total_rows'] - after['total_rows'],
            'quality_score_change': round(completeness_improvement, 2)
        }
    
    def generate_report(self, report: Dict) -> str:
        """生成清洗报告

        根据清洗报告生成格式化的文本报告。

        Args:
            report (Dict): 清洗报告

        Returns:
            str: 格式化的清洗报告
        """
        lines = [
            "=" * 60,
            "数据清洗报告",
            "=" * 60,
            f"原始数据形状：{report['original_shape']}",
            f"清洗后数据形状：{report['final_shape']}",
            "",
            "清洗操作:",
            "-" * 60
        ]
        
        for op in report['operations']:
            op_type = op['type']
            if op_type == 'duplicate_removal':
                lines.append(f"✓ 删除重复行：{op['removed_rows']} 行")
            elif op_type == 'column_dropping':
                lines.append(f"✓ 删除列：{', '.join(op['columns'])}")
            elif op_type == 'missing_value_deletion':
                lines.append(f"✓ 删除 {op['column']} 列的缺失值：{op['removed_rows']} 行")
            elif op_type == 'missing_value_imputation':
                lines.append(f"✓ 填充 {op['column']} 列缺失值 ({op['method']}): {op['filled_count']} 个值")
            elif op_type == 'outlier_removal':
                lines.append(f"✓ 删除异常值 ({op['method']}): {op['removed_rows']} 行")
        
        lines.extend([
            "",
            "数据质量对比:",
            "-" * 60,
            f"清洗前完整率：{report['quality_before']['completeness']:.2f}%",
            f"清洗后完整率：{report['quality_after']['completeness']:.2f}%",
            f"质量提升：{report['improvement']['completeness_improvement']:+.2f}%",
            f"缺失率降低：{report['improvement']['missing_rate_reduction']:.2f}%",
            "",
            "=" * 60
        ])
        
        return "\n".join(lines)
    
    def create_template_rule(self, template_name: str, df: pd.DataFrame) -> DataCleaningRule:
        """基于数据分析创建模板规则

        根据数据框的分析结果创建清洗模板规则。

        Args:
            template_name (str): 模板名称
            df (pd.DataFrame): 要分析的数据框

        Returns:
            DataCleaningRule: 创建的模板规则
        """
        rule = DataCleaningRule(
            name=template_name,
            description=f"基于{len(df)}行数据自动生成的清洗模板"
        )
        
        # 默认启用删除重复行
        rule.set_duplicate_removal(True)
        
        # 分析各列，自动配置缺失值处理
        for col in df.columns:
            missing_rate = df[col].isnull().sum() / len(df)
            
            # 如果缺失率超过 50%，建议删除该列
            if missing_rate > 0.5:
                rule.add_column_to_drop(col)
            # 如果缺失率在 5%-50% 之间，使用中位数填充（数值型）或众数（分类型）
            elif missing_rate > 0.05:
                if df[col].dtype in [np.float64, np.int64]:
                    rule.configure_missing_value(col, 'median')
                else:
                    rule.configure_missing_value(col, 'mode')
        
        return rule


# 预定义的清洗模板
def create_agricultural_standard_template() -> DataCleaningRule:
    """创建农业数据标准清洗流程模板

    创建适用于智能农场传感器数据的标准清洗流程模板。

    Returns:
        DataCleaningRule: 农业数据标准清洗流程模板
    """
    rule = DataCleaningRule(
        name="农业数据标准清洗流程",
        description="适用于智能农场传感器数据的标准清洗流程"
    )
    
    # 删除重复行
    rule.set_duplicate_removal(True)
    
    # 配置异常值检测 - 使用 IQR 方法
    rule.configure_outlier_detection('iqr', {
        'columns': [],  # 空表示所有数值列
        'remove': True
    })
    
    # 配置常见农业数据列的缺失值处理
    standard_columns = {
        'temperature': 'median',
        'humidity': 'median',
        'soil_moisture': 'median',
        'soil_nutrient': 'median',
        'light_intensity': 'median'
    }
    
    for col_pattern, method in standard_columns.items():
        rule.configure_missing_value(col_pattern, method)
    
    return rule


def create_machine_learning_template(df: pd.DataFrame) -> DataCleaningRule:
    """创建机器学习导向的清洗模板

    创建为机器学习模型准备的高质量数据集清洗模板。

    Args:
        df (pd.DataFrame): 要分析的数据框

    Returns:
        DataCleaningRule: 机器学习数据清洗模板
    """
    rule = DataCleaningRule(
        name="机器学习数据清洗模板",
        description="为机器学习模型准备的高质量数据集"
    )
    
    # 严格删除重复行
    rule.set_duplicate_removal(True)
    
    # 使用孤立森林检测异常值
    rule.configure_outlier_detection('isolation_forest', {
        'contamination': 0.1,
        'n_estimators': 100,
        'max_samples': 'auto',
        'remove': True
    })
    
    # 对所有数值列使用中位数填充
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        rule.configure_missing_value(col, 'median')
    
    return rule

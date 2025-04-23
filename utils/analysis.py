import pandas as pd

def describe_data(data):
    """描述性统计"""
    return data.describe()

def calculate_correlation(data):
    """相关性分析"""
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_columns) < 2:
        return None
    return data[numeric_columns].corr()

def group_and_aggregate(data, group_column, agg_column, agg_function):
    """数据分组和聚合"""
    agg_dict = {"平均值": "mean", "总和": "sum", "最大值": "max", "最小值": "min"}
    return data.groupby(group_column)[agg_column].agg(agg_dict[agg_function]).reset_index()
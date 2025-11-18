import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def detect_outliers_iqr(data, column):
    """
    使用四分位距(IQR)方法检测异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    column (str): 列名
    
    Returns:
    pd.Series: 布尔序列，True表示异常值
    """
    Q1 = data[column].quantile(0.25)
    Q3 = data[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return (data[column] < lower_bound) | (data[column] > upper_bound)


def detect_outliers_zscore(data, column, threshold=3):
    """
    使用Z-Score方法检测异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    column (str): 列名
    threshold (float): Z-Score阈值，默认为3
    
    Returns:
    pd.Series: 布尔序列，True表示异常值
    """
    z_scores = np.abs(stats.zscore(data[column].dropna()))
    return data[column].isin(z_scores[z_scores > threshold].index)


def detect_outliers_isolation_forest(data, columns=None, contamination=0.1):
    """
    使用孤立森林(Isolation Forest)算法检测异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    columns (list): 用于检测的列名列表，如果为None则使用所有数值列
    contamination (float): 异常值比例估计，默认为0.1
    
    Returns:
    pd.Series: 布尔序列，True表示异常值
    """
    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    
    # 标准化数据
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data[columns].dropna())
    
    # 使用孤立森林检测异常值
    iso_forest = IsolationForest(contamination=contamination, random_state=42)
    outliers = iso_forest.fit_predict(scaled_data)
    
    # 返回布尔序列，True表示异常值
    outlier_indices = data[columns].dropna().index[outliers == -1]
    return data.index.isin(outlier_indices)


def detect_anomalies(data, method='iqr'):
    """
    检测数据中的异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    method (str): 检测方法 ('iqr', 'zscore', 'isolation_forest')
    
    Returns:
    dict: 每一列的异常值索引
    """
    numeric_columns = data.select_dtypes(include=[np.number]).columns
    anomalies = {}
    
    for column in numeric_columns:
        if method == 'iqr':
            anomalies[column] = data[detect_outliers_iqr(data, column)].index.tolist()
        elif method == 'zscore':
            anomalies[column] = data[detect_outliers_zscore(data, column)].index.tolist()
        elif method == 'isolation_forest':
            anomalies[column] = data[detect_outliers_isolation_forest(data, [column])].index.tolist()
    
    return anomalies


def remove_anomalies(data, anomalies):
    """
    移除数据中的异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    anomalies (dict): 异常值索引字典
    
    Returns:
    pd.DataFrame: 移除异常值后的数据
    """
    # 获取所有异常值的索引
    all_anomaly_indices = set()
    for indices in anomalies.values():
        all_anomaly_indices.update(indices)
    
    # 移除异常值
    cleaned_data = data.drop(index=list(all_anomaly_indices)).reset_index(drop=True)
    return cleaned_data


def get_anomaly_summary(anomalies):
    """
    获取异常值摘要信息
    
    Parameters:
    anomalies (dict): 异常值索引字典
    
    Returns:
    dict: 每列异常值数量和比例的摘要
    """
    summary = {}
    total_rows = len(set().union(*[indices for indices in anomalies.values()])) if anomalies else 0
    
    for column, indices in anomalies.items():
        count = len(indices)
        percentage = (count / total_rows * 100) if total_rows > 0 else 0
        summary[column] = {
            'count': count,
            'percentage': percentage
        }
    
    return summary
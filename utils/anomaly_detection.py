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


def detect_outliers_isolation_forest(data, columns=None, contamination='auto', n_estimators=100, 
                                   max_samples='auto', random_state=42):
    """
    使用孤立森林(Isolation Forest)算法检测异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    columns (list): 用于检测的列名列表，如果为None则使用所有数值列
    contamination (float or 'auto'): 异常值比例估计，'auto'表示自动估计
    n_estimators (int): 孤立树的数量
    max_samples (int, float or 'auto'): 从训练集中抽取样本的数量
    random_state (int): 随机种子
    
    Returns:
    pd.Series: 布尔序列，True表示异常值
    """
    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    
    # 移除包含NaN的行
    clean_data = data[columns].dropna()
    
    if clean_data.empty:
        return pd.Series([False] * len(data), index=data.index)
    
    # 如果max_samples是浮点数，则将其视为比例
    if isinstance(max_samples, float) and 0 < max_samples <= 1.0:
        max_samples = int(max_samples * len(clean_data))
    
    # 标准化数据
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(clean_data)
    
    # 使用孤立森林检测异常值
    iso_forest = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        max_samples=max_samples,
        random_state=random_state,
        n_jobs=-1  # 使用所有处理器核心
    )
    outliers = iso_forest.fit_predict(scaled_data)
    
    # 返回布尔序列，True表示异常值
    outlier_indices = clean_data.index[outliers == -1]
    return data.index.isin(outlier_indices)


def detect_anomalies(data, method='iqr', **kwargs):
    """
    检测数据中的异常值
    
    Parameters:
    data (pd.DataFrame): 数据集
    method (str): 检测方法 ('iqr', 'zscore', 'isolation_forest')
    **kwargs: 方法特定的参数
    
    Returns:
    dict: 每一列的异常值索引
    """
    numeric_columns = data.select_dtypes(include=[np.number]).columns
    anomalies = {}
    
    for column in numeric_columns:
        if method == 'iqr':
            anomalies[column] = data[detect_outliers_iqr(data, column)].index.tolist()
        elif method == 'zscore':
            # 获取阈值参数，默认为3
            threshold = kwargs.get('threshold', 3)
            anomalies[column] = data[detect_outliers_zscore(data, column, threshold)].index.tolist()
        elif method == 'isolation_forest':
            # 对于孤立森林，我们传入所有数值列一起处理以获得更好的效果
            isolation_params = {k: v for k, v in kwargs.items() if k in [
                'contamination', 'n_estimators', 'max_samples', 'random_state']}
            outlier_series = detect_outliers_isolation_forest(data, numeric_columns.tolist(), **isolation_params)
            anomalies[column] = data[outlier_series].index.tolist()
    
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
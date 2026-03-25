def describe_data(data):
    """计算数据的描述性统计信息

    计算数据的基本描述性统计信息，包括均值、标准差、最小值、最大值等。

    Args:
        data (pd.DataFrame): 要分析的数据

    Returns:
        pd.DataFrame: 描述性统计结果
    """
    return data.describe()


def calculate_correlation(data):
    """计算数据的相关性矩阵

    计算数据中数值列之间的相关性矩阵，用于分析变量之间的关联关系。

    Args:
        data (pd.DataFrame): 要分析的数据

    Returns:
        pd.DataFrame or None: 相关性矩阵，如果数值列少于2个则返回None
    """
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_columns) < 2:
        return None
    return data[numeric_columns].corr()


def group_and_aggregate(data, group_column, agg_column, agg_function):
    """对数据进行分组和聚合操作

    根据指定的分组列和聚合函数对数据进行分组和聚合，支持平均值、总和、最大值、最小值四种聚合方式。

    Args:
        data (pd.DataFrame): 要分析的数据
        group_column (str): 分组列名称
        agg_column (str): 聚合列名称
        agg_function (str): 聚合函数，可选值为"平均值"、"总和"、"最大值"、"最小值"

    Returns:
        pd.DataFrame: 分组聚合结果
    """
    agg_dict = {"平均值": "mean", "总和": "sum", "最大值": "max", "最小值": "min"}
    return data.groupby(group_column)[agg_column].agg(agg_dict[agg_function]).reset_index()

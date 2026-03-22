from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import n_colors


def create_scatter_plot(data, x_column, y_column, color_column=None, size_column=None, 
                       hover_data=None, title=None):
    """创建散点图 - 增强版"""
    fig = px.scatter(
        data, 
        x=x_column, 
        y=y_column, 
        color=color_column,
        size=size_column,
        hover_data=hover_data,
        title=title,
        opacity=0.7,
        trendline="lowess" if len(data) > 10 else None  # 添加趋势线
    )
    
    # 增强交互性
    fig.update_traces(
        marker=dict(line=dict(width=1, color='DarkSlateGray')),
        selector=dict(mode='markers')
    )
    
    return fig


def create_line_chart(data, x_column, y_column, color_column=None, line_group=None,
                     markers=False, title=None, show_legend=True):
    """创建折线图 - 增强版"""
    fig = px.line(
        data, 
        x=x_column, 
        y=y_column, 
        color=color_column,
        line_group=line_group,
        markers=markers,
        title=title
    )
    
    # 增强悬停信息
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>值：%{y:.2f}<extra></extra>'
    )
    
    return fig


def create_bar_chart(data, x_column, y_column, color_column=None, orientation='v',
                    title=None, text_auto='.2s'):
    """创建柱状图 - 增强版"""
    fig = px.bar(
        data, 
        x=x_column if orientation == 'v' else y_column,
        y=y_column if orientation == 'v' else x_column,
        color=color_column,
        orientation=orientation,
        title=title,
        text_auto=text_auto
    )
    
    # 优化布局
    fig.update_layout(
        bargap=0.15,
        bargroupgap=0.1
    )
    
    return fig


def create_box_plot(data, column, color_column=None, points="all", title=None):
    """创建箱线图 - 增强版"""
    fig = px.box(
        data, 
        y=column,
        color=color_column,
        points=points,
        title=title,
        notched=True  # 显示缺口
    )
    
    return fig


def create_histogram(data, column, nbins=30, marginal="box", title=None,
                    histnorm='probability density'):
    """创建直方图 - 增强版"""
    fig = px.histogram(
        data, 
        x=column, 
        nbins=nbins, 
        marginal=marginal,
        title=title,
        histnorm=histnorm,  # 概率密度归一化
        opacity=0.75
    )
    
    return fig


def create_pie_chart(data, column, values_column=None, hole=0.4, title=None):
    """创建饼图 - 增强版"""
    if values_column:
        fig = px.pie(
            data, 
            names=column,
            values=values_column,
            hole=hole,  # 创建环形图
            title=title
        )
    else:
        value_counts = data[column].value_counts()
        fig = px.pie(
            values=value_counts.values, 
            names=value_counts.index,
            hole=hole,
            title=title
        )
    
    # 增强标签
    fig.update_traces(textposition='inside', textinfo='percent+label')
    
    return fig


def create_heatmap(data, columns=None, title=None, colorscale='RdBu_r'):
    """创建热力图 - 增强版"""
    if columns is None:
        columns = data.select_dtypes(include=['float64', 'int64']).columns
    
    corr_matrix = data[columns].corr()
    
    fig = px.imshow(
        corr_matrix, 
        text_auto='.2f',
        aspect="auto", 
        color_continuous_scale=colorscale,
        zmin=-1, 
        zmax=1,
        title=title
    )
    
    # 优化文本显示
    fig.update_traces(textfont_size=10)
    
    return fig


def create_dual_axis_chart(data, x_column, y1_column, y2_column, 
                          y1_title='Y1 轴', y2_title='Y2 轴',
                          title=None, y1_color='#1f77b4', y2_color='#ff7f0e'):
    """创建双 Y 轴图表 - 新功能"""
    fig = go.Figure()
    
    # 第一条曲线 (左 Y 轴)
    fig.add_trace(go.Scatter(
        x=data[x_column],
        y=data[y1_column],
        name=y1_title,
        line=dict(color=y1_color, width=2),
        yaxis='y1'
    ))
    
    # 第二条曲线 (右 Y 轴)
    fig.add_trace(go.Scatter(
        x=data[x_column],
        y=data[y2_column],
        name=y2_title,
        line=dict(color=y2_color, width=2, dash='dash'),
        yaxis='y2'
    ))
    
    # 更新布局
    fig.update_layout(
        title=title or f'{y1_title} vs {y2_title}',
        xaxis=dict(
            title=x_column,
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            title=y1_title,
            titlefont=dict(color=y1_color),
            tickfont=dict(color=y1_color),
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis2=dict(
            title=y2_title,
            titlefont=dict(color=y2_color),
            tickfont=dict(color=y2_color),
            anchor='free',
            overlaying='y',
            side='right',
            position=0.95,
            showgrid=False
        ),
        legend=dict(x=0.02, y=0.98),
        hovermode='x unified',
        plot_bgcolor='rgba(240, 240, 244, 0.8)',
        paper_bgcolor='rgba(240, 240, 244, 0.8)'
    )
    
    return fig


def create_multi_subplot_chart(data: pd.DataFrame,
                               data_dict: Dict[str, Dict], 
                               x_column: str,
                               titles: Dict[str, str],
                               subplot_titles: List[str] = None,
                               shared_xaxes: bool = True,
                               vertical_spacing: float = 0.08,
                               title: str = None):
    """创建多子图组合图表 - 新功能"""
    from plotly.subplots import make_subplots
    
    n_charts = len(data_dict)
    rows = (n_charts + 1) // 2  # 最多 2 列
    
    fig = make_subplots(
        rows=rows, 
        cols=2 if n_charts > 1 else 1,
        subplot_titles=subplot_titles or list(titles.values()),
        shared_xaxes=shared_xaxes,
        vertical_spacing=vertical_spacing
    )
    
    # 添加每个图表
    for idx, (key, chart_config) in enumerate(data_dict.items()):
        row = idx // 2 + 1
        col = idx % 2 + 1
        
        y_column = chart_config.get('y_column')
        color = chart_config.get('color', None)
        line_width = chart_config.get('line_width', 2)
        
        # 添加折线
        fig.add_trace(
            go.Scatter(
                x=data[x_column],
                y=data[y_column],
                name=titles.get(key, y_column),
                line=dict(width=line_width),
                mode='lines'
            ),
            row=row, 
            col=col
        )
    
    # 更新整体布局
    fig.update_layout(
        title=title or '多变量对比分析',
        height=400 * rows,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig


def create_smart_chart_recommendation(data: pd.DataFrame, context: str = None) -> Tuple[str, Dict]:
    """智能推荐图表类型 - 新功能"""
    
    # 分析数据特征
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = data.select_dtypes(include=['datetime64']).columns.tolist()
    categorical_cols = data.select_dtypes(include=['object', 'category']).columns.tolist()
    
    recommendations = {
        'trend_analysis': {
            'condition': len(datetime_cols) > 0 and len(numeric_cols) > 0,
            'chart_type': '线图',
            'params': {
                'x_column': datetime_cols[0] if datetime_cols else None,
                'y_column': numeric_cols[0] if numeric_cols else None,
                'title': '时间趋势分析'
            },
            'reason': '检测到时间序列数据，适合用折线图展示趋势'
        },
        'correlation': {
            'condition': len(numeric_cols) >= 2,
            'chart_type': '热力图',
            'params': {
                'columns': numeric_cols[:10],  # 限制最多 10 个变量
                'title': '变量相关性分析'
            },
            'reason': '多个数值变量，适合用热力图分析相关性'
        },
        'distribution': {
            'condition': len(numeric_cols) > 0,
            'chart_type': '直方图',
            'params': {
                'column': numeric_cols[0] if numeric_cols else None,
                'title': '数据分布分析'
            },
            'reason': '分析单变量的分布特征'
        },
        'comparison': {
            'condition': len(categorical_cols) > 0 and len(numeric_cols) > 0,
            'chart_type': '柱状图',
            'params': {
                'x_column': categorical_cols[0] if categorical_cols else None,
                'y_column': numeric_cols[0] if numeric_cols else None,
                'title': '分类对比分析'
            },
            'reason': '类别与数值对比分析'
        }
    }
    
    # 返回第一个满足条件的推荐
    for key, rec in recommendations.items():
        if rec['condition']:
            return rec['chart_type'], rec['params'], rec['reason']
    
    # 默认推荐散点图（确保有足够的列）
    if len(numeric_cols) >= 2:
        default_params = {
            'x_column': numeric_cols[0],
            'y_column': numeric_cols[1],
            'title': '数据关系分析'
        }
        return '散点图', default_params, '默认推荐'
    elif len(numeric_cols) == 1:
        default_params = {
            'column': numeric_cols[0],
            'title': '数据分布分析'
        }
        return '直方图', default_params, '单变量分布'
    else:
        # 没有任何数值列时的兜底方案 - 使用饼图展示分类数据
        if len(categorical_cols) > 0:
            default_params = {
                'column': categorical_cols[0],
                'title': '分类数据分布'
            }
            return '饼图', default_params, '分类数据展示'
        else:
            # 完全没有任何可用列时的最后兜底
            return None, None, None


def visualize_data(data, chart_type, x_column=None, y_column=None, color_column=None, 
                  column=None, **kwargs):
    """
    统一的数据可视化函数 - 增强版
    :param data: 数据集
    :param chart_type: 图表类型
    :param x_column: X 轴列名
    :param y_column: Y 轴列名
    :param color_column: 颜色列名
    :param column: 单列分析时的列名
    :param kwargs: 额外参数
    :return: Plotly 图表对象
    """
    # 定义现代科技感的颜色方案
    color_scheme = n_colors('rgb(0, 122, 255)', 'rgb(10, 132, 255)', 6, colortype='rgb')

    if chart_type == "散点图":
        fig = create_scatter_plot(data, x_column, y_column, color_column, **kwargs)
    elif chart_type == "线图":
        fig = create_line_chart(data, x_column, y_column, color_column, **kwargs)
    elif chart_type == "柱状图":
        fig = create_bar_chart(data, x_column, y_column, color_column, **kwargs)
    elif chart_type == "箱线图":
        fig = create_box_plot(data, column, **kwargs)
    elif chart_type == "直方图":
        fig = create_histogram(data, column, **kwargs)
    elif chart_type == "饼图":
        fig = create_pie_chart(data, column, **kwargs)
    elif chart_type == "热力图":
        fig = create_heatmap(data, data.select_dtypes(include=['float64', 'int64']).columns, **kwargs)
    elif chart_type == "双轴图":
        y1_column = kwargs.get('y1_column', y_column)
        y2_column = kwargs.get('y2_column', column)
        fig = create_dual_axis_chart(data, x_column, y1_column, y2_column, **kwargs)
    elif chart_type == "多子图":
        data_dict = kwargs.get('data_dict', {})
        titles = kwargs.get('titles', {})
        fig = create_multi_subplot_chart(data, data_dict, x_column, titles, **kwargs)
    else:
        raise ValueError(f"不支持的图表类型：{chart_type}")

    # 如果图表还没有设置标题，使用统一的标题格式
    if not fig.layout.title.text:
        fig.update_layout(
            title={
                'text': f"{chart_type} - {y_column if y_column else column if column else ''}",
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=24, color='#1D3557')
            }
        )

    # 统一的样式增强
    fig.update_layout(
        legend_title="图例",
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif",
            size=14
        ),
        hovermode="x unified" if chart_type in ["线图", "双轴图", "多子图"] else "closest",
        plot_bgcolor='rgba(240, 240, 244, 0.8)',
        paper_bgcolor='rgba(240, 240, 244, 0.8)',
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 122, 255, 0.1)') if hasattr(fig, 'xaxis') else None,
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 122, 255, 0.1)') if hasattr(fig, 'yaxis') else None
    )

    return fig

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.colors import n_colors

def create_scatter_plot(data, x_column, y_column, color_column=None):
    """创建散点图"""
    fig = px.scatter(data, x=x_column, y=y_column, color=color_column)
    return fig

def create_line_chart(data, x_column, y_column, color_column=None):
    """创建折线图"""
    fig = px.line(data, x=x_column, y=y_column, color=color_column)
    return fig

def create_bar_chart(data, x_column, y_column, color_column=None):
    """创建柱状图"""
    fig = px.bar(data, x=x_column, y=y_column, color=color_column)
    return fig

def create_box_plot(data, column):
    """创建箱线图"""
    fig = px.box(data, y=column)
    return fig

def create_histogram(data, column):
    """创建直方图"""
    fig = px.histogram(data, x=column, nbins=30, marginal="box")
    return fig

def create_pie_chart(data, column):
    """创建饼图"""
    value_counts = data[column].value_counts()
    fig = px.pie(values=value_counts.values, names=value_counts.index)
    return fig

def create_heatmap(data, columns):
    """创建热力图"""
    corr_matrix = data[columns].corr()
    fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
    return fig

def visualize_data(data, chart_type, x_column=None, y_column=None, color_column=None, column=None):
    """
    统一的数据可视化函数
    :param data: 数据集
    :param chart_type: 图表类型
    :param x_column: X轴列名
    :param y_column: Y轴列名
    :param color_column: 颜色列名
    :param column: 单列分析时的列名
    :return: Plotly图表对象
    """
    # 定义现代科技感的颜色方案
    color_scheme = n_colors('rgb(0, 122, 255)', 'rgb(10, 132, 255)', 6, colortype='rgb')

    if chart_type == "散点图":
        fig = create_scatter_plot(data, x_column, y_column, color_column)
    elif chart_type == "线图":
        fig = create_line_chart(data, x_column, y_column, color_column)
    elif chart_type == "柱状图":
        fig = create_bar_chart(data, x_column, y_column, color_column)
    elif chart_type == "箱线图":
        fig = create_box_plot(data, column)
    elif chart_type == "直方图":
        fig = create_histogram(data, column)
    elif chart_type == "饼图":
        fig = create_pie_chart(data, column)
    elif chart_type == "热力图":
        fig = create_heatmap(data, data.select_dtypes(include=['float64', 'int64']).columns)

    # 更新图表布局
    fig.update_layout(
        title={
            'text': f"{chart_type.capitalize()} - {y_column if chart_type in ['散点图', '线图', '柱状图'] else column if column else ''}",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24, color='#1D3557')
        },
        xaxis_title=x_column if chart_type in ["散点图", "线图", "柱状图"] else column if column else '',
        yaxis_title=y_column if chart_type in ["散点图", "线图", "柱状图"] else "频率" if chart_type != "热力图" else '',
        legend_title="图例",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif", size=14),
        hovermode="closest",
        plot_bgcolor='rgba(240, 240, 244, 0.8)',
        paper_bgcolor='rgba(240, 240, 244, 0.8)',
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 122, 255, 0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 122, 255, 0.1)')
    )

    return fig
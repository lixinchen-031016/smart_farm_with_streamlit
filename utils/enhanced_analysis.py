import pandas as pd
import streamlit as st
import numpy as np
from scipy import stats


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


def explain_descriptive_statistics(data, desc_stats):
    """
    用通俗易懂的语言解释描述性统计数据
    """
    st.subheader("📊 数据洞察解读")
    
    # 解释数据集基本信息
    st.markdown(f"**数据概览**：")
    st.write(f"• 共有 {data.shape[0]} 个数据记录，涵盖 {data.shape[1]} 个不同指标")
    
    # 识别数值型列
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    
    if len(numeric_columns) > 0:
        st.markdown(f"**关键指标详细解读**：")
        
        # 对每个数值列进行详细解释
        for col in numeric_columns:
            if col in desc_stats.columns:
                mean_val = desc_stats.loc['mean', col]
                std_val = desc_stats.loc['std', col]
                min_val = desc_stats.loc['min', col]
                max_val = desc_stats.loc['max', col]
                q25_val = desc_stats.loc['25%', col]
                q50_val = desc_stats.loc['50%', col]  # 中位数
                q75_val = desc_stats.loc['75%', col]
                
                # 简单的中文解释
                st.markdown(f"**{col}**：")
                
                # 均值解释
                if 'temperature' in col.lower() or '温' in col:
                    st.write(f"  • 平均值：{mean_val:.2f}°C，这是整体温度水平")
                    if mean_val < 15:
                        st.write(f"  • 温度偏低，可能需要注意保温措施")
                    elif mean_val > 30:
                        st.write(f"  • 温度偏高，可能需要注意通风降温")
                    else:
                        st.write(f"  • 温度适中，适合大多数作物生长")
                        
                elif 'humidity' in col.lower() or '湿' in col:
                    st.write(f"  • 平均值：{mean_val:.2f}%，这是整体湿度水平")
                    if mean_val < 40:
                        st.write(f"  • 湿度偏低，可能需要增加喷雾或浇水")
                    elif mean_val > 70:
                        st.write(f"  • 湿度偏高，可能需要注意通风除湿")
                    else:
                        st.write(f"  • 湿度适中，有利于作物健康生长")
                        
                elif 'moisture' in col.lower() or '土壤' in col:
                    st.write(f"  • 平均值：{mean_val:.2f}，这是土壤湿润程度")
                    if mean_val < 30:
                        st.write(f"  • 土壤偏干，建议及时灌溉")
                    elif mean_val > 60:
                        st.write(f"  • 土壤偏湿，可能需要适当晾晒")
                    else:
                        st.write(f"  • 土壤湿度适宜，作物生长良好")
                        
                elif 'light' in col.lower() or '光照' in col:
                    st.write(f"  • 平均值：{mean_val:.2f}，反映光照强度")
                    if mean_val < 1000:
                        st.write(f"  • 光照不足，可能需要人工补光")
                    else:
                        st.write(f"  • 光照充足，有利于作物光合作用")
                else:
                    st.write(f"  • 平均值：{mean_val:.2f}")
                
                # 中位数解释
                st.write(f"  • 中位数：{q50_val:.2f}，这是数据的中间值，不受极端值影响")
                
                # 标准差解释
                st.write(f"  • 波动程度（标准差）：{std_val:.2f}，表明数据波动{'大' if std_val > mean_val * 0.3 else '小'}")
                
                # 范围解释
                st.write(f"  • 数值范围：从 {min_val:.2f} 到 {max_val:.2f}")
                
                # 四分位数解释
                st.write(f"  • 数据分布：25%的数据低于{q25_val:.2f}，50%的数据低于{q50_val:.2f}，75%的数据低于{q75_val:.2f}")
                
                # 数据稳定性评估
                if std_val < mean_val * 0.1:
                    st.write(f"  • 数据稳定性：数据变化较小，比较稳定")
                elif std_val < mean_val * 0.2:
                    st.write(f"  • 数据稳定性：数据变化适中，有一定波动")
                else:
                    st.write(f"  • 数据稳定性：数据变化较大，波动明显")
                
                # 偏离度分析
                if abs(mean_val - q50_val) / mean_val > 0.1 if mean_val != 0 else False:
                    st.write(f"  • 数据分布：平均值与中位数差异较大，数据可能存在偏态分布")
                else:
                    st.write(f"  • 数据分布：平均值与中位数接近，数据分布相对对称")
                
                # 极值分析
                range_val = max_val - min_val
                if range_val != 0:
                    iqr = q75_val - q25_val  # 四分位距
                    outlier_ratio = (range_val - iqr) / range_val
                    if outlier_ratio > 0.5:
                        st.write(f"  • 异常值评估：数据中可能存在较多异常值")
                    else:
                        st.write(f"  • 异常值评估：数据分布相对集中，异常值较少")


def explain_correlation_analysis(corr_matrix, data):
    """
    用通俗易懂的语言解释相关性分析结果
    """
    st.subheader("🔗 指标关联解读")
    
    if corr_matrix is None or corr_matrix.empty:
        st.info("由于数据中缺少足够的数值列，无法进行相关性分析。")
        return
    
    # 找出不同强度的相关关系
    very_strong_correlations = []  # |r| >= 0.9
    strong_correlations = []       # 0.7 <= |r| < 0.9
    moderate_correlations = []     # 0.3 <= |r| < 0.7
    weak_correlations = []         # 0.1 <= |r| < 0.3
    
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            col1 = corr_matrix.columns[i]
            col2 = corr_matrix.columns[j]
            
            if abs(corr_val) >= 0.9:
                very_strong_correlations.append((col1, col2, corr_val))
            elif abs(corr_val) >= 0.7:
                strong_correlations.append((col1, col2, corr_val))
            elif abs(corr_val) >= 0.3:
                moderate_correlations.append((col1, col2, corr_val))
            elif abs(corr_val) >= 0.1:
                weak_correlations.append((col1, col2, corr_val))
    
    # 解释极强相关关系
    if very_strong_correlations:
        st.markdown("**极强关联指标（相关性≥0.9）：**")
        for col1, col2, corr in very_strong_correlations:
            direction = "正相关" if corr > 0 else "负相关"
            st.write(f"• **{col1}** 和 **{col2}** 呈现出极强{direction}（相关系数：{corr:.2f}）")
            if 'temperature' in col1.lower() and 'humidity' in col2.lower():
                st.write(f"  - 温度升高时湿度往往{'上升' if corr > 0 else '下降'}，这是常见的气象现象")
            elif 'soil' in col1.lower() and 'humidity' in col2.lower():
                st.write(f"  - 土壤湿度与空气湿度{'正相关' if corr > 0 else '负相关'}，反映了环境的整体湿润程度")
    else:
        st.info("没有发现极强相关（≥0.9）的指标对。")
    
    # 解释强相关关系
    if strong_correlations:
        st.markdown("**强关联指标（相关性0.7-0.9）：**")
        for col1, col2, corr in strong_correlations:
            direction = "正相关" if corr > 0 else "负相关"
            st.write(f"• **{col1}** 和 **{col2}** 呈现出强{direction}（相关系数：{corr:.2f}）")
            if 'temperature' in col1.lower() and 'humidity' in col2.lower():
                st.write(f"  - 温度升高时湿度往往{'上升' if corr > 0 else '下降'}，这是常见的气象现象")
            elif 'soil' in col1.lower() and 'humidity' in col2.lower():
                st.write(f"  - 土壤湿度与空气湿度{'正相关' if corr > 0 else '负相关'}，反映了环境的整体湿润程度")
    else:
        st.info("没有发现强相关（0.7-0.9）的指标对。")
    
    # 解释中等相关关系
    if moderate_correlations:
        st.markdown("**中等关联指标（相关性0.3-0.7）：**")
        for col1, col2, corr in moderate_correlations:
            direction = "正相关" if corr > 0 else "负相关"
            st.write(f"• **{col1}** 和 **{col2}** 存在中等{direction}（相关系数：{corr:.2f}）")
            if 'temperature' in col1.lower() and 'humidity' in col2.lower():
                st.write(f"  - 温度与湿度存在一定的{direction}关系，{'温度升高时湿度也倾向于上升' if corr > 0 else '温度升高时湿度倾向于下降'}")
            elif 'soil' in col1.lower() and 'humidity' in col2.lower():
                st.write(f"  - 土壤湿度与空气湿度存在一定的{direction}关系，表明环境条件对土壤有一定影响")
    else:
        st.info("没有发现中等相关（0.3-0.7）的指标对。")
    
    # 解释弱相关关系
    if weak_correlations:
        st.markdown("**弱关联指标（相关性0.1-0.3）：**")
        for col1, col2, corr in weak_correlations[:5]:  # 限制显示数量
            direction = "正相关" if corr > 0 else "负相关"
            st.write(f"• **{col1}** 和 **{col2}** 存在弱{direction}（相关系数：{corr:.2f}）")
            st.write(f"  - 这种关系较弱，可能没有实际意义")
    
    # 相关性分析总结
    total_pairs = len(very_strong_correlations) + len(strong_correlations) + len(moderate_correlations) + len(weak_correlations)
    st.markdown(f"\n**相关性分析总结**：")
    st.write(f"• 共分析了 {len(corr_matrix.columns)} 个指标之间的关系，涉及 {total_pairs} 对指标组合")
    
    if total_pairs == 0:
        st.write(f"• 数据中的指标间相关性较弱，可能需要考虑其他分析方法")
    else:
        st.write(f"• 指标间存在一定的关联性，可进一步探索因果关系")
        
        # 提供农业相关的建议
        has_temp_humidity_corr = any(('temperature' in pair[0].lower() and 'humidity' in pair[1].lower()) or 
                                   ('humidity' in pair[0].lower() and 'temperature' in pair[1].lower()) 
                                   for pair in very_strong_correlations + strong_correlations)
        
        if has_temp_humidity_corr:
            st.write(f"• 温湿度存在显著相关性，建议在环境调控时综合考虑两者关系")


def explain_data_quality(data):
    """
    解释数据质量
    """
    st.subheader("🔍 数据质量评估")
    
    # 缺失值
    missing_count = data.isnull().sum().sum()
    missing_percentage = (missing_count / (data.shape[0] * data.shape[1])) * 100
    
    # 重复行
    duplicated_count = data.duplicated().sum()
    
    # 数据类型
    dtypes_info = data.dtypes.value_counts()
    
    st.markdown(f"**数据完整性：**")
    if missing_count == 0:
        st.write("✅ 数据完整，没有缺失值")
    else:
        st.write(f"⚠️ 发现 {missing_count} 个缺失值（占总体 {missing_percentage:.2f}%），可能需要数据清洗")
    
    st.markdown(f"**数据唯一性：**")
    if duplicated_count == 0:
        st.write("✅ 数据唯一，没有重复记录")
    else:
        st.write(f"⚠️ 发现 {duplicated_count} 条重复记录，建议去重处理")
    
    st.markdown(f"**数据类型分布：**")
    for dtype, count in dtypes_info.items():
        st.write(f"• {dtype} 类型：{count} 列")


def provide_smart_insights(data):
    """
    提供智能洞察和建议
    """
    st.subheader("💡 智能洞察与建议")
    
    insights = []
    
    # 检查是否有时间戳列
    if 'timestamp' in data.columns:
        time_diff = pd.to_datetime(data['timestamp']).max() - pd.to_datetime(data['timestamp']).min()
        insights.append(f"数据时间跨度：{time_diff.days} 天")
    
    # 检查数值列的统计特征
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_columns:
        if col in data.columns:
            series = data[col].dropna()
            if len(series) > 0:
                # 检查是否可能存在异常值（使用IQR方法）
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                
                if len(outliers) > 0:
                    insights.append(f"在 '{col}' 列中发现 {len(outliers)} 个潜在异常值，可能需要进一步检查")
    
    # 检查数据分布
    if len(numeric_columns) > 0:
        # 选择第一个数值列进行分布检查
        first_numeric_col = numeric_columns[0]
        series = data[first_numeric_col].dropna()
        if len(series) > 8:
            # 使用Shapiro-Wilk检验检查正态性（样本量不能太大）
            if len(series) <= 5000:
                try:
                    stat, p_value = stats.shapiro(series.sample(min(5000, len(series))))
                    if p_value < 0.05:
                        insights.append(f"'{first_numeric_col}' 列的数据分布不符合正态分布")
                except:
                    pass  # 如果数据不适合Shapiro检验则跳过
    
    # 检查数据周期性（针对时间序列数据）
    if 'timestamp' in data.columns:
        timestamp_col = pd.to_datetime(data['timestamp'])
        time_diffs = timestamp_col.sort_values().diff().dropna()
        avg_interval = time_diffs.mean()
        if avg_interval.total_seconds() <= 3600:  # 1小时内
            insights.append(f"数据采集频率较高（平均间隔{avg_interval.total_seconds()/60:.1f}分钟），适合进行高频分析")
        elif avg_interval.total_seconds() <= 86400:  # 1天内
            insights.append(f"数据采集频率适中（平均间隔{avg_interval.total_seconds()/3600:.1f}小时）")
        else:
            insights.append(f"数据采集频率较低（平均间隔{avg_interval.total_seconds()/86400:.1f}天）")
    
    # 检查农业相关指标范围
    for col in numeric_columns:
        if 'temperature' in col.lower() or '温' in col:
            series = data[col].dropna()
            temp_range = (series.min(), series.max())
            if temp_range[0] < 0 or temp_range[1] > 50:
                insights.append(f"温度数据范围异常（{temp_range[0]:.1f}°C ~ {temp_range[1]:.1f}°C），请确认单位和范围")
            elif temp_range[1] - temp_range[0] > 30:
                insights.append(f"温度变化范围较大（{temp_range[1] - temp_range[0]:.1f}°C），可能存在明显日温差")
        
        elif 'humidity' in col.lower() or '湿' in col:
            series = data[col].dropna()
            hum_range = (series.min(), series.max())
            if hum_range[0] < 0 or hum_range[1] > 100:
                insights.append(f"湿度数据超出正常范围（{hum_range[0]:.1f}% ~ {hum_range[1]:.1f}%），请确认数据有效性")
        
        elif 'moisture' in col.lower() or '土壤' in col:
            series = data[col].dropna()
            moist_range = (series.min(), series.max())
            if moist_range[0] < 0 or moist_range[1] > 100:
                insights.append(f"土壤湿度数据超出正常范围（{moist_range[0]:.1f}% ~ {moist_range[1]:.1f}%），请确认数据有效性")
    
    # 显示洞察
    if insights:
        st.markdown("**重要发现：**")
        for insight in insights:
            st.write(f"• {insight}")
    else:
        st.info("数据质量良好，未发现明显问题。")
    
    # 根据数据类型提供建议
    st.markdown("**操作建议：**")
    if 'timestamp' in data.columns:
        st.write("• 由于数据包含时间信息，建议使用时间序列分析方法，如趋势分析、周期性检测等")
    if len(numeric_columns) >= 2:
        st.write("• 数据包含多个数值指标，适合进行相关性分析、聚类分析和预测建模")
    if data.shape[0] > 1000:
        st.write("• 数据量较大，可以进行更复杂的统计分析和建模")
    else:
        st.write("• 数据量适中，适合进行探索性数据分析和基础统计建模")
    
    # 农业领域特定建议
    st.markdown("**农业管理建议：**")
    has_temp = any('temperature' in col.lower() or '温' in col for col in numeric_columns)
    has_hum = any('humidity' in col.lower() or '湿' in col for col in numeric_columns)
    has_moist = any('moisture' in col.lower() or '土壤' in col for col in numeric_columns)
    
    if has_temp and has_hum:
        st.write("• 温湿度数据齐全，可进行环境舒适度分析和病虫害风险评估")
    if has_moist:
        st.write("• 包含土壤湿度数据，建议进行灌溉策略优化分析")
    if 'timestamp' in data.columns and (has_temp or has_hum or has_moist):
        st.write("• 结合时间信息，可进行环境调控策略优化和预测性维护")


def enhanced_data_analysis(data):
    """
    增强版数据分析，提供通俗易懂的解释
    """
    # 数据质量评估
    explain_data_quality(data)
    
    # 描述性统计
    desc_stats = describe_data(data)
    explain_descriptive_statistics(data, desc_stats)
    
    # 相关性分析
    corr_matrix = calculate_correlation(data)
    explain_correlation_analysis(corr_matrix, data)
    
    # 智能洞察
    provide_smart_insights(data)
    
    # 显示原始统计表格（可折叠）
    with st.expander("📄 查看原始统计表格"):
        st.dataframe(desc_stats)
    
    return desc_stats, corr_matrix
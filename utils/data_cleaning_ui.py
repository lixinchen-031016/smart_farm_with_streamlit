import base64
import io

import numpy as np
import streamlit as st
import pandas as  pd
import json
from utils.logger import log_operation
from utils.data_cleaning import DataCleaner


def data_cleaning():
    """
    显示数据清洗页面，提供删除重复行、处理缺失值和删除列的功能
    使用新的数据清洗模块，支持规则模板和效果评估
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("🧹 数据清洗")

    # 导入新的数据清洗模块
    from utils.data_cleaning import (
        DataCleaner,
        DataCleaningRule,
        create_agricultural_standard_template,
        create_machine_learning_template
    )

    # 添加标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ 规则模板", "🔧 基础清洗", "💧 缺失值处理", "📊 异常值检测", "📤 数据导出"])

    # 初始化数据清洗器
    if 'cleaner' not in st.session_state:
        st.session_state['cleaner'] = DataCleaner()

    cleaner = st.session_state['cleaner']

    # 规则模板标签页
    with tab1:
        st.subheader("🎯 清洗规则模板")
        st.markdown("使用预设的清洗规则模板，快速应用标准化的清洗流程")

        if 'data' not in st.session_state:
            st.warning("请先在数据概览页面上传数据")
            return

        data = st.session_state['data']

        # 添加规则管理子标签页
        rule_tab1, rule_tab2 = st.tabs(["📋 应用模板", "💾 规则管理"])

        with rule_tab1:
            template_choice = st.selectbox(
                "选择清洗模板",
                ["农业数据标准清洗流程", "机器学习数据清洗模板", "自定义规则"],
                help="选择预设的清洗规则模板"
            )

            if st.button("应用模板并查看效果", key="apply_template"):
                progress_bar = st.progress(0)

                # 创建规则
                if template_choice == "农业数据标准清洗流程":
                    rule = create_agricultural_standard_template()
                elif template_choice == "机器学习数据清洗模板":
                    rule = create_machine_learning_template(data)
                else:
                    rule = DataCleaningRule("自定义规则")
                    rule.set_duplicate_removal(True)

                progress_bar.progress(30)

                # 应用规则
                cleaned_data, report = cleaner.apply_rule(data, rule)

                progress_bar.progress(100)

                # 显示清洗报告
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("原始数据行数", report['original_shape'][0])
                    st.metric("清洗后数据行数", report['final_shape'][0])
                    st.metric("删除行数", report['original_shape'][0] - report['final_shape'][0])

                with col2:
                    st.metric("清洗前完整率", f"{report['quality_before']['completeness']:.2f}%")
                    st.metric("清洗后完整率", f"{report['quality_after']['completeness']:.2f}%")
                    st.metric("质量提升", f"{report['improvement']['completeness_improvement']:+.2f}%")

                # 保存清洗后的数据
                st.session_state['data'] = cleaned_data
                data = cleaned_data

                # 显示详细报告
                with st.expander("查看详细清洗报告", expanded=True):
                    st.code(cleaner.generate_report(report))

                # 保存当前规则到 session state
                st.session_state['current_rule'] = rule

        with rule_tab2:
            st.subheader("💾 规则管理")
            st.markdown("导出已配置的规则或加载已保存的规则")

            # 导出规则
            st.subheader("导出规则")
            if 'current_rule' in st.session_state:
                rule = st.session_state['current_rule']
                st.info(f"当前规则：**{rule.name}**")

                # 显示规则详情
                with st.expander("查看规则详情"):
                    st.json(rule.to_dict())

                # 导出按钮
                rule_name = st.text_input("规则文件名", value=rule.name.replace(" ", "_"))

                if st.button("导出规则到文件"):
                    try:
                        filepath = f"{rule_name}.json"
                        rule.save(filepath)

                        # 读取文件内容用于下载
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()

                        st.success(f"✅ 规则已保存到：{filepath}")

                        # 提供下载链接
                        st.download_button(
                            label="📥 下载规则文件",
                            data=file_content,
                            file_name=f"{rule_name}.json",
                            mime="application/json"
                        )

                        log_operation(st.session_state['username'], "INFO", "数据清洗 - 导出规则",
                                      f"规则名：{rule.name} 文件：{filepath}")
                    except Exception as e:
                        st.error(f"❌ 导出失败：{str(e)}")
            else:
                st.warning("请先应用一个模板以创建规则")

            st.divider()

            # 加载规则
            st.subheader("加载规则")
            uploaded_rule = st.file_uploader("上传规则文件 (.json)", type=["json"])

            if uploaded_rule is not None:
                try:
                    # 读取 JSON 内容
                    rule_json = json.load(uploaded_rule)
                    loaded_rule = DataCleaningRule.from_dict(rule_json)

                    st.success(f"✅ 成功加载规则：**{loaded_rule.name}**")

                    # 显示规则信息
                    st.info(f"描述：{loaded_rule.description}")
                    st.write(f"创建时间：{loaded_rule.created_at}")

                    # 显示规则配置
                    with st.expander("查看规则配置"):
                        st.json(loaded_rule.rules)

                    # 提供应用按钮
                    if st.button("应用加载的规则"):
                        progress_bar = st.progress(0)
                        cleaned_data, report = cleaner.apply_rule(data, loaded_rule)
                        progress_bar.progress(100)

                        # 显示报告
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("原始数据行数", report['original_shape'][0])
                            st.metric("清洗后数据行数", report['final_shape'][0])
                        with col2:
                            st.metric("清洗前完整率", f"{report['quality_before']['completeness']:.2f}%")
                            st.metric("清洗后完整率", f"{report['quality_after']['completeness']:.2f}%")

                        st.session_state['data'] = cleaned_data
                        data = cleaned_data
                        st.session_state['current_rule'] = loaded_rule

                        with st.expander("查看清洗报告"):
                            st.code(cleaner.generate_report(report))

                    log_operation(st.session_state['username'], "INFO", "数据清洗 - 加载规则",
                                  f"规则名：{loaded_rule.name} 文件：{uploaded_rule.name}")

                except Exception as e:
                    st.error(f"❌ 加载规则失败：{str(e)}")
                    st.error("请确保上传的文件是有效的规则 JSON 文件")

    # 基础清洗标签页
    with tab2:
        st.subheader("删除重复行")
        if st.button("删除重复行", key="drop_duplicates_btn"):
            progress_bar = st.progress(0)
            original_rows = data.shape[0]
            progress_bar.progress(33)
            data = data.drop_duplicates()
            log_operation(st.session_state['username'], "INFO", "数据清洗-删除重复行",
                          f"删除{original_rows - data.shape[0]}行 剩余{data.shape[0]}行")
            st.success(f"删除了 {original_rows - data.shape[0]} 行重复数据")
            progress_bar.progress(100)
            st.session_state['data'] = data

        st.subheader("批量删除列")
        st.markdown("选择要删除的列类型，支持批量操作")

        # 列类型分类
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        datetime_cols = data.select_dtypes(include=['datetime64']).columns.tolist()

        col1, col2, col3 = st.columns(3)
        with col1:
            drop_numeric = st.checkbox(f"删除数值列 ({len(numeric_cols)}个)", value=False)
        with col2:
            drop_categorical = st.checkbox(f"删除分类型列 ({len(categorical_cols)}个)", value=False)
        with col3:
            drop_datetime = st.checkbox(f"删除时间列 ({len(datetime_cols)}个)", value=False)

        if st.button("删除选中的列类型", key="drop_columns_batch"):
            columns_to_drop = []
            if drop_numeric:
                columns_to_drop.extend(numeric_cols)
            if drop_categorical:
                columns_to_drop.extend(categorical_cols)
            if drop_datetime:
                columns_to_drop.extend(datetime_cols)

            # 确保不删除 timestamp 列（如果存在）
            if 'timestamp' in columns_to_drop:
                columns_to_drop.remove('timestamp')

            if columns_to_drop:
                progress_bar = st.progress(0)
                original_cols = len(data.columns)
                data = data.drop(columns=columns_to_drop)
                progress_bar.progress(100)
                log_operation(st.session_state['username'], "INFO", "数据清洗 - 批量删除列",
                              f"删除{len(columns_to_drop)}列 剩余{len(data.columns)}列")
                st.success(f"已删除 {len(columns_to_drop)} 列，剩余 {len(data.columns)} 列")
            else:
                st.warning("未选择任何列进行删除")

        st.subheader("手动选择删除列")
        columns_to_drop_manual = st.multiselect("选择要删除的列", data.columns.tolist())
        if st.button("删除选中的列", key="drop_columns_manual"):
            log_operation(st.session_state['username'], "INFO", "数据清洗 - 删除列",
                          f"删除列：{', '.join(columns_to_drop_manual)}")
            if columns_to_drop_manual:
                progress_bar = st.progress(0)
                data = data.drop(columns=columns_to_drop_manual)
                progress_bar.progress(100)
                st.success(f"已删除列：{', '.join(columns_to_drop_manual)}")
                st.session_state['data'] = data
            else:
                st.warning("未选择任何列进行删除")

        st.success("基础清洗完成")

    # 缺失值处理标签页
    with tab3:
        st.subheader("处理缺失值")
        missing_columns = data.columns[data.isnull().any()].tolist()
        if not missing_columns:
            st.info("当前数据没有缺失值")
        else:
            for column in missing_columns:
                method = st.selectbox(f"选择处理 {column} 缺失值的方法",
                                      ["保持不变", "删除", "填充平均值", "填充中位数", "填充众数"])
                if method != "保持不变":
                    log_operation(st.session_state['username'], "INFO", "数据清洗-处理缺失值",
                                  f"列: {column} 方法: {method}")
                    progress_bar = st.progress(0)
                    if method == "删除":
                        data = data.dropna(subset=[column])
                    else:
                        # 新增: 创建标识列
                        fill_flag_col = f"{column}_filled"

                        # 初始化标识列为False
                        data[fill_flag_col] = False

                        # 获取缺失值的索引
                        missing_index = data[column].isnull()

                        # 确定环境数据类型
                        env_type = "其他"
                        if 'temperature' in column.lower():
                            env_type = "空气温度"
                        elif 'humidity' in column.lower():
                            env_type = "空气湿度"
                        elif 'soil' in column.lower():
                            env_type = "土壤数据"
                        elif 'light' in column.lower():
                            env_type = "光照强度"

                        # 计算填充值
                        if method == "填充平均值":
                            fill_value = data[column].mean()
                        elif method == "填充中位数":
                            fill_value = data[column].median()
                        elif method == "填充众数":
                            fill_value = data[column].mode()[0]

                        # 填充并记录信息
                        data.loc[missing_index, column] = fill_value
                        data.loc[missing_index, fill_flag_col] = data.loc[missing_index].apply(
                            lambda row: f"行号:{row.name} | 类型:{env_type} | 填充值:{fill_value:.2f}",
                            axis=1
                        )
                        log_operation(st.session_state['username'], "INFO", "数据清洗-数据填充",
                                      f"已填充{missing_index.sum()}个缺失值并添加标识列: {fill_flag_col}")
                        st.success(f"已填充{missing_index.sum()}个缺失值并添加标识列: {fill_flag_col}")

                    progress_bar.progress(100)  # 操作完成

            st.session_state['data'] = data
            st.success("缺失值处理完成")

    # 异常值检测标签页
    with tab4:
        st.subheader("异常值检测与清除")

        # 导入异常检测工具
        from utils.anomaly_detection import detect_outliers_iqr, detect_outliers_zscore, \
            detect_outliers_isolation_forest, remove_anomalies, get_anomaly_summary

        # 选择检测方法
        detection_method = st.radio("选择异常值检测方法",
                                    ["四分位距法 (IQR)", "Z-Score法", "孤立森林算法"],
                                    horizontal=True)

        # 为孤立森林算法提供参数调整选项
        isolation_forest_params = {}
        if detection_method == "孤立森林算法":
            st.subheader("孤立森林算法参数设置")
            col1, col2 = st.columns(2)
            with col1:
                # 使用session state保存contamination值
                if 'isolation_forest_contamination' not in st.session_state:
                    st.session_state.isolation_forest_contamination = 0.1

                contamination = st.slider("异常值比例估计", 0.01, 0.5, st.session_state.isolation_forest_contamination,
                                          0.01,
                                          help="预计数据中异常值的比例，较低的值会使算法更敏感",
                                          key="isolation_forest_contamination_slider")
                st.session_state.isolation_forest_contamination = contamination

            with col2:
                # 使用session state保存n_estimators值
                if 'isolation_forest_n_estimators' not in st.session_state:
                    st.session_state.isolation_forest_n_estimators = 100

                n_estimators = st.slider("树的数量", 50, 500, st.session_state.isolation_forest_n_estimators, 10,
                                         help="孤立树的数量，更多的树可以提高准确性但会增加计算时间",
                                         key="isolation_forest_n_estimators_slider")
                st.session_state.isolation_forest_n_estimators = n_estimators

            # 使用session state保存max_samples值
            if 'isolation_forest_max_samples' not in st.session_state:
                st.session_state.isolation_forest_max_samples = 1.0

            max_samples = st.slider("样本数量", 0.1, 1.0, st.session_state.isolation_forest_max_samples, 0.1,
                                    help="每棵树使用的样本比例，较小的值可以提高速度但可能降低准确性",
                                    key="isolation_forest_max_samples_slider")
            st.session_state.isolation_forest_max_samples = max_samples

            isolation_forest_params = {
                'contamination': contamination,
                'n_estimators': n_estimators,
                'max_samples': max_samples if max_samples < 1.0 else 'auto'
            }

        # 选择要检测的列
        numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
        if not numeric_columns:
            st.warning("数据中没有数值型列，无法进行异常值检测")
        else:
            selected_columns = st.multiselect("选择要检测的列", numeric_columns, default=numeric_columns[:3] if len(
                numeric_columns) > 3 else numeric_columns)

            if st.button("检测异常值"):
                if not selected_columns:
                    st.warning("请至少选择一列进行检测")
                else:
                    # 根据选择的方法进行异常值检测
                    anomalies = {}
                    method_key = ""
                    if detection_method == "四分位距法 (IQR)":
                        method_key = "iqr"
                        for col in selected_columns:
                            anomalies[col] = data[detect_outliers_iqr(data, col)].index.tolist()
                    elif detection_method == "Z-Score法":
                        method_key = "zscore"
                        for col in selected_columns:
                            anomalies[col] = data[detect_outliers_zscore(data, col)].index.tolist()
                    elif detection_method == "孤立森林算法":
                        method_key = "isolation_forest"
                        # 使用改进的孤立森林算法
                        outlier_series = detect_outliers_isolation_forest(data, selected_columns,
                                                                          **isolation_forest_params)
                        for col in selected_columns:
                            anomalies[col] = data[outlier_series].index.tolist()

                    # 显示异常值摘要
                    summary = get_anomaly_summary(anomalies)
                    st.write("异常值检测结果:")
                    summary_df = pd.DataFrame(summary).T
                    st.dataframe(summary_df)

                    # 保存异常值索引到session_state
                    st.session_state['anomalies'] = anomalies
                    st.session_state['anomaly_summary'] = summary

                    # 显示详细异常值
                    with st.expander("查看详细异常值"):
                        for col, indices in anomalies.items():
                            if indices:
                                st.write(f"**{col}** 列的异常值:")
                                st.dataframe(data.loc[indices, [col]])

            # 提供清除异常值的选项
            if 'anomalies' in st.session_state:
                if st.button("清除检测到的异常值"):
                    data = remove_anomalies(data, st.session_state['anomalies'])
                    st.session_state['data'] = data
                    st.success("已清除异常值")
                    # 清除异常值信息
                    del st.session_state['anomalies']
                    del st.session_state['anomaly_summary']

    # 数据导出标签页
    with tab5:
        st.subheader("导出清洗后的数据")
        export_format = st.selectbox("选择导出格式", ["CSV", "Excel", "JSON"])
        if st.button("导出数据"):
            log_operation(st.session_state['username'], "INFO", "数据清洗-数据导出",
                          f"导出格式: {export_format} 文件名: cleaned_data.{export_format.lower()}")
            progress_bar = st.progress(0)
            if export_format == "CSV":
                csv = data.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="cleaned_data.csv">下载 CSV 文件</a>'
            elif export_format == "Excel":
                excel = io.BytesIO()
                data.to_excel(excel, index=False)
                excel.seek(0)
                b64 = base64.b64encode(excel.read()).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="cleaned_data.xlsx">下载 Excel 文件</a>'
            elif export_format == "JSON":
                json_str = data.to_json(orient='records')
                b64 = base64.b64encode(json_str.encode()).decode()
                href = f'<a href="data:application/json;base64,{b64}" download="cleaned_data.json">下载 JSON 文件</a>'
            progress_bar.progress(100)  # 操作完成
            st.markdown(href, unsafe_allow_html=True)


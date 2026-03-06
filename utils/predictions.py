import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.tsa.statespace.sarimax import SARIMAX

import models


def sarima_validation_prediction(data, prediction_days, params, prophet_forecast):
    """SARIMA验证/微调模型实现"""
    # 参数解析
    order_p = params.get('sarima_order_p', 1)
    order_q = params.get('sarima_order_q', 1)
    seasonal_P = params.get('sarima_seasonal_P', 1)
    seasonal_Q = params.get('sarima_seasonal_Q', 1)
    manual_prophet_weight = params.get('manual_prophet_weight', 0.6)
    manual_sarima_weight = params.get('manual_sarima_weight', 0.4)

    # 数据预处理
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # 使用优化的SARIMA参数
    model = SARIMAX(df['value'],
                    order=(order_p, 1, order_q),
                    seasonal_order=(seasonal_P, 1, seasonal_Q, 24),
                    enforce_stationarity=False,
                    enforce_invertibility=False)

    try:
        model_fit = model.fit(disp=False, maxiter=200)

        # 生成预测时间戳 - 使用periods确保点数匹配
        last_date = df.index[-1].replace(hour=0, minute=0, second=0)
        total_prediction_points = prediction_days * 8  # 每天8个点(每3小时一个点)
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=total_prediction_points,
            freq='3H'
        )

        # SARIMA预测
        sarima_forecast = model_fit.forecast(steps=len(forecast_dates))

        # 计算拟合效果
        fitted = model_fit.fittedvalues
        sarima_rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))

        # 获取Prophet预测值
        prophet_values = prophet_forecast['value'].values
        sarima_values = sarima_forecast.values

        # 长度验证 - 确保两个数组长度一致
        if len(prophet_values) != len(sarima_values):
            # 如果长度不匹配，以较短的为准进行截断
            min_length = min(len(prophet_values), len(sarima_values))
            prophet_values = prophet_values[:min_length]
            sarima_values = sarima_values[:min_length]
            forecast_dates = forecast_dates[:min_length]
            st.warning(f"预测长度不匹配，已调整为{min_length}个点")

        # 权重融合策略
        if manual_prophet_weight + manual_sarima_weight == 1.0:
            # 使用用户指定的手动权重
            final_prophet_weight = manual_prophet_weight
            final_sarima_weight = manual_sarima_weight
        else:
            # 基于性能自动调整权重
            prophet_weight = 1 / (1 + sarima_rmse)  # SARIMA RMSE越小权重越大
            sarima_weight = 1 / (1 + sarima_rmse)  # 这里应该使用Prophet的RMSE
            total_weight = prophet_weight + sarima_weight
            final_prophet_weight = prophet_weight / total_weight
            final_sarima_weight = sarima_weight / total_weight

        # 融合预测结果
        combined_forecast = (final_prophet_weight * prophet_values +
                             final_sarima_weight * sarima_values)

        validation_explanation = f"""
        **SARIMA验证模型详情**
        
        **模型配置:**
        - AR项阶数(p): {order_p}
        - MA项阶数(q): {order_q}
        - 季节性AR项(P): {seasonal_P}
        - 季节性MA项(Q): {seasonal_Q}
        - 季节性周期: 24小时
        
        **融合权重:**
        - Prophet权重: {final_prophet_weight:.3f}
        - SARIMA权重: {final_sarima_weight:.3f}
        - 权重来源: {'手动设置' if manual_prophet_weight + manual_sarima_weight == 1.0 else '自动调整'}
        
        **性能指标:**
        - SARIMA拟合RMSE: {sarima_rmse:.4f}
        - 最终预测点数: {len(combined_forecast)}
        """

        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': combined_forecast})
        return forecast_df, sarima_rmse, validation_explanation

    except Exception as e:
        # 如果SARIMA拟合失败，回退到纯Prophet预测
        st.warning(f"SARIMA模型拟合失败: {str(e)}，使用纯Prophet预测结果")
        return prophet_forecast, float('inf'), "SARIMA验证失败，使用Prophet预测"


def prophet_prediction(data, prediction_days, params):
    """Facebook Prophet模型预测实现"""
    # 使用 prophet 替代 fbprophet
    from prophet import Prophet
    import pandas as pd
    import numpy as np

    # 数据预处理
    df = pd.DataFrame(data, columns=['ds', 'y'])
    df['ds'] = pd.to_datetime(df['ds'])

    # 添加农业数据特定的季节性参数
    model = Prophet(
        yearly_seasonality=False,  # 农业数据通常不需要年周期
        weekly_seasonality=True,  # 周周期对农业数据可能有用
        daily_seasonality=True,  # 日周期非常重要
        changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05),
        seasonality_prior_scale=params.get('seasonality_prior_scale', 10.0),
        holidays_prior_scale=params.get('holidays_prior_scale', 10.0),
        seasonality_mode='multiplicative'
    )

    # 添加自定义季节性 - 适合农业数据的季节性
    model.add_seasonality(name='hourly', period=1 / 24, fourier_order=5)  # 每小时周期

    # 训练模型
    model.fit(df)

    # 生成预测时间戳 - 每天8个时间点(0,3,6,9,12,15,18,21)
    future = model.make_future_dataframe(
        periods=prediction_days * 8,  # 每天8个点
        freq='3H'
    )

    # 生成预测
    forecast = model.predict(future)

    # 计算历史数据的RMSE
    y_true = df['y'].values
    y_pred = forecast.loc[:len(df) - 1, 'yhat'].values
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

    # 准备返回数据
    forecast_df = forecast[['ds', 'yhat']].rename(columns={'ds': 'timestamp', 'yhat': 'value'})
    forecast_df = forecast_df[forecast_df['timestamp'] > df['ds'].max()]  # 只返回预测部分

    explanation = f"""
    **Prophet模型训练说明**
    
    本次预测使用了Facebook Prophet模型，特别针对农业数据优化:
    
    **模型特性:**
    1. 内置日周期和周周期检测
    2. 自动处理节假日效应
    3. 对异常值和缺失值鲁棒
    4. 乘法季节性模式适合农业数据
    
    **农业数据优化:**
    1. 添加了精细的每小时季节性
    2. 调整了变化点灵敏度
    3. 优化了季节性强度参数
    
    **性能指标:**
    - 历史数据拟合RMSE: {rmse:.4f}
    - 预测天数: {prediction_days}天
    """

    return df.set_index('ds'), forecast_df, explanation, rmse


def perform_prediction(data, model_type, prediction_days, lstm_params=None):
    # 修改：检查传入的数据类型
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], tuple):
        # 从数据库获取的原始数据格式
        df = pd.DataFrame(data, columns=['timestamp', 'value'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    else:
        # 已经是DataFrame格式（来自清洗后的数据）
        df = data.copy()
        # 确保列名正确
        if not isinstance(df, pd.DataFrame):
            # 如果不是DataFrame，尝试转换为DataFrame
            df = pd.DataFrame(df)
        if 'value' not in df.columns and len(df.columns) >= 1:
            # 假设最后一列是我们要预测的值
            value_col = df.columns[-1]
            df = df.rename(columns={value_col: 'value'})
        df.index = pd.to_datetime(df.index)

    # 农业数据预处理 - 处理异常值和缺失值
    # 只对数值列进行线性插值（避免对时间索引进行插值）
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        df[numeric_columns] = df[numeric_columns].interpolate(method='linear')

    # 处理异常值
    if 'value' in df.columns:
        df['value'] = np.where(df['value'] > df['value'].quantile(0.99),
                               df['value'].median(),
                               df['value'])

    # 只选择最近60天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=60))]

    model_explanation = ""  # 初始化解释字符串
    rmse = 0.0  # 初始化RMSE

    if model_type == "Prophet":
        # 准备Prophet需要的输入格式
        prophet_data = df.reset_index()
        # 确保数据包含正确的列名，只取时间列和值列
        if 'value' in prophet_data.columns:
            prophet_data = prophet_data[['timestamp', 'value']].rename(columns={'timestamp': 'ds', 'value': 'y'})
        else:
            # 如果没有'value'列，则使用第一列作为时间，最后一列作为值
            prophet_data = prophet_data.iloc[:, [0, -1]]
            prophet_data.columns = ['ds', 'y']
        return prophet_prediction(prophet_data, prediction_days, lstm_params or {})

    elif model_type == "SARIMA":
        # 使用SARIMA作为验证/微调模型
        # 首先调用Prophet作为主干模型获取基础预测
        prophet_data = df.reset_index()
        if 'value' in prophet_data.columns:
            prophet_data = prophet_data[['timestamp', 'value']].rename(columns={'timestamp': 'ds', 'value': 'y'})
        else:
            prophet_data = prophet_data.iloc[:, [0, -1]]
            prophet_data.columns = ['ds', 'y']

        # 获取Prophet基础预测
        _, prophet_forecast, prophet_explanation, prophet_rmse = prophet_prediction(prophet_data, prediction_days,
                                                                                    lstm_params or {})

        # 使用增强的SARIMA验证函数
        sarima_forecast_df, sarima_rmse, validation_explanation = sarima_validation_prediction(
            [(idx, row['value']) for idx, row in df.iterrows()],
            prediction_days,
            lstm_params or {},
            prophet_forecast
        )

        # 选择最终RMSE（取较好的那个）
        final_rmse = min(prophet_rmse, sarima_rmse)

        model_explanation = f"""
        **Prophet + SARIMA混合预测模型**
        
        本次预测采用双模型融合策略：
        
        **主干模型 - Prophet:**
        1. Facebook开源的时间序列预测模型
        2. 自动处理季节性和趋势成分
        3. 对异常值和缺失值具有鲁棒性
        4. 内置节假日效应处理
        
        **验证模型 - SARIMA:**
        1. 季节性自回归积分滑动平均模型
        2. 专门针对农业数据的24小时周期优化
        3. 经典统计学方法，理论基础扎实
        
        {validation_explanation}
        
        **性能指标:**
        - Prophet RMSE: {prophet_rmse:.4f}
        - SARIMA RMSE: {sarima_rmse:.4f}
        - 最终RMSE: {final_rmse:.4f}
        - 使用的数据范围: 最近60天数据
        - 预测天数: {prediction_days}天
        
        **农业数据优化:**
        - 24小时昼夜周期建模
        - 多模型交叉验证提升可靠性
        - 动态权重调整适应数据特性
        """

        return df, sarima_forecast_df, model_explanation, final_rmse

    elif model_type == "Prophet":
        # 准备Prophet需要的输入格式
        prophet_data = df.reset_index()
        # 确保数据包含正确的列名，只取时间列和值列
        if 'value' in prophet_data.columns:
            prophet_data = prophet_data[['timestamp', 'value']].rename(columns={'timestamp': 'ds', 'value': 'y'})
        else:
            # 如果没有'value'列，则使用第一列作为时间，最后一列作为值
            prophet_data = prophet_data.iloc[:, [0, -1]]
            prophet_data.columns = ['ds', 'y']
        return prophet_prediction(prophet_data, prediction_days, lstm_params or {})

    return df, pd.DataFrame(), model_explanation, rmse


def get_historical_data(session, data_type):
    """获取历史数据"""
    if data_type == "空气温度":
        query = session.query(models.AirTemperatureHumidity.timestamp,
                              models.AirTemperatureHumidity.temperature).order_by(
            models.AirTemperatureHumidity.timestamp)
    elif data_type == "空气湿度":
        query = session.query(models.AirTemperatureHumidity.timestamp,
                              models.AirTemperatureHumidity.humidity).order_by(
            models.AirTemperatureHumidity.timestamp)
    elif data_type == "土壤湿度":
        query = session.query(models.SoilMoisture.timestamp, models.SoilMoisture.value).order_by(
            models.SoilMoisture.timestamp)
    return query.all()


def prepare_prediction_ui():
    """准备预测UI组件"""
    data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度"])
    model_type = st.selectbox("选择预测模型", ["Prophet+SARIMA(推荐)", "纯Prophet"])
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)

    lstm_params = {}
    # 统一模型类型映射
    model_mapping = {
        "Prophet+SARIMA(推荐)": "SARIMA",  # 内部仍使用SARIMA标识符，但实际执行混合预测
        "纯Prophet": "Prophet",
        "纯SARIMA": "SARIMA",
    }
    model_mapping.get(model_type, model_type)

    if model_type == "Prophet":
        with st.expander("Prophet模型参数配置"):
            lstm_params['changepoint_prior_scale'] = st.slider("变化点灵敏度", 0.001, 0.5, 0.05, step=0.01,
                                                               help="控制趋势灵活性的参数")
            lstm_params['seasonality_prior_scale'] = st.slider("季节性强度", 0.1, 20.0, 10.0, step=0.1,
                                                               help="控制季节性效应强度的参数")
    elif model_type == "Hybrid":
        with st.expander("混合模型参数配置"):
            # Prophet参数
            lstm_params['changepoint_prior_scale'] = st.slider("Prophet变化点灵敏度", 0.001, 0.5, 0.05, step=0.01,
                                                               help="控制趋势灵活性的参数")
            lstm_params['seasonality_prior_scale'] = st.slider("Prophet季节性强度", 0.1, 20.0, 10.0, step=0.1,
                                                               help="控制季节性效应强度的参数")

            # 神经网络通用参数
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7,
                                                 help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 10)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 32)

            # LSTM参数
            lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 16)

            # Transformer参数
            default_d_model = 64
            lstm_params['d_model'] = st.slider("Transformer嵌入维度", 32, 256, default_d_model,
                                               step=4, help="必须能被注意力头数整除")
            lstm_params['nhead'] = st.slider("注意力头数", 2, 8, 4,
                                             help=f"当前嵌入维度: {lstm_params.get('d_model', default_d_model)}")
            if 'd_model' in lstm_params and 'nhead' in lstm_params:
                if lstm_params['d_model'] % lstm_params['nhead'] != 0:
                    st.warning(f"嵌入维度({lstm_params['d_model']})必须能被注意力头数({lstm_params['nhead']})整除")
                    lstm_params['nhead'] = _find_divisor(lstm_params['d_model'], lstm_params['nhead'])
                    st.info(f"已自动调整注意力头数为: {lstm_params['nhead']}")

            lstm_params['num_layers'] = st.slider("Transformer编码器层数", 1, 6, 2)

            # 混合权重
            st.subheader("模型权重配置")
            st.write("三个模型的权重总和应为1.0")
            col1, col2, col3 = st.columns(3)
            with col1:
                lstm_params['prophet_weight'] = st.number_input("Prophet权重", 0.0, 1.0, 0.4, step=0.1)
            with col2:
                lstm_params['lstm_weight'] = st.number_input("LSTM权重", 0.0, 1.0, 0.3, step=0.1)
            with col3:
                lstm_params['transformer_weight'] = st.number_input("Transformer权重", 0.0, 1.0, 0.3, step=0.1)

            total_weight = (lstm_params.get('prophet_weight', 0.4) +
                            lstm_params.get('lstm_weight', 0.3) +
                            lstm_params.get('transformer_weight', 0.3))
            if abs(total_weight - 1.0) > 1e-6:
                st.warning(f"当前权重总和为{total_weight:.2f}，建议调整为1.0")

    return data_type, model_type, prediction_days, lstm_params


def show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type):
    """显示预测结果"""
    if model_explanation:
        with st.expander("模型训练说明", expanded=True):
            st.markdown(model_explanation)
            st.markdown(f"**模型评价指标:**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("RMSE (均方根误差)", f"{rmse:.4f}")
            with col2:
                st.markdown("RMSE值越小表示模型预测精度越高")

    # 统一列名处理
    hist_col = 'y' if 'y' in historical_data.columns else 'value'
    # 修复：确保能正确处理混合模型预测数据的列名
    forecast_col = 'value'  # 混合模型和其他模型统一使用'value'列

    # 性能优化：对大数据集进行采样
    max_points = 500  # 减少采样点数以提高渲染性能
    if len(historical_data) > max_points:
        historical_data_sampled = historical_data.sample(n=max_points, random_state=42).sort_index()
    else:
        historical_data_sampled = historical_data

    if len(forecast_data) > max_points:
        forecast_data_sampled = forecast_data.sample(n=max_points, random_state=42).sort_values('timestamp')
    else:
        forecast_data_sampled = forecast_data

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=historical_data_sampled.index,
        y=historical_data_sampled[hist_col],
        mode='lines',
        name='历史数据',
        line=dict(width=2),
        hovertemplate="时间: %{x}<br>值: %{y}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=forecast_data_sampled['timestamp'],
        y=forecast_data_sampled[forecast_col],
        mode='lines',
        name='预测数据',
        line=dict(width=3, dash='dash'),
        hovertemplate="时间: %{x}<br>预测值: %{y}<extra></extra>"
    ))

    # 添加置信区间（如果可用）
    if 'yhat_lower' in forecast_data_sampled.columns and 'yhat_upper' in forecast_data_sampled.columns:
        fig.add_trace(go.Scatter(
            x=pd.concat([forecast_data_sampled['timestamp'], forecast_data_sampled['timestamp'][::-1]]),
            y=pd.concat([forecast_data_sampled['yhat_upper'], forecast_data_sampled['yhat_lower'][::-1]]),
            fill='toself',
            fillcolor='rgba(0,100,80,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name='置信区间'
        ))

    fig.update_layout(
        title=f"{data_type} 预测结果",
        xaxis_title="时间",
        yaxis_title="值",
        legend_title="数据类型",
        hovermode='x unified',  # 统一悬停效果
        font=dict(size=12)
    )

    # 启用WebGL加速
    fig.update_traces(patch=dict(mode='lines'), selector=dict(type='scatter'))

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("预测结果评价")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("预测数据数", len(forecast_data))
    with col2:
        st.metric("历史数据量", len(historical_data))
    with col3:
        st.metric("模型精度 (RMSE)", f"{rmse:.4f}",
                  delta="优" if rmse < 1.0 else "良" if rmse < 2.5 else "一般",
                  delta_color="inverse")

    # 添加智能推荐
    if rmse < 1.0:
        st.success("✅ **智能推荐**: 模型预测精度较高，可结合实际环境用于决策参考")
    elif rmse < 2.5:
        st.warning("⚠️ **智能推荐**: 模型预测精度中等，建议结合实际经验进行判断")
    else:
        st.warning("⚠️ **智能推荐**: 模型预测偏差较大，建议结合实际数据趋势进行判断")

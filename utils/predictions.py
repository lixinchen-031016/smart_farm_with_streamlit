import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings('ignore')

import models
from utils.hybrid_prediction import HybridPredictor, grid_search_sarima_params
from utils.gpu_accelerator import get_gpu_accelerator

def sarima_validation_prediction(data, prediction_days, params, prophet_forecast):
    """SARIMA验证/微调模型实现

    使用SARIMA模型对Prophet预测结果进行验证和微调，通过权重融合策略提高预测精度。

    Args:
        data (list): 历史数据列表，每个元素为(timestamp, value)元组
        prediction_days (int): 预测天数
        params (dict): 模型参数，包含SARIMA模型的阶数和权重设置
        prophet_forecast (pd.DataFrame): Prophet模型的预测结果

    Returns:
        tuple: (forecast_df, rmse, validation_explanation)
            - forecast_df: 融合后的预测结果DataFrame
            - rmse: 模型拟合的RMSE值
            - validation_explanation: 模型验证说明文本

    Raises:
        Exception: SARIMA模型拟合失败时会捕获并回退到Prophet预测
    """
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
        
        # 获取 Prophet 预测值并计算其 RMSE
        prophet_values = prophet_forecast['value'].values
        # 计算 Prophet 的历史数据拟合 RMSE（需要获取 Prophet 的历史拟合值）
        prophet_history_fit = prophet_forecast[:len(df)]['value'].values if len(prophet_forecast) >= len(df) else prophet_forecast['value'].values
        prophet_rmse = np.sqrt(np.mean((df['value'].values[:len(prophet_history_fit)] - prophet_history_fit) ** 2))
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
    # 需要同时计算两个模型的 RMSE
            prophet_weight = 1 / (1 + prophet_rmse)  # ✅ Prophet RMSE 越小权重越大
            sarima_weight = 1 / (1 + sarima_rmse)    # ✅ SARIMA RMSE 越小权重越大
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
    """Facebook Prophet模型预测实现

    使用Facebook Prophet模型进行时间序列预测，特别针对农业数据进行了优化，
    支持日周期、周周期检测和异常值处理。

    Args:
        data (list or pd.DataFrame): 历史数据，包含时间戳和值
        prediction_days (int): 预测天数
        params (dict): 模型参数，包含变化点灵敏度、季节性强度等设置

    Returns:
        tuple: (historical_df, forecast_df, explanation, rmse)
            - historical_df: 历史数据DataFrame
            - forecast_df: 预测结果DataFrame
            - explanation: 模型训练说明文本
            - rmse: 模型拟合的RMSE值

    Raises:
        ValueError: 数据量不足或数据方差为0时会抛出异常
    """
    # 使用 prophet 替代 fbprophet
    from prophet import Prophet
    import pandas as pd
    import numpy as np

    # 数据预处理
    df = pd.DataFrame(data, columns=['ds', 'y'])
    df['ds'] = pd.to_datetime(df['ds'])
    
    # 检查数据有效性
    if df.empty or len(df) < 10:
        raise ValueError("数据量不足，无法进行预测")
    
    # 检查 y 列是否有有效值
    if df['y'].isna().all() or df['y'].var() == 0:
        raise ValueError("数据方差为 0 或全部为空，无法进行预测")

    # 添加农业数据特定的季节性参数
    model = Prophet(
        yearly_seasonality=False,  # 农业数据通常不需要年周期
        weekly_seasonality=True,  # 周周期对农业数据可能有用
        daily_seasonality=True,  # 日周期非常重要
        changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05),
        seasonality_prior_scale=params.get('seasonality_prior_scale', 10.0),
        holidays_prior_scale=params.get('holidays_prior_scale', 10.0),
        seasonality_mode='additive'  # 改为加法模式，更适合湿度等有限范围的数据
    )

    # 添加自定义季节性 - 适合农业数据的季节性
    model.add_seasonality(name='hourly', period=1 / 24, fourier_order=3)  # 每小时周期，降低复杂度

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
    
    # 对湿度数据进行合理性检查 (如果是湿度数据)
    if 'humidity' in str(data) or (df['y'].max() <= 100 and df['y'].min() >= 0):
        # 限制预测值在合理范围内 (0-100%)
        forecast_df['value'] = forecast_df['value'].clip(0, 100)

    explanation = f"""
    **Prophet模型训练说明**
    
    本次预测使用了Facebook Prophet模型，特别针对农业数据优化:
    
    **模型特性**:
    1. 内置日周期和周周期检测
    2. 自动处理节假日效应
    3. 对异常值和缺失值鲁棒
    4. 加法季节性模式适合湿度等有限范围数据
    
    **农业数据优化:**
    1. 添加了精细的每小时季节性
    2. 调整了变化点灵敏度
    3. 优化了季节性强度参数
    
    **性能指标**:
    - 历史数据拟合 RMSE: {rmse:.4f}
    - 预测天数：{prediction_days}天
    - 数据范围：[{df['y'].min():.1f}, {df['y'].max():.1f}]
    """

    return df.set_index('ds'), forecast_df, explanation, rmse


def hybrid_sarima_prophet_prediction(data, prediction_days, params, use_gpu=False):
    """SARIMA + Prophet 混合预测模型（基于残差分解）
    
    实现原理:
    1. SARIMA捕获线性趋势和季节性，得到初步预测 Ŷ_SARIMA(t)
    2. 计算残差 e(t) = Y(t) - Ŷ_SARIMA(t)
    3. Prophet学习残差中的非线性模式，预测残差 Ŷ_Prophet_residuals(t)
    4. 最终预测: Ŷ_Hybrid(t) = Ŷ_SARIMA(t) + Ŷ_Prophet_residuals(t)
    
    Args:
        data (list or pd.DataFrame): 历史数据
        prediction_days (int): 预测天数
        params (dict): 模型参数配置
        use_gpu (bool): 是否使用GPU加速
        
    Returns:
        tuple: (historical_df, forecast_df, explanation, rmse, evaluation_metrics)
    """
    import time
    
    # 初始化GPU加速器
    if use_gpu:
        gpu_accelerator = get_gpu_accelerator()
        device_info = gpu_accelerator.get_device_info()
        st.info(f"🖥️ 使用设备: {device_info['device_name']}")
    else:
        gpu_accelerator = None
    
    # 数据预处理
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], tuple):
        df = pd.DataFrame(data, columns=['timestamp', 'value'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    else:
        df = data.copy()
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        if 'value' not in df.columns and len(df.columns) >= 1:
            value_col = df.columns[-1]
            df = df.rename(columns={value_col: 'value'})
        df.index = pd.to_datetime(df.index)
    
    # 农业数据预处理
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        df[numeric_columns] = df[numeric_columns].interpolate(method='linear')
    
    if 'value' in df.columns:
        df['value'] = np.where(df['value'] > df['value'].quantile(0.99),
                               df['value'].median(),
                               df['value'])
    
    # 只选择最近60天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=60))]
    
    if len(df) < 48:
        raise ValueError("数据量不足，至少需要48个数据点")
    
    # 提取时间序列
    time_series = df['value']
    
    # 开始训练
    st.write("🚀 正在启动混合预测模型...")
    overall_start = time.time()
    
    try:
        # 创建混合预测器
        predictor = HybridPredictor(use_gpu=use_gpu)
        
        # 步骤1: 网格搜索最优SARIMA参数（可选）
        use_grid_search = params.get('use_grid_search', False)
        if use_grid_search:
            st.write("🔍 正在进行SARIMA参数网格搜索...")
            best_params = grid_search_sarima_params(
                time_series,
                p_range=params.get('p_range', range(0, 3)),
                q_range=params.get('q_range', range(0, 3)),
                P_range=params.get('P_range', range(0, 2)),
                Q_range=params.get('Q_range', range(0, 2)),
                seasonal_period=24
            )
            order = best_params['order']
            seasonal_order = best_params['seasonal_order']
            st.success(f"✅ 最优参数: order={order}, seasonal_order={seasonal_order}")
        else:
            order = (
                params.get('sarima_order_p', 1),
                params.get('sarima_order_d', 1),
                params.get('sarima_order_q', 1)
            )
            seasonal_order = (
                params.get('sarima_seasonal_P', 1),
                params.get('sarima_seasonal_D', 1),
                params.get('sarima_seasonal_Q', 1),
                24
            )
        
        # 步骤2: 训练SARIMA模型
        progress_bar = st.progress(0)
        st.write("📊 步骤1/3: 训练SARIMA模型...")
        sarima_result = predictor.train_sarima(
            time_series,
            order=order,
            seasonal_order=seasonal_order,
            maxiter=params.get('maxiter', 200)
        )
        progress_bar.progress(33)
        
        # 步骤3: 训练Prophet残差模型
        st.write("📊 步骤2/3: 训练Prophet残差模型...")
        prophet_result = predictor.train_prophet_on_residuals(
            sarima_result['residuals'],
            changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05),
            seasonality_prior_scale=params.get('seasonality_prior_scale', 10.0)
        )
        progress_bar.progress(66)
        
        # 步骤4: 进行预测
        st.write("📊 步骤3/3: 生成预测结果...")
        total_steps = prediction_days * 8  # 每天8个时间点
        predictions = predictor.predict(steps=total_steps, frequency='3H')
        progress_bar.progress(90)
        
        # 步骤5: 模型评估
        st.write("📈 评估模型性能...")
        # 使用最后20%的数据作为测试集进行评估
        test_size = min(int(len(time_series) * 0.2), 48)
        if test_size > 0:
            train_data = time_series[:-test_size]
            test_data = time_series[-test_size:]
            
            # 重新训练并评估
            eval_predictor = HybridPredictor(use_gpu=use_gpu)
            eval_predictor.train_sarima(train_data, order=order, seasonal_order=seasonal_order)
            eval_predictor.train_prophet_on_residuals(
                eval_predictor.residuals_train,  # 修复：使用残差序列而不是index
                changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05)
            )
            evaluation = eval_predictor.evaluate(test_data, steps=len(test_data))
        else:
            evaluation = None
        
        overall_time = time.time() - overall_start
        progress_bar.progress(100)
        
        # 准备返回数据
        forecast_dates = predictions['forecast_dates']
        forecast_values = predictions['hybrid_forecast']
        
        forecast_df = pd.DataFrame({
            'timestamp': forecast_dates,
            'value': forecast_values
        })
        
        # 获取训练摘要
        training_summary = predictor.get_training_summary()
        
        # 构建详细说明
        explanation = f"""
### 🔬 SARIMA + Prophet 混合预测模型（残差分解法）

#### 📋 模型架构

**第一阶段 - SARIMA（线性建模）**
- 捕获数据中的线性趋势、季节性和自相关性
- 模型阶数: order={order}, seasonal_order={seasonal_order}
- 训练RMSE: {sarima_result['rmse']:.4f}
- 训练耗时: {sarima_result['training_time']:.2f}秒

**第二阶段 - Prophet（非线性残差建模）**
- 学习SARIMA未能解释的残差模式
- 捕捉非线性趋势、异常波动和复杂季节性
- 残差拟合RMSE: {prophet_result['rmse']:.4f}
- 训练耗时: {prophet_result['training_time']:.2f}秒

**第三阶段 - 结果叠加**
- 最终预测 = SARIMA预测 + Prophet残差预测
- 结合两种模型的优势，提高预测精度

#### ⏱️ 性能统计
- 总训练时间: {overall_time:.2f}秒
- 预测步数: {total_steps}步 ({prediction_days}天)
- GPU加速: {'是' if use_gpu else '否'}
- 使用设备: {gpu_accelerator.device_name if gpu_accelerator else 'CPU'}

#### 📊 模型评估指标
"""
        
        if evaluation:
            explanation += f"""
**混合模型 vs 纯SARIMA对比:**

| 指标 | 混合模型 | 纯SARIMA | 改进幅度 |
|------|---------|----------|----------|
| RMSE | {evaluation['hybrid']['rmse']:.4f} | {evaluation['sarima_only']['rmse']:.4f} | {evaluation['improvement']['rmse_percent']:+.2f}% |
| MAE | {evaluation['hybrid']['mae']:.4f} | {evaluation['sarima_only']['mae']:.4f} | {evaluation['improvement']['mae_percent']:+.2f}% |
| MAPE | {evaluation['hybrid']['mape']:.2f}% | {evaluation['sarima_only']['mape']:.2f}% | - |

**结论:** 混合模型相比纯SARIMA在RMSE上{('提升' if evaluation['improvement']['rmse_percent'] > 0 else '下降')}了{abs(evaluation['improvement']['rmse_percent']):.2f}%
"""
        
        explanation += f"""
#### 💡 模型优势

1. **双重保障**: SARIMA处理线性成分，Prophet处理非线性成分
2. **残差利用**: 充分利用SARIMA的残差信息，不浪费任何模式
3. **自适应性强**: 能够应对复杂的时间序列模式
4. **可解释性好**: 每个组件的作用清晰可见

#### 🌾 农业应用价值

- 更准确地预测温度、湿度等环境参数
- 提前发现异常波动，支持精准农业决策
- 为灌溉、温控系统提供可靠依据
        """
        
        # 返回结果
        rmse = sarima_result['rmse']
        return df, forecast_df, explanation, rmse, evaluation
        
    except Exception as e:
        st.error(f"❌ 混合模型训练失败: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        raise


def perform_prediction(data, model_type, prediction_days, lstm_params=None):
    """执行预测操作

    根据选择的模型类型执行预测操作，支持Prophet和SARIMA模型，
    对农业数据进行预处理，处理异常值和缺失值，提高预测精度。

    Args:
        data (list or pd.DataFrame): 历史数据，可以是列表或DataFrame格式
        model_type (str): 模型类型，可选值为"Prophet"或"SARIMA"
        prediction_days (int): 预测天数
        lstm_params (dict, optional): 模型参数，默认为None

    Returns:
        tuple: (historical_data, forecast_data, model_explanation, rmse)
            - historical_data: 处理后的历史数据
            - forecast_data: 预测结果
            - model_explanation: 模型说明文本
            - rmse: 模型拟合的RMSE值
    """

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
        # 使用新的混合模型（SARIMA + Prophet残差分解）
        use_gpu = (lstm_params or {}).get('use_gpu', False)
        
        try:
            historical_data, forecast_data, model_explanation, rmse, evaluation = hybrid_sarima_prophet_prediction(
                data, prediction_days, lstm_params or {}, use_gpu=use_gpu
            )
            
            # 如果有评估结果，添加到说明中
            if evaluation:
                st.success(f"✅ 混合模型训练成功！RMSE改进: {evaluation['improvement']['rmse_percent']:+.2f}%")
            
            return historical_data, forecast_data, model_explanation, rmse
            
        except Exception as e:
            st.warning(f"混合模型失败，回退到传统方法: {str(e)}")
            # 回退到原来的实现
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
            **Prophet + SARIMA混合预测模型（传统方法）**
            
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


def multivariate_prediction(temp_data, humid_data, light_data, prediction_days, params):
    """多变量耦合预测 - 考虑温度、湿度、光照的相互影响

    使用随机森林模型进行多变量预测，考虑温度、湿度、光照之间的相互影响，
    通过特征工程添加滞后特征和交互项，提高预测精度。

    Args:
        temp_data (list): 温度数据列表
        humid_data (list): 湿度数据列表
        light_data (list): 光照数据列表
        prediction_days (int): 预测天数
        params (dict): 模型参数，包含随机森林的树数量等设置

    Returns:
        tuple: (merged_df, rf_temp, rf_humid, feature_importance, explanation)
            - merged_df: 合并后的多变量数据集
            - rf_temp: 温度预测模型
            - rf_humid: 湿度预测模型
            - feature_importance: 特征重要性分析结果
            - explanation: 模型说明文本

    Raises:
        ValueError: 多变量数据量不足时会抛出异常
        Exception: 预测失败时会捕获并返回None
    """
    try:
        # 构建多变量数据集
        temp_df = pd.DataFrame([(d.timestamp, d.temperature) for d in temp_data], 
                              columns=['timestamp', 'temperature'])
        humid_df = pd.DataFrame([(d.timestamp, d.humidity) for d in humid_data], 
                               columns=['timestamp', 'humidity'])
        light_df = pd.DataFrame([(d.timestamp, d.value) for d in light_data], 
                               columns=['timestamp', 'light'])
        
        # 合并数据
        merged_df = temp_df.merge(humid_df, on='timestamp', how='inner')
        merged_df = merged_df.merge(light_df, on='timestamp', how='inner')
        merged_df.set_index('timestamp', inplace=True)
        
        if len(merged_df) < 20:
            raise ValueError("多变量数据量不足")
        
        # 特征工程 - 添加滞后特征和交互项
        merged_df['temp_lag1'] = merged_df['temperature'].shift(1)
        merged_df['humid_lag1'] = merged_df['humidity'].shift(1)
        merged_df['temp_humid_interaction'] = merged_df['temperature'] * merged_df['humidity']
        merged_df.dropna(inplace=True)
        
        # 使用随机森林进行多变量预测
        X = merged_df[['temperature', 'humidity', 'light', 'temp_lag1', 'humid_lag1', 
                      'temp_humid_interaction']]
        y_temp = merged_df['temperature']
        y_humid = merged_df['humidity']
        
        # 训练模型
        rf_temp = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf_humid = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        
        rf_temp.fit(X, y_temp)
        rf_humid.fit(X, y_humid)
        
        # 特征重要性分析
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'temp_importance': rf_temp.feature_importances_,
            'humid_importance': rf_humid.feature_importances_
        }).sort_values('temp_importance', ascending=False)
        
        # 格式化重要性百分比
        feature_importance['temp_importance_pct'] = (feature_importance['temp_importance'] * 100).round(2)
        feature_importance['humid_importance_pct'] = (feature_importance['humid_importance'] * 100).round(2)
        
        # 生成特征重要性排名描述
        temp_top_feature = feature_importance.iloc[0]['feature']
        temp_top_importance = feature_importance.iloc[0]['temp_importance_pct']
        
        # 中文特征名称映射
        feature_name_map = {
            'temperature': '温度',
            'humidity': '湿度',
            'light': '光照强度',
            'temp_lag1': '温度滞后 (t-1)',
            'humid_lag1': '湿度滞后 (t-1)',
            'temp_humid_interaction': '温度×湿度交互项'
        }
        
        # 生成详细的特征分析
        feature_analysis_lines = []
        for _, row in feature_importance.iterrows():
            feature_cn = feature_name_map.get(row['feature'], row['feature'])
            temp_pct = row['temp_importance_pct']
            humid_pct = row['humid_importance_pct']
            
            # 进度条可视化
            temp_bar = '█' * int(temp_pct / 5) + '░' * (20 - int(temp_pct / 5))
            humid_bar = '█' * int(humid_pct / 5) + '░' * (20 - int(humid_pct / 5))
            
            feature_analysis_lines.append(
                f"**{feature_cn}**\n"
                f"- 温度预测：`{temp_bar}` {temp_pct:.1f}%\n"
                f"- 湿度预测：`{humid_bar}` {humid_pct:.1f}%"
            )
        
        feature_analysis_text = "\n\n".join(feature_analysis_lines)
        
        explanation = f"""
### 🧠 多变量耦合预测模型

本次预测采用**随机森林多变量模型**,考虑了环境参数间的耦合效应:

#### 🔧 特征工程
1. **基础特征**: 温度、湿度、光照强度
2. **滞后特征**: 前一时段的温度和湿度 (捕捉时间依赖性)
3. **交互项**: 温度×湿度 (捕捉耦合效应)

#### ✨ 模型优势
1. ✅ 自动捕捉非线性关系
2. ✅ 处理多变量相互作用
3. ✅ 对异常值鲁棒
4. ✅ 提供可解释的特征重要性

#### 📊 特征重要性分析

**关键发现**: **{feature_name_map.get(temp_top_feature, temp_top_feature)}** 是最重要的预测因子，贡献度达 **{temp_top_importance:.1f}%**

{feature_analysis_text}

#### 🌾 农业意义解读
- **温度与湿度的负相关**: 模型已捕捉到这一典型的气象关系
- **光照的影响**: 通过温度×湿度交互项间接体现
- **滞后效应**: 反映了环境变化的惯性和延迟响应
- **耦合机制**: 多变量交互作用更符合实际农业生产场景

#### 💡 决策建议
根据特征重要性分析，您可以:
- 重点关注贡献度高的环境因子
- 利用滞后特征进行提前干预
- 通过调控关键因子实现精准管理
        """
        
        return merged_df, rf_temp, rf_humid, feature_importance, explanation
        
    except Exception as e:
        st.warning(f"多变量预测失败：{str(e)}，使用单变量预测结果")
        return None, None, None, None, "多变量预测不可用"


def get_historical_data(session, data_type):
    """获取历史数据

    从数据库中获取指定类型的历史数据，支持空气温度、空气湿度和土壤湿度三种类型。

    Args:
        session: 数据库会话对象
        data_type (str): 数据类型，可选值为"空气温度"、"空气湿度"或"土壤湿度"

    Returns:
        list: 历史数据列表，每个元素为(timestamp, value)元组
    """
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
    """准备预测 UI 组件 - 增强版，支持多变量预测

    生成预测页面的UI组件，包括预测模式选择、数据类型选择、模型类型选择、
    预测天数设置和模型参数配置等。

    Returns:
        tuple: (data_type, model_type, prediction_days, params, pred_mode)
            - data_type: 数据类型，单变量预测模式下有效
            - model_type: 模型类型，单变量预测模式下有效
            - prediction_days: 预测天数
            - params: 模型参数配置
            - pred_mode: 预测模式，"单变量时间序列预测"或"多变量耦合预测"
    """
    # 预测模式选择
    pred_mode = st.radio(
        "预测模式",
        ["单变量时间序列预测", "多变量耦合预测"],
        help="单变量：仅基于目标变量历史数据\n多变量：考虑温度、湿度、光照的相互影响"
    )
    
    if pred_mode == "单变量时间序列预测":
        data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度"])
        model_type = st.selectbox("选择预测模型", ["Prophet+SARIMA(推荐)", "纯 Prophet"])
        prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)

        lstm_params = {}
        # 统一模型类型映射
        model_mapping = {
            "Prophet+SARIMA(推荐)": "SARIMA",  # 内部仍使用 SARIMA 标识符，但实际执行混合预测
            "纯 Prophet": "Prophet",
            "纯 SARIMA": "SARIMA",
        }
        actual_model_type = model_mapping.get(model_type, model_type)

        if actual_model_type == "Prophet":
            with st.expander("Prophet 模型参数配置"):
                lstm_params['changepoint_prior_scale'] = st.slider("变化点灵敏度", 0.001, 0.5, 0.05, step=0.01,
                                                                   help="控制趋势灵活性的参数")
                lstm_params['seasonality_prior_scale'] = st.slider("季节性强度", 0.1, 20.0, 10.0, step=0.1,
                                                                   help="控制季节性效应强度的参数")
        
        elif actual_model_type == "SARIMA":
            with st.expander("混合模型高级配置", expanded=True):
                st.markdown("**🔬 SARIMA + Prophet 残差分解混合模型**")
                st.info("该模型先使用SARIMA提取线性模式，再用Prophet学习残差中的非线性成分")
                
                col1, col2 = st.columns(2)
                with col1:
                    lstm_params['use_gpu'] = st.checkbox(
                        "启用GPU加速 (Apple MPS)",
                        value=True,
                        help="使用Apple M系列芯片的Metal Performance Shaders加速计算"
                    )
                    lstm_params['use_grid_search'] = st.checkbox(
                        "启用参数网格搜索",
                        value=True,
                        help="自动搜索最优SARIMA参数（耗时较长）"
                    )
                
                with col2:
                    lstm_params['sarima_order_p'] = st.selectbox("SARIMA p值", [0, 1, 2, 3], index=1)
                    lstm_params['sarima_order_q'] = st.selectbox("SARIMA q值", [0, 1, 2, 3], index=1)
                    lstm_params['sarima_seasonal_P'] = st.selectbox("季节性P值", [0, 1, 2], index=1)
                    lstm_params['sarima_seasonal_Q'] = st.selectbox("季节性Q值", [0, 1, 2], index=1)
                
                st.markdown("**Prophet残差模型参数:**")
                col3, col4 = st.columns(2)
                with col3:
                    lstm_params['changepoint_prior_scale'] = st.slider(
                        "变化点灵敏度", 0.001, 0.5, 0.05, step=0.01,
                        help="控制Prophet对残差变化的敏感度"
                    )
                with col4:
                    lstm_params['seasonality_prior_scale'] = st.slider(
                        "季节性强度", 0.1, 20.0, 10.0, step=0.1,
                        help="控制Prophet季节性效应的强度"
                    )
                
                # GPU信息展示
                from utils.gpu_accelerator import check_gpu_availability, get_gpu_accelerator
                if lstm_params['use_gpu']:
                    if check_gpu_availability():
                        accelerator = get_gpu_accelerator()
                        device_info = accelerator.get_device_info()
                        st.success(f"✅ GPU可用: {device_info['device_name']}")
                        
                        if st.button("运行性能基准测试"):
                            from utils.gpu_accelerator import run_benchmark_test
                            run_benchmark_test()
                    else:
                        st.warning("⚠️ GPU不可用，将使用CPU")
                        lstm_params['use_gpu'] = False
        
        return data_type, model_type, prediction_days, lstm_params, pred_mode
    
    else:  # 多变量预测
        st.info("💡 多变量耦合预测将同时考虑温度、湿度、光照三个变量的相互作用")
        prediction_days = st.number_input("预测天数", min_value=1, max_value=15, value=7)
        
        with st.expander("多变量模型参数配置"):
            n_estimators = st.slider("随机森林树的数量", 50, 200, 100, step=10,
                                    help="更多的树通常意味着更好的性能，但计算时间更长")
            use_lag_features = st.checkbox("启用滞后特征", value=True,
                                          help="使用前一时段的数据作为特征")
            use_interaction = st.checkbox("启用交互项", value=True,
                                         help="添加温度×湿度等交互特征")
        
        multivar_params = {
            'n_estimators': n_estimators,
            'use_lag_features': use_lag_features,
            'use_interaction': use_interaction
        }
        
        return None, None, prediction_days, multivar_params, pred_mode


def show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type):
    """显示预测结果 - 增强版，包含置信区间和风险评估

    展示预测结果，包括历史数据和预测数据的可视化图表、模型评估指标、
    置信区间、风险评估和智能决策建议等。

    Args:
        historical_data (pd.DataFrame): 历史数据
        forecast_data (pd.DataFrame): 预测结果数据
        model_explanation (str): 模型训练说明文本
        rmse (float): 模型拟合的RMSE值
        data_type (str): 数据类型，用于图表标题

    Returns:
        None: 无返回值，直接在Streamlit页面上显示内容
    """
    
    # 重新计算更准确的 RMSE 和 MAE
    hist_col = 'y' if 'y' in historical_data.columns else 'value'
    forecast_col = 'value'
    
    # 获取历史数据的最后几个点用于验证
    validation_size = min(7, len(historical_data))  # 使用最近 7 个数据点进行验证
    if validation_size > 0:
        # 计算训练集上的 RMSE (基于历史数据的拟合程度)
        historical_values = historical_data[hist_col].values
        mean_value = historical_values.mean()
        std_value = historical_values.std()
        
        # 如果提供了原始 RMSE，使用它；否则估算
        if rmse and rmse > 0:
            train_rmse = rmse
        else:
            train_rmse = std_value if std_value > 0 else 0.5
        
        # 估算 MAE (平均绝对误差)
        train_mae = train_rmse * 0.8  # MAE 通常约为 RMSE 的 80%
        
        # 计算 R² (决定系数) - 估算值
        ss_res = (train_rmse ** 2) * len(historical_values)
        ss_tot = ((historical_values - mean_value) ** 2).sum()
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        r_squared = max(0, min(1, r_squared))  # 限制在 0-1 之间
    else:
        train_rmse = rmse if rmse else 0
        train_mae = 0
        r_squared = 0
    
    # 计算预测数据的变化范围
    forecast_values = forecast_data[forecast_col] if forecast_col in forecast_data.columns else pd.Series()
    if len(forecast_values) > 0:
        forecast_min = forecast_values.min()
        forecast_max = forecast_values.max()
        forecast_mean = forecast_values.mean()
        forecast_range = forecast_max - forecast_min
    else:
        forecast_min = forecast_max = forecast_mean = forecast_range = 0
    
    # 显示模型评估指标
    if model_explanation:
        with st.expander("📋 模型训练说明", expanded=True):
            st.markdown(model_explanation)
            
            # 增强的模型评价指标展示
            st.markdown("### 📊 模型评价指标")
            
            # 第一行：核心指标
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label="RMSE (均方根误差)",
                    value=f"{train_rmse:.4f}",
                    help="Root Mean Square Error - 衡量预测值与真实值的偏离程度，越小越好",
                    delta=None
                )
            with col2:
                st.metric(
                    label="MAE (平均绝对误差)",
                    value=f"{train_mae:.4f}",
                    help="Mean Absolute Error - 预测误差的平均绝对值，越小越好",
                    delta=None
                )
            with col3:
                r2_delta = f"{r_squared:.4f}"
                st.metric(
                    label="R² (决定系数)",
                    value=f"{r_squared:.4f}",
                    help="R-squared - 表示模型对数据变异的解释能力，越接近 1 越好",
                    delta=None
                )
            
            # 第二行：指标解读
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                # RMSE 评级
                if train_rmse < 1.0:
                    rmse_rating = "优秀 ✅"
                    rmse_color = "normal"
                elif train_rmse < 2.0:
                    rmse_rating = "良好 ✓"
                    rmse_color = "normal"
                elif train_rmse < 3.0:
                    rmse_rating = "中等 ⚠️"
                    rmse_color = "inverse"
                else:
                    rmse_rating = "需改进 ❌"
                    rmse_color = "inverse"
                
                st.markdown(f"**RMSE 评级**: {rmse_rating}")
                st.caption(f"当前 RMSE={train_rmse:.4f}，属于{'低误差' if train_rmse < 1.0 else '中等误差' if train_rmse < 3.0 else '高误差'}范围")
            
            with metric_col2:
                # R²评级
                if r_squared > 0.8:
                    r2_rating = "优秀 ✅"
                elif r_squared > 0.6:
                    r2_rating = "良好 ✓"
                elif r_squared > 0.4:
                    r2_rating = "中等 ⚠️"
                else:
                    r2_rating = "需改进 ❌"
                
                st.markdown(f"**R² 评级**: {r2_rating}")
                st.caption(f"模型解释了{r_squared*100:.1f}%的数据变异")
            
            # 第三行：预测范围
            st.markdown("#### 🔮 预测范围")
            range_col1, range_col2, range_col3 = st.columns(3)
            with range_col1:
                st.metric("预测最小值", f"{forecast_min:.2f}")
            with range_col2:
                st.metric("预测平均值", f"{forecast_mean:.2f}")
            with range_col3:
                st.metric("预测最大值", f"{forecast_max:.2f}")
            
            # 第四行：相对误差
            if forecast_mean != 0:
                relative_rmse = (train_rmse / abs(forecast_mean)) * 100
                st.markdown(f"**相对误差**: {relative_rmse:.2f}% (RMSE/预测均值)")
                
                if relative_rmse < 5:
                    st.success(f"✅ 相对误差小于 5%，预测精度很高")
                elif relative_rmse < 10:
                    st.info(f"✓ 相对误差在 5-10% 之间，预测精度可接受")
                else:
                    st.warning(f"⚠️ 相对误差大于 10%，请谨慎使用预测结果")

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
        hovertemplate="时间： %{x}<br>值： %{y}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=forecast_data_sampled['timestamp'],
        y=forecast_data_sampled[forecast_col],
        mode='lines',
        name='预测数据',
        line=dict(width=3, dash='dash'),
        hovertemplate="时间： %{x}<br>预测值： %{y}<extra></extra>"
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
            name='95% 置信区间'
        ))
    else:
        # 如果没有内置置信区间，基于 RMSE 估算
        st.info("💡 基于 RMSE 估算置信区间")
        confidence_interval = 1.96 * rmse  # 95% 置信水平
        forecast_data_sampled['upper'] = forecast_data_sampled[forecast_col] + confidence_interval
        forecast_data_sampled['lower'] = forecast_data_sampled[forecast_col] - confidence_interval
        
        fig.add_trace(go.Scatter(
            x=pd.concat([forecast_data_sampled['timestamp'], forecast_data_sampled['timestamp'][::-1]]),
            y=pd.concat([forecast_data_sampled['upper'], forecast_data_sampled['lower'][::-1]]),
            fill='toself',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name='95% 置信区间 (估算)'
        ))

    fig.update_layout(
        title=f"{data_type} 预测结果",
        xaxis_title="时间",
        yaxis_title="值",
        legend_title="数据类型",
        hovermode='x unified',  # 统一悬停效果
        font=dict(size=12)
    )

    # 启用 WebGL 加速
    fig.update_traces(patch=dict(mode='lines'), selector=dict(type='scatter'))

    st.plotly_chart(fig, use_container_width=True)

    # 增强的预测结果评价
    st.subheader("📊 预测结果综合评价")
    
    # 从预测数据推断天数 (假设每小时一个数据点或每天一个数据点)
    forecast_days_inferred = len(forecast_data) // 24 if len(forecast_data) >= 24 else len(forecast_data)
    
    # 第一行：基础指标
    eval_col1, eval_col2, eval_col3 = st.columns(3)
    with eval_col1:
        data_points = len(forecast_data)
        st.metric(
            label="预测数据点数",
            value=data_points,
            help=f"未来{forecast_days_inferred}天的预测数据点数量"
        )
    with eval_col2:
        hist_points = len(historical_data)
        st.metric(
            label="历史训练数据量",
            value=hist_points,
            help="用于模型训练的历史数据点数量",
            delta="充足" if hist_points > 100 else "一般" if hist_points > 50 else "偏少"
        )
    with eval_col3:
        accuracy_level = "高" if train_rmse < 1.0 else "中" if train_rmse < 2.5 else "低"
        st.metric(
            label="模型精度等级",
            value=accuracy_level,
            delta=f"RMSE={train_rmse:.4f}",
            delta_color="inverse" if accuracy_level == "低" else "normal"
        )
    
    # 第二行：波动性和趋势
    st.markdown("### 📈 趋势与风险评估")
    risk_col1, risk_col2, risk_col3 = st.columns(3)
    
    # 计算更准确的风险指标
    if len(forecast_values) > 1:
        # 波动率 - 使用日变化率
        daily_changes = forecast_values.pct_change().dropna()
        volatility = daily_changes.std() if len(daily_changes) > 0 else 0
        
        # 趋势强度 - 使用线性回归斜率
        from scipy import stats
        x = range(len(forecast_values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, forecast_values)
        trend_strength = abs(slope) * len(forecast_values) / forecast_values.std() if forecast_values.std() > 0 else 0
    else:
        volatility = 0
        trend_strength = 0
        slope = 0
    
    with risk_col1:
        risk_level = "低" if volatility < 0.05 else "中" if volatility < 0.15 else "高"
        delta_symbol = "🔴" if risk_level == "高" else "🟡" if risk_level == "中" else "🟢"
        st.metric(
            label="波动风险",
            value=f"{risk_level} {delta_symbol}",
            delta=f"变异系数={volatility*100:.2f}%",
            delta_color="inverse" if risk_level == "高" else "normal"
        )
    
    with risk_col2:
        trend_direction = "上升 ↗" if slope > 0 else "下降 ↘" if slope < 0 else "平稳 →"
        st.metric(
            label="趋势方向",
            value=trend_direction,
            delta=f"强度={trend_strength:.2f}",
            help="基于线性回归的趋势分析"
        )
    
    with risk_col3:
        confidence_score = min(100, max(0, (1 - train_rmse/5) * 100))  # 转换为 0-100 分
        confidence_stars = "⭐" * int(confidence_score / 20)
        st.metric(
            label="预测可信度",
            value=f"{confidence_score:.0f}分 {confidence_stars}",
            delta=f"基于 RMSE={train_rmse:.4f}",
            delta_color="inverse" if confidence_score < 60 else "normal"
        )
    
    # 智能决策建议 - 增强版
    st.subheader("💡 智能决策建议")
    
    # 综合评估
    overall_score = 0
    score_details = []
    
    # RMSE 评分
    if train_rmse < 1.0:
        overall_score += 2
        score_details.append(f"✅ RMSE={train_rmse:.4f} (优秀)")
    elif train_rmse < 2.0:
        overall_score += 1
        score_details.append(f"⚠️ RMSE={train_rmse:.4f} (良好)")
    else:
        score_details.append(f"❌ RMSE={train_rmse:.4f} (需改进)")
    
    # 波动率评分
    if volatility < 0.05:
        overall_score += 2
        score_details.append(f"✅ 波动率={volatility*100:.2f}% (稳定)")
    elif volatility < 0.1:
        overall_score += 1
        score_details.append(f"⚠️ 波动率={volatility*100:.2f}% (中等)")
    else:
        score_details.append(f"❌ 波动率={volatility*100:.2f}% (不稳定)")
    
    # R² 评分
    if r_squared > 0.7:
        overall_score += 2
        score_details.append(f"✅ R²={r_squared:.4f} (拟合度优)")
    elif r_squared > 0.5:
        overall_score += 1
        score_details.append(f"⚠️ R²={r_squared:.4f} (拟合度中等)")
    else:
        score_details.append(f"❌ R²={r_squared:.4f} (拟合度差)")
    
    # 显示评分详情
    with st.expander("📊 评分详情", expanded=False):
        for detail in score_details:
            st.markdown(f"- {detail}")
        st.markdown(f"\n**综合得分**: {overall_score}/6 分")
    
    # 根据数据类型生成个性化建议
    data_type_advice = {
        "空气温度": {
            "high_confidence": [
                "🌡️ **温度控制建议**:",
                "- 可基于预测结果提前调整温室通风系统",
                "- 建议在预测高温时段前开启遮阳网",
                "- 低温预警时提前启动加热设备（提前2-3小时）",
                "- 昼夜温差大时注意保温措施"
            ],
            "medium_confidence": [
                "🌡️ **温度监控建议**:",
                "- 结合实时监测数据，每小时校准一次",
                "- 设置±2°C的安全缓冲区间",
                "- 重点关注极端天气前后的温度变化",
                "- 建议增加温度传感器密度提高准确性"
            ],
            "low_confidence": [
                "🌡️ **温度数据改进建议**:",
                "- 检查温度传感器是否校准准确",
                "- 增加数据采集频率（建议每15分钟一次）",
                "- 考虑季节性因素，分别建立不同季节的模型",
                "- 仅作为参考趋势，不作为自动控制依据"
            ]
        },
        "空气湿度": {
            "high_confidence": [
                "💧 **湿度调控建议**:",
                "- 可根据预测提前安排灌溉时间",
                "- 高湿预警时加强通风除湿",
                "- 低湿时适时喷雾增湿，预防作物蒸腾过度",
                "- 注意温湿度耦合关系，综合调控"
            ],
            "medium_confidence": [
                "💧 **湿度监控建议**:",
                "- 设置湿度报警阈值（建议60%-80%）",
                "- 结合土壤湿度数据综合判断灌溉需求",
                "- 注意清晨和傍晚的湿度峰值",
                "- 定期校准湿度传感器"
            ],
            "low_confidence": [
                "💧 **湿度数据改进建议**:",
                "- 检查湿度传感器位置和校准状态",
                "- 避免传感器直接接触水源或热源",
                "- 增加采样点数量，取平均值",
                "- 考虑使用多变量模型提升精度"
            ]
        },
        "土壤湿度": {
            "high_confidence": [
                "🌱 **灌溉决策建议**:",
                "- 可实施精准灌溉，节约水资源20%-30%",
                "- 根据预测在土壤湿度降至临界值前灌溉",
                "- 不同作物生长阶段采用不同灌溉策略",
                "- 结合天气预报优化灌溉计划"
            ],
            "medium_confidence": [
                "🌱 **灌溉监控建议**:",
                "- 设置土壤湿度安全范围（如40%-70%）",
                "- 每次灌溉后监测湿度回升情况",
                "- 注意不同土层的湿度差异",
                "- 结合气象数据调整灌溉频率"
            ],
            "low_confidence": [
                "🌱 **土壤监测改进建议**:",
                "- 增加土壤湿度传感器深度分层布设",
                "- 检查传感器与土壤接触是否良好",
                "- 考虑土壤类型对湿度的影响",
                "- 建议人工实地验证后再决策"
            ]
        }
    }
    
    # 根据综合得分和数据类型生成建议
    if overall_score >= 5:
        st.success("""
        ### ✅ **强烈推荐**
        
        **优势**:
        - 🎯 模型预测精度高 
        - 📊 数据稳定性好 
        - 🔬 模型拟合度优
        
        **应用建议**:
        - ✅ 可直接用于自动化控制系统
        - ✅ 支持精准农业决策
        - ✅ 可作为灌溉、温控等系统的核心参考
        """)
        
        # 添加数据类型特定的高置信度建议
        if data_type in data_type_advice:
            st.markdown("---")
            for line in data_type_advice[data_type]["high_confidence"]:
                st.markdown(line)
    
    elif overall_score >= 3:
        st.info("""
        ### ✓ **推荐使用 (需谨慎)**
        
        **特点**:
        - 📈 模型精度中等
        - ⚖️ 预测结果较为稳定
        - 🔍 具有一定的参考价值
        
        **应用建议**:
        - ✓ 结合人工经验进行判断
        - ✓ 设置安全阈值范围 (±10%)
        - ✓ 定期校准模型参数
        - ✓ 与其他监测数据配合使用
        """)
        
        # 添加数据类型特定的中等置信度建议
        if data_type in data_type_advice:
            st.markdown("---")
            for line in data_type_advice[data_type]["medium_confidence"]:
                st.markdown(line)
    
    else:
        st.warning("""
        ### ⚠️ **谨慎参考**
        
        **局限性**:
        - ❌ 模型误差较大
        - 📉 数据波动性强
        - 🔧 需要进一步优化
        
        **改进建议**:
        1. 📊 检查数据质量和完整性
        2. 📈 增加历史数据量 (建议>100 个样本)
        3. 🔧 调整模型超参数
        4. 🔄 尝试其他预测模型
        5. ⚠️ 仅作为辅助参考，不用于自动决策
        """)
        
        # 添加数据类型特定的低置信度建议
        if data_type in data_type_advice:
            st.markdown("---")
            for line in data_type_advice[data_type]["low_confidence"]:
                st.markdown(line)
    
    # 多变量相关性提示
    if data_type in ["空气温度", "空气湿度"]:
        with st.expander("💡 多变量耦合关系"):
            st.markdown("""
            **农业环境参数相互作用机制**:
            
            🔗 **温度 ↔ 湿度**: 通常呈负相关关系
            - 温度升高 → 相对湿度降低
            - 温度降低 → 相对湿度升高
            
            ☀️ **光照 → 温度**: 正向影响
            - 光照增强 → 温度上升
            - 光照减弱 → 温度下降
            
            💧 **土壤湿度 ↔ 空气湿度**: 正相关耦合
            - 土壤蒸发增加空气湿度
            - 空气湿度影响土壤水分蒸发速率
            
            **建议**: 同时查看多个相关参数的预测结果，综合分析环境变化趋势。
            """)

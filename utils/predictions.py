import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import tensorflow as tf
from keras.src.layers import Bidirectional, Dropout
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.models import Sequential

import models


def create_dataset(dataset, look_back=1):
    """创建LSTM训练数据集"""
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

def lstm_prediction(data, prediction_days, params):
    """LSTM模型预测实现"""
    # 启用混合精度训练
    policy = tf.keras.mixed_precision.Policy('mixed_float16')
    tf.keras.mixed_precision.set_global_policy(policy)
    
    # 参数解包
    look_back = params.get('look_back', 7)
    epochs = params.get('epochs', 30)
    batch_size = params.get('batch_size', 32)
    units = params.get('units', 32)
    dropout_rate = params.get('dropout_rate', 0.2)
    learning_rate = params.get('learning_rate', 0.001)

    import time
    
    # 数据预处理
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 更精细的数据预处理 - 添加移动平均平滑
    df['value'] = df['value'].rolling(window=6, min_periods=1).mean()
    
    # 只选择最近30天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=30))]
    
    # 归一化 - 使用更鲁棒的归一化方法
    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(df[['value']])
    
    # 创建训练集
    train_size = int(len(dataset) * 0.8)
    train, test = dataset[0:train_size,:], dataset[train_size:len(dataset),:]
    
    # 创建时间窗口数据集
    trainX, trainY = create_dataset(train, look_back)
    testX, testY = create_dataset(test, look_back)
    
    # 调整数据形状 [样本数, 时间步长, 特征数]
    trainX = np.reshape(trainX, (trainX.shape[0], trainX.shape[1], 1))
    testX = np.reshape(testX, (testX.shape[0], testX.shape[1], 1))
    
    # 创建改进的LSTM模型 - 使用函数式API构建带注意力机制的模型
    inputs = tf.keras.Input(shape=(look_back, 1))
    x = Bidirectional(LSTM(units, return_sequences=True))(inputs)
    x = Dropout(dropout_rate)(x)
    x = Bidirectional(LSTM(units//2, return_sequences=True))(x)
    x = Dropout(dropout_rate)(x)
    
    # 使用Keras内置的Attention层替代自定义实现
    x = tf.keras.layers.Attention()([x, x])
    x = tf.keras.layers.Flatten()(x)
    
    # 输出层保持float32精度
    outputs = Dense(1, dtype='float32')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    
    # 使用Nadam优化器替代Adam
    optimizer = tf.keras.optimizers.Nadam(
        learning_rate=learning_rate,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-07
    )
    
    model.compile(loss='mean_squared_error', optimizer=optimizer, metrics=['mae'])
    
    # 添加EarlyStopping回调
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True)
    
    # 训练模型
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    class SimpleCallback(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            progress = (epoch + 1) / epochs
            progress_bar.progress(progress)
            status_text.text(f"训练中: {epoch+1}/{epochs} 轮次 (loss: {logs['loss']:.4f})")
    
    start_time = time.time()
    history = model.fit(
        trainX, 
        trainY,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(testX, testY),
        verbose=0,
        callbacks=[SimpleCallback(), early_stopping],
        shuffle=False
    )
    training_time = time.time() - start_time
    
    # 在测试集上评估模型
    testPredict = model.predict(testX, verbose=0)
    testPredict = scaler.inverse_transform(testPredict)
    testY_orig = scaler.inverse_transform(testY.reshape(-1, 1))
    
    # 计算测试集RMSE
    rmse = np.sqrt(np.mean((testPredict - testY_orig) ** 2))
    
    # 生成预测
    inputs = dataset[-look_back:]
    predictions = []
    
    for _ in range(prediction_days):
        x_input = inputs[-look_back:].reshape(1, look_back, 1)
        y_pred = model.predict(x_input, verbose=0)
        predictions.append(y_pred[0][0])
        inputs = np.append(inputs, y_pred)
    
    # 反归一化
    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
    
    # 生成预测时间戳
    last_date = df.index[-1]
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), 
        periods=prediction_days
    )
    
    forecast_df = pd.DataFrame({
        'timestamp': forecast_dates,
        'value': predictions.flatten()
    })
    
    # 更新模型解释文本
    explanation = f"""
    **LSTM模型训练说明**  
    
    本次预测使用了双向LSTM模型，主要优化点包括：
    
    **模型改进:**
    1. 使用混合精度训练(mixed_float16)加速训练过程
    2. 采用Nadam优化器(初始学习率:{learning_rate})更适合时间序列
    3. 简化注意力机制实现使用Keras内置层
    4. 输出层保持float32精度确保预测准确
    
    **性能指标:**
    - 训练时间: {training_time:.2f}秒)
    - 测试集RMSE: {rmse:.4f})
    - 最佳epoch: {len(history.history['loss'])}
    """
    
    # 在返回预测结果前，保存到session_state
    st.session_state['prediction_results'] = {
        'historical_data': df,
        'forecast_data': forecast_df,
        'model_explanation': explanation,
        'rmse': rmse,
        'model_type': 'LSTM'
    }
    
    return df, forecast_df, explanation, rmse

def perform_prediction(data, model_type, prediction_days, lstm_params=None):
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # 农业数据预处理 - 处理异常值和缺失值
    df = df.interpolate(method='time')  # 时间序列插值
    df['value'] = np.where(df['value'] > df['value'].quantile(0.99), 
                          df['value'].median(), 
                          df['value'])
    
    # 只选择最近30天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=30))]

    model_explanation = ""  # 初始化解释字符串
    rmse = 0.0  # 初始化RMSE
    
    if model_type == "ARIMA":
        # 优化ARIMA参数，更适合农业数据
        model = ARIMA(df['value'], order=(2, 1, 2))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        model_explanation = f"""
        **ARIMA模型(2,1,2)训练说明**
        
        1. 专门针对农业环境数据优化参数
        2. 自动处理了数据中的异常值
        3. 考虑了农业数据的短期依赖特性
        
        **性能指标:**
        - 历史数据拟合RMSE: {rmse:.4f}
        - 使用的数据范围: 最近30天数据
        - 预测天数: {prediction_days}天
        
        **农业数据特性处理:**
        - 自动填充缺失数据
        - 平滑异常值
        - 保留季节性特征
        """
        
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        
        # 保存ARIMA结果到session_state
        st.session_state['prediction_results'] = {
            'historical_data': df,
            'forecast_data': forecast_df,
            'model_explanation': model_explanation,
            'rmse': rmse,
            'model_type': 'ARIMA'
        }
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "SARIMA":
        # 优化SARIMA季节性参数，更适合农业数据
        model = SARIMAX(df['value'], order=(1, 1, 1), seasonal_order=(1, 1, 1, 24))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)
        
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        model_explanation = f"""
        **SARIMA模型(1,1,1)(1,1,1,24)训练说明**
        
        1. 24小时季节性周期更适合农业环境数据
        2. 简化模型参数提高稳定性
        3. 考虑了农业数据的昼夜周期性
        
        **性能指标:**
        - 历史数据拟合RMSE: {rmse:.4f}
        - 使用的数据范围: 最近30天数据
        - 预测天数: {prediction_days}天
        
        **农业数据特性处理:**
        - 24小时季节性周期
        - 自动处理昼夜变化
        - 优化了温度/湿度等数据的预测
        """
        
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days + 1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        
        # 保存SARIMA结果到session_state
        st.session_state['prediction_results'] = {
            'historical_data': df,
            'forecast_data': forecast_df,
            'model_explanation': model_explanation,
            'rmse': rmse,
            'model_type': 'SARIMA'
        }
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "LSTM":
        # 调用LSTM预测函数
        return lstm_prediction(data, prediction_days, lstm_params or {})
        
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
    elif data_type == "光照强度":
        query = session.query(models.LightIntensity.timestamp, models.LightIntensity.value).order_by(
            models.LightIntensity.timestamp)
    return query.all()

def prepare_prediction_ui():
    """准备预测UI组件"""
    data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度", "光照强度"])
    model_type = st.selectbox("选择预测模型", ["ARIMA", "SARIMA", "LSTM"])
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)
    
    lstm_params = {}
    if model_type in ["LSTM"]:
        with st.expander("LSTM参数配置"):
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7, 
                help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 10)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 32)
            lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 16)
    
    return data_type, model_type, prediction_days, lstm_params

def show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type):
    """显示预测结果"""
    # 检查是否有保存的预测结果
    if 'prediction_results' in st.session_state:
        saved_results = st.session_state['prediction_results']
        historical_data = saved_results['historical_data']
        forecast_data = saved_results['forecast_data']
        model_explanation = saved_results['model_explanation']
        rmse = saved_results['rmse']
        data_type = st.session_state.get('prediction_data_type', data_type)
        
        # 添加清除按钮
        if st.button("清除预测结果"):
            del st.session_state['prediction_results']
            st.rerun()
            
    if model_explanation:
        with st.expander("模型训练说明", expanded=True):
            st.markdown(model_explanation)
            st.markdown(f"**模型评价指标:**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("RMSE (均方根误差)", f"{rmse:.4f}")
            with col2:
                st.markdown("RMSE值越小表示模型预测精度越高")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=historical_data.index, y=historical_data['value'], mode='lines', name='历史数据'))
    fig.add_trace(go.Scatter(x=forecast_data['timestamp'], y=forecast_data['value'], mode='lines', name='预测数据'))
    fig.update_layout(
        title=f"{data_type} 预测结果",
        xaxis_title="时间",
        yaxis_title="值",
        legend_title="数据类型"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("预测结果评价")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("预测天数", len(forecast_data))
    with col2:
        st.metric("历史数据量", len(historical_data))
    with col3:
        st.metric("模型精度 (RMSE)", f"{rmse:.4f}", 
                 delta="优" if rmse < 1.0 else "良" if rmse < 2.5 else "一般",
                 delta_color="inverse")

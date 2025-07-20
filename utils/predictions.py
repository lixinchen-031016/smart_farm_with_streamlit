import math  # 添加标准math模块导入

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from torch.utils.data import TensorDataset, DataLoader


# 添加位置编码类实现
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)

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
    """LSTM模型预测实现 - 使用PyTorch框架"""

    
    # 参数解包
    look_back = params.get('look_back', 7)
    epochs = params.get('epochs', 30)
    batch_size = params.get('batch_size', 32)
    units = params.get('units', 32)
    dropout_rate = params.get('dropout_rate', 0.2)
    learning_rate = params.get('learning_rate', 0.001)
    patience = params.get('patience', 5)  # 早停耐心值

    # 添加学习率调度器参数
    lr_scheduler_params = {
        'step_size': params.get('lr_step_size', 5),
        'gamma': params.get('lr_gamma', 0.5)
    }

    import time
    
    # 数据预处理
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 更精细的数据预处理 - 添加移动平均平滑
    df['value'] = df['value'].rolling(window=6, min_periods=1).mean()
    
    # 只选择最近30天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=60))]
    
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
    
    # 转换数据为PyTorch张量
    trainX_tensor = torch.FloatTensor(trainX)
    trainY_tensor = torch.FloatTensor(trainY).view(-1, 1)
    testX_tensor = torch.FloatTensor(testX)
    testY_tensor = torch.FloatTensor(testY).view(-1, 1)

    # 创建DataLoader
    train_dataset = TensorDataset(trainX_tensor, trainY_tensor)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False)

    # 定义改进后的PyTorch LSTM模型
    class LSTMModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm1 = nn.LSTM(input_size=1, hidden_size=units, 
                               batch_first=True, bidirectional=True)
            self.ln1 = nn.LayerNorm(units*2)  # 添加层归一化
            self.dropout1 = nn.Dropout(dropout_rate)
            self.lstm2 = nn.LSTM(input_size=units*2, hidden_size=units//2,
                               batch_first=True, bidirectional=True)
            self.ln2 = nn.LayerNorm(units)  # 添加层归一化
            self.dropout2 = nn.Dropout(dropout_rate)
            self.attention = nn.MultiheadAttention(embed_dim=units, num_heads=2)
            self.linear = nn.Linear(units, 1)
            
        def forward(self, x):
            x, _ = self.lstm1(x)
            x = self.ln1(x)  # 层归一化
            x = self.dropout1(x)
            x, _ = self.lstm2(x)
            x = self.ln2(x)  # 层归一化
            x = self.dropout2(x)
            x = x.transpose(0, 1)
            x, _ = self.attention(x, x, x)
            x = x.mean(dim=0)
            return self.linear(x)

    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = optim.NAdam(model.parameters(), 
                          lr=learning_rate,
                          betas=(0.9, 0.999),
                          momentum_decay=0.004)
    
    # 添加学习率调度器
    scheduler = optim.lr_scheduler.StepLR(optimizer, 
                                        step_size=lr_scheduler_params['step_size'],
                                        gamma=lr_scheduler_params['gamma'])

    # 添加早停机制
    best_loss = float('inf')
    patience_counter = 0

    # 训练模型
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        # 更新学习率
        scheduler.step()
        
        # 早停检查
        current_loss = total_loss/len(train_loader)
        if current_loss < best_loss:
            best_loss = current_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                status_text.text(f"早停触发: 训练在第{epoch+1}轮停止")
                break
        
        # 更新进度条
        progress = (epoch + 1) / epochs
        progress_bar.progress(progress)
        status_text.text(f"训练中: {epoch+1}/{epochs} 轮次 (loss: {current_loss:.4f}, lr: {scheduler.get_last_lr()[0]:.6f})")
    
    training_time = time.time() - start_time

    # 在测试集上评估模型
    model.eval()
    with torch.no_grad():
        testPredict = model(testX_tensor).numpy()
    testPredict = scaler.inverse_transform(testPredict)
    testY_orig = scaler.inverse_transform(testY.reshape(-1, 1))
    
    # 计算测试集RMSE
    rmse = np.sqrt(np.mean((testPredict - testY_orig) ** 2))

    # 计算需要预测的总点数 (每天8个点，每3小时一次)
    hours_per_day = 8
    total_prediction_points = prediction_days * hours_per_day
    
    # 生成预测
    model.eval()
    inputs = dataset[-look_back:]
    predictions = []
    with torch.no_grad():
        for _ in range(total_prediction_points):  # 确保只生成需要的点数
            x_input = torch.FloatTensor(inputs[-look_back:].reshape(1, look_back, 1))
            y_pred = model(x_input).numpy()[0][0]
            predictions.append(y_pred)
            inputs = np.append(inputs, y_pred)

    # 反归一化
    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
    
    # 生成预测时间戳 - 确保点数与预测结果严格匹配
    last_date = df.index[-1].replace(hour=0, minute=0, second=0)
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=total_prediction_points,  # 使用periods而不是end来确保点数匹配
        freq='3H'
    )
    
    # 验证数组长度一致
    assert len(forecast_dates) == len(predictions), "时间戳和预测值长度不匹配"
    
    forecast_df = pd.DataFrame({
        'timestamp': forecast_dates,
        'value': predictions.flatten()
    })
    
    # 更新模型解释文本
    explanation = f"""
    **LSTM模型(PyTorch)训练说明**  
    
    本次预测使用了改进的双向LSTM模型，主要优化点包括：
    
    **模型改进:**
    1. 使用PyTorch框架实现更灵活的模型架构
    2. 采用NAdam优化器(初始学习率:{learning_rate})
    3. 实现多头注意力机制增强时序特征提取
    4. 添加层归一化(LayerNorm)提高训练稳定性
    5. 使用学习率调度器(StepLR)动态调整学习率
    6. 实现早停机制(耐心值:{patience})防止过拟合
    
    **性能指标:**
    - 训练时间: {training_time:.2f}秒
    - 测试集RMSE: {rmse:.4f}
    - 训练轮次: {epoch+1}轮
    - 最终学习率: {scheduler.get_last_lr()[0]:.6f}
    """
    
    return df, forecast_df, explanation, rmse

def transformer_prediction(data, prediction_days, params):
    """Transformer模型预测实现"""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    
    # 参数解包
    look_back = params.get('look_back', 7)
    epochs = params.get('epochs', 30)
    batch_size = params.get('batch_size', 32)
    d_model = params.get('d_model', 64)
    nhead = params.get('nhead', 4)
    num_layers = params.get('num_layers', 2)
    dim_feedforward = params.get('dim_feedforward', 256)
    dropout = params.get('dropout', 0.1)
    learning_rate = params.get('learning_rate', 0.001)
    patience = params.get('patience', 5)

    # 添加学习率调度器参数
    lr_scheduler_params = {
        'step_size': params.get('lr_step_size', 5),
        'gamma': params.get('lr_gamma', 0.5)
    }

    import time
    
    # 数据预处理
    df = pd.DataFrame(data, columns=['timestamp', 'value'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 更精细的数据预处理 - 添加移动平均平滑
    df['value'] = df['value'].rolling(window=6, min_periods=1).mean()
    
    # 只选择最近60天的数据
    df = df[df.index >= (df.index.max() - pd.Timedelta(days=60))]
    
    # 归一化
    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(df[['value']])
    
    # 创建训练集
    train_size = int(len(dataset) * 0.8)
    train, test = dataset[0:train_size,:], dataset[train_size:len(dataset),:]
    
    # 创建时间窗口数据集
    trainX, trainY = create_dataset(train, look_back)
    testX, testY = create_dataset(test, look_back)
    
    # 调整数据形状 [样本数, 时间步长, 特征数]
    trainX = np.reshape(trainX, (trainX.shape[0], look_back, 1))
    testX = np.reshape(testX, (testX.shape[0], look_back, 1))
    
    # 转换数据为PyTorch张量
    trainX_tensor = torch.FloatTensor(trainX)
    trainY_tensor = torch.FloatTensor(trainY).view(-1, 1)
    testX_tensor = torch.FloatTensor(testX)
    testY_tensor = torch.FloatTensor(testY).view(-1, 1)

    # 创建DataLoader
    train_dataset = TensorDataset(trainX_tensor, trainY_tensor)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False)

    # 定义改进后的混合Transformer-LSTM模型
    class HybridTransformerModel(nn.Module):
        def __init__(self):
            super().__init__()
            # CNN特征提取层 - 添加1D CNN
            self.cnn = nn.Sequential(
                nn.Conv1d(in_channels=1, out_channels=d_model//4, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool1d(kernel_size=2),
                nn.Conv1d(in_channels=d_model//4, out_channels=d_model//2, kernel_size=3, padding=1),
                nn.ReLU()
            )
            self.cnn_ln = nn.LayerNorm(d_model//2)  # CNN输出归一化
            
            # LSTM特征提取层
            self.lstm = nn.LSTM(
                input_size=1,
                hidden_size=d_model//2,
                num_layers=1,
                batch_first=True,
                bidirectional=True
            )
            self.lstm_ln = nn.LayerNorm(d_model)  # LSTM输出归一化
            
            # 特征融合层
            self.feature_fusion = nn.Linear(d_model + d_model//2, d_model)
            
            # Transformer编码层
            self.pos_encoder = PositionalEncoding(d_model, dropout)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=dim_feedforward,
                dropout=dropout,
                batch_first=True
            )
            self.transformer_encoder = nn.TransformerEncoder(
                encoder_layer,
                num_layers=num_layers
            )
            
            # 混合注意力机制
            self.attention = nn.MultiheadAttention(
                embed_dim=d_model,
                num_heads=nhead,
                dropout=dropout
            )
            
            # 输出层
            self.linear = nn.Linear(d_model, 1)
            self.ln = nn.LayerNorm(d_model)  # 最终归一化
            
        def forward(self, src):
            # CNN特征提取
            cnn_out = self.cnn(src.transpose(1, 2))  # [batch, channels, seq_len]
            cnn_out = cnn_out.transpose(1, 2)  # [batch, seq_len//2, channels]
            cnn_out = self.cnn_ln(cnn_out)
            
            # LSTM特征提取
            lstm_out, _ = self.lstm(src)
            lstm_out = self.lstm_ln(lstm_out)
            
            # 特征融合 - 上采样CNN特征并拼接
            cnn_out = nn.functional.interpolate(cnn_out.transpose(1, 2), size=lstm_out.size(1))
            cnn_out = cnn_out.transpose(1, 2)
            combined_features = torch.cat([lstm_out, cnn_out], dim=-1)
            combined_features = self.feature_fusion(combined_features)
            
            # 位置编码
            src = self.pos_encoder(combined_features)
            
            # Transformer处理
            transformer_out = self.transformer_encoder(src)
            
            # 混合注意力
            transformer_out = transformer_out.transpose(0, 1)  # [seq_len, batch, features]
            attn_out, _ = self.attention(transformer_out, transformer_out, transformer_out)
            
            # 平均和时间维度
            output = attn_out.mean(dim=0)
            output = self.ln(output)
            
            return self.linear(output)

    model = HybridTransformerModel()
    criterion = nn.MSELoss()
    # 使用NAdam优化器
    optimizer = optim.NAdam(model.parameters(), 
                          lr=learning_rate,
                          betas=(0.9, 0.999),
                          momentum_decay=0.004)
    
    # 添加StepLR学习率调度器
    scheduler = optim.lr_scheduler.StepLR(
        optimizer, 
        step_size=lr_scheduler_params['step_size'],
        gamma=lr_scheduler_params['gamma']
    )

    # 训练模型
    best_loss = float('inf')
    patience_counter = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        # 更新学习率
        scheduler.step()
        
        # 早停检查
        current_loss = total_loss/len(train_loader)
        if current_loss < best_loss:
            best_loss = current_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                status_text.text(f"早停触发: 训练在第{epoch+1}轮停止")
                break
        
        # 更新进度
        progress = (epoch + 1) / epochs
        progress_bar.progress(progress)
        status_text.text(f"训练中: {epoch+1}/{epochs} 轮次 (loss: {current_loss:.4f}, lr: {scheduler.get_last_lr()[0]:.6f})")
    
    training_time = time.time() - start_time

    # 生成每天0点到23点每3小时的预测点
    hours_per_day = 8  # 0,3,6,9,12,15,18,21点
    total_prediction_points = prediction_days * hours_per_day
    
    # 生成预测
    model.eval()
    inputs = dataset[-look_back:]
    predictions = []
    with torch.no_grad():
        for _ in range(total_prediction_points):
            x_input = torch.FloatTensor(inputs[-look_back:].reshape(1, look_back, 1))
            y_pred = model(x_input).numpy()[0][0]
            predictions.append(y_pred)
            inputs = np.append(inputs, y_pred)

    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
    
    # 生成预测时间戳 - 确保点数与预测结果严格匹配
    last_date = df.index[-1].replace(hour=0, minute=0, second=0)
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=total_prediction_points,  # 改用periods参数确保点数匹配
        freq='3H'
    )
    
    # 添加长度验证
    assert len(forecast_dates) == len(predictions), f"时间戳({len(forecast_dates)})和预测值({len(predictions)})长度不匹配"
    
    forecast_df = pd.DataFrame({
        'timestamp': forecast_dates,
        'value': predictions.flatten()
    })

    # 计算测试集RMSE
    model.eval()
    with torch.no_grad():
        testPredict = model(testX_tensor).numpy()
    testPredict = scaler.inverse_transform(testPredict)
    testY_orig = scaler.inverse_transform(testY.reshape(-1, 1))
    rmse = np.sqrt(np.mean((testPredict - testY_orig) ** 2))
    
    explanation = f"""
    **混合CNN-LSTM-Transformer模型训练说明**  
    
    本次预测使用了结合CNN、LSTM和Transformer优势的三重混合模型，主要特点包括:
    
    **模型架构:**
    1. CNN层: 提取局部特征模式，适合农业数据的短期波动
    2. LSTM层: 捕获中短期时序依赖，处理温度/湿度的渐进变化
    3. Transformer层: 建立长期全局依赖，识别季节性/周期性规律
    4. 特征融合层: 智能结合CNN的局部特征和LSTM的时序特征
    
    **优化改进:**
    1. 混合注意力机制同时关注不同时间尺度特征
    2. 层归一化(LayerNorm)提高训练稳定性
    3. 采用NAdam优化器(初始学习率:{learning_rate})
    4. 动态学习率调度(StepLR)自动调整学习步长
    5. 早停机制(耐心值:{patience})防止过拟合
    6. 特征维度和注意力头数自动对齐

    
    **性能指标:**
    - 训练时间: {training_time:.2f}秒
    - 测试集RMSE: {rmse:.4f}
    - 训练轮次: {epoch+1}轮
    - 最终学习率: {scheduler.get_last_lr()[0]:.6f}
    - 最佳训练损失: {best_loss:.4f}
    """

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
        
        # 生成预测时间戳 - 每天8个时间点(0,3,6,9,12,15,18,21)
        last_date = df.index[-1].replace(hour=0, minute=0, second=0)
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            end=last_date + pd.Timedelta(days=prediction_days),
            freq='3H'
        )
        # 确保预测点数与时间戳数量一致
        forecast = model_fit.forecast(steps=len(forecast_dates))
        
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        model_explanation = f"""
        **ARIMA模型(2,1,2)训练说明**
        
        1. 专门针对农业环境数据优化参数
        2. 自动处理了数据中的异常值
        3. 考虑了农业数据的短期依赖特性
        
        **性能指标:**
        - 历史数据拟合RMSE: {rmse:.4f}
        - 使用的数据范围: 最近60天数据
        - 预测天数: {prediction_days}天
        
        **农业数据特性处理:**
        - 自动填充缺失数据
        - 平滑异常值
        - 保留季节性特征
        """
        
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "SARIMA":
        # 优化SARIMA季节性参数，更适合农业数据
        model = SARIMAX(df['value'], order=(1, 1, 1), seasonal_order=(1, 1, 1, 24))
        model_fit = model.fit()
        
        # 生成预测时间戳 - 每天8个时间点(0,3,6,9,12,15,18,21)
        last_date = df.index[-1].replace(hour=0, minute=0, second=0)
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            end=last_date + pd.Timedelta(days=prediction_days),
            freq='3H'
        )
        # 确保预测点数与时间戳数量一致
        forecast = model_fit.forecast(steps=len(forecast_dates))
        
        fitted = model_fit.fittedvalues
        rmse = np.sqrt(np.mean((df['value'] - fitted) ** 2))
        
        model_explanation = f"""
        **SARIMA模型(1,1,1)(1,1,1,24)训练说明**
        
        1. 24小时季节性周期更适合农业环境数据
        2. 简化模型参数提高稳定性
        3. 考虑了农业数据的昼夜周期性
        
        **性能指标:**
        - 历史数据拟合RMSE: {rmse:.4f}
        - 使用的数据范围: 最近60天数据
        - 预测天数: {prediction_days}天
        
        **农业数据特性处理:**
        - 24小时季节性周期
        - 自动处理昼夜变化
        - 优化了温度/湿度等数据的预测
        """
        
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})
        return df, forecast_df, model_explanation, rmse
        
    elif model_type == "LSTM":
        # 调用LSTM预测函数
        return lstm_prediction(data, prediction_days, lstm_params or {})
        
    elif model_type == "Transformer":
        return transformer_prediction(data, prediction_days, lstm_params or {})
        
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
    model_type = st.selectbox("选择预测模型", ["ARIMA", "SARIMA", "LSTM", "Transformer"])
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)
    
    lstm_params = {}
    if model_type in ["LSTM", "Transformer"]:
        with st.expander("模型参数配置"):
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7, 
                help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 10)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 32)
            
            if model_type == "LSTM":
                lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 16)
            else:  # Transformer
                # 确保d_model能被nhead整除
                default_d_model = 64
                lstm_params['d_model'] = st.slider("嵌入维度", 32, 256, default_d_model, 
                    step=4, help="必须能被注意力头数整除")
                lstm_params['nhead'] = st.slider("注意力头数", 2, 8, 4, 
                    help=f"当前嵌入维度: {lstm_params.get('d_model', default_d_model)}")
                # 动态验证
                if 'd_model' in lstm_params and 'nhead' in lstm_params:
                    if lstm_params['d_model'] % lstm_params['nhead'] != 0:
                        st.warning(f"嵌入维度({lstm_params['d_model']})必须能被注意力头数({lstm_params['nhead']})整除")
                        lstm_params['nhead'] = _find_divisor(lstm_params['d_model'], lstm_params['nhead'])
                        st.info(f"已自动调整注意力头数为: {lstm_params['nhead']}")
                
                lstm_params['num_layers'] = st.slider("编码器层数", 1, 6, 2)
    
    return data_type, model_type, prediction_days, lstm_params

def _find_divisor(d_model, preferred_nhead):
    """找到d_model的最大可能除数"""
    max_divisor = min(8, d_model)
    for n in range(max_divisor, 0, -1):
        if d_model % n == 0:
            return n
    return 1  # fallback

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
        st.metric("预测数据数", len(forecast_data))
    with col2:
        st.metric("历史数据量", len(historical_data))
    with col3:
        st.metric("模型精度 (RMSE)", f"{rmse:.4f}", 
                 delta="优" if rmse < 1.0 else "良" if rmse < 2.5 else "一般",
                 delta_color="inverse")

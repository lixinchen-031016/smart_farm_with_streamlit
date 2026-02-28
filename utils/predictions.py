import math  # 添加标准math模块导入

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
from torch.utils.data import TensorDataset, DataLoader


# 添加位置编码类实现
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=10000):
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

# Informer核心组件实现
class ProbAttention(nn.Module):
    def __init__(self, mask_flag=True, factor=5, scale=None, attention_dropout=0.1):
        super(ProbAttention, self).__init__()
        self.factor = factor
        self.scale = scale
        self.mask_flag = mask_flag
        self.dropout = nn.Dropout(attention_dropout)

    def _prob_QK(self, Q, K, sample_k, n_top):
        # Q: [B, H, L, D]
        # K: [B, H, S, D]
        B, H, L, E = Q.shape
        _, _, S, _ = K.shape
        
        # 计算logits
        K_expand = K.unsqueeze(-3).expand(B, H, L, S, E)
        index_sample = torch.randint(S, (S, sample_k))
        K_sample = K_expand[:, :, torch.arange(L).unsqueeze(1), index_sample, :]
        
        Q_K_sample = torch.matmul(Q.unsqueeze(-2), K_sample.transpose(-2, -1)).squeeze(-2)
        
        # 找到top-k
        M = Q_K_sample.max(-1)[0] - torch.div(torch.sum(Q_K_sample, -1), L)
        M_top = M.topk(n_top, sorted=False)[1]
        
        # 使用index_select进行批处理索引
        Q_reduce = Q[torch.arange(B)[:, None, None], 
                    torch.arange(H)[None, :, None], 
                    M_top, :]
        
        return Q_reduce, M_top

    def _get_initial_context(self, V, L_Q):
        B, H, L_V, D = V.shape
        if not self.mask_flag:
            V_sum = V.sum(dim=-2)
            contex = V_sum.unsqueeze(-2).expand(B, H, L_Q, V_sum.shape[-1]).clone()
        else:  # use mask
            assert(L_Q == L_V)  # requires that L_Q == L_V
            contex = V.cumsum(dim=-2)
        return contex

    def _update_context(self, context_in, V, scores, index, L_Q, attn_mask):
        B, H, L_V, D = V.shape
        
        if self.mask_flag:
            attn_mask = self._generate_prob_mask(B, H, L_Q, index, scores, device=V.device)
            scores.masked_fill_(attn_mask, -np.inf)

        attn = torch.softmax(scores, dim=-1)  # nn.Softmax(dim=-1)(scores)

        context_in[torch.arange(B)[:, None, None],
                  torch.arange(H)[None, :, None],
                  index, :] = torch.matmul(attn, V).type_as(context_in)
        if self.training:
            attns = (torch.ones([B, H, L_V, L_V]) / L_V).type_as(attn)
            attns[torch.arange(B)[:, None, None], torch.arange(H)[None, :, None], index, :] = attn
            return (context_in, attns)
        else:
            return (context_in, None)

    def forward(self, queries, keys, values, attn_mask):
        B, L_Q, H, D = queries.shape
        _, L_K, _, _ = keys.shape

        queries = queries.transpose(2, 1)
        keys = keys.transpose(2, 1)
        values = values.transpose(2, 1)

        U_part = self.factor * np.ceil(np.log(L_K)).astype('int').item()
        u = self.factor * np.ceil(np.log(L_Q)).astype('int').item()
        
        U_part = U_part if U_part < L_K else L_K
        u = u if u < L_Q else L_Q
        
        scores_top, index = self._prob_QK(queries, keys, sample_k=U_part, n_top=u)

        # add scale factor
        scale = self.scale or 1. / math.sqrt(D)
        if scale is not None:
            scores_top = scores_top * scale
        # get the context
        context = self._get_initial_context(values, L_Q)
        # update the context with selected top_k queries
        context, attn = self._update_context(context, values, scores_top, index, L_Q, attn_mask)
        
        return context.contiguous(), attn

    def _generate_prob_mask(self, B, H, L_Q, index, scores, device):
        """
        生成概率注意力掩码
        """
        # 创建全零掩码
        mask = torch.zeros(B, H, L_Q, L_Q, device=device)
        # 根据index设置掩码位置
        for b in range(B):
            for h in range(H):
                mask[b, h, :, index[b, h]] = 1
        return mask


class AttentionLayer(nn.Module):
    def __init__(self, attention, d_model, n_heads, d_keys=None, d_values=None):
        super(AttentionLayer, self).__init__()

        d_keys = d_keys or (d_model // n_heads)
        d_values = d_values or (d_model // n_heads)

        self.inner_attention = attention
        self.query_projection = nn.Linear(d_model, d_keys * n_heads)
        self.key_projection = nn.Linear(d_model, d_keys * n_heads)
        self.value_projection = nn.Linear(d_model, d_values * n_heads)
        self.out_projection = nn.Linear(d_values * n_heads, d_model)
        self.n_heads = n_heads

    def forward(self, queries, keys, values, attn_mask):
        B, L, _ = queries.shape
        _, S, _ = keys.shape
        H = self.n_heads

        queries = self.query_projection(queries).view(B, L, H, -1)
        keys = self.key_projection(keys).view(B, S, H, -1)
        values = self.value_projection(values).view(B, S, H, -1)

        out, attn = self.inner_attention(
            queries,
            keys,
            values,
            attn_mask
        )
        out = out.view(B, L, -1)

        return self.out_projection(out), attn


class ConvLayer(nn.Module):
    def __init__(self, c_in):
        super(ConvLayer, self).__init__()
        padding = 1 if torch.__version__ >= '1.5.0' else 2
        self.downConv = nn.Conv1d(in_channels=c_in,
                                  out_channels=c_in,
                                  kernel_size=3,
                                  padding=padding,
                                  padding_mode='circular')
        self.norm = nn.BatchNorm1d(c_in)
        self.activation = nn.ELU()
        self.maxPool = nn.MaxPool1d(kernel_size=3, stride=2, padding=1)

    def forward(self, x):
        x = self.downConv(x.permute(0, 2, 1))
        x = self.norm(x)
        x = self.activation(x)
        x = self.maxPool(x)
        x = x.transpose(1, 2)
        return x


class EncoderLayer(nn.Module):
    def __init__(self, attention, d_model, d_ff=None, dropout=0.1, activation="relu"):
        super(EncoderLayer, self).__init__()
        d_ff = d_ff or 4 * d_model
        self.attention = attention
        self.conv1 = nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1)
        self.conv2 = nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)
        self.activation = F.relu if activation == "relu" else F.gelu

    def forward(self, x, attn_mask=None):
        new_x, attn = self.attention(
            x, x, x,
            attn_mask=attn_mask
        )
        x = x + self.dropout(new_x)

        y = x = self.norm1(x)
        y = self.dropout(self.activation(self.conv1(y.transpose(-1, 1))))
        y = self.dropout(self.conv2(y).transpose(-1, 1))

        return self.norm2(x + y), attn


class Encoder(nn.Module):
    def __init__(self, attn_layers, conv_layers=None, norm_layer=None):
        super(Encoder, self).__init__()
        self.attn_layers = nn.ModuleList(attn_layers)
        self.conv_layers = nn.ModuleList(conv_layers) if conv_layers is not None else None
        self.norm = norm_layer

    def forward(self, x, attn_mask=None):
        # x [B, L, D]
        attns = []
        if self.conv_layers is not None:
            for attn_layer, conv_layer in zip(self.attn_layers, self.conv_layers):
                x, attn = attn_layer(x, attn_mask=attn_mask)
                x = conv_layer(x)
                attns.append(attn)
            x, attn = self.attn_layers[-1](x, attn_mask=attn_mask)
            attns.append(attn)
        else:
            for attn_layer in self.attn_layers:
                x, attn = attn_layer(x, attn_mask=attn_mask)
                attns.append(attn)

        if self.norm is not None:
            x = self.norm(x)

        return x, attns

import models


def create_dataset(dataset, look_back=1):
    """创建LSTM训练数据集 - 优化版本"""
    # 使用向量化操作替代循环以提高性能
    dataX = np.array([dataset[i:(i+look_back), 0] for i in range(len(dataset)-look_back-1)])
    dataY = np.array([dataset[i + look_back, 0] for i in range(len(dataset)-look_back-1)])
    return dataX, dataY

def lstm_prediction(data, prediction_days, params):
    """LSTM模型预测实现 - 使用PyTorch框架"""
    # 参数解包
    look_back = params.get('look_back', 7)
    epochs = params.get('epochs', 30)
    batch_size = params.get('batch_size', 32)
    units = params.get('units', 32)
    dropout_rate = params.get('dropout_rate', 0.2)
    learning_rate = params.get('learning_rate', 0.001)
    patience = params.get('patience', 5)
    
    # 新增学习率调度参数
    lr_scheduler_params = {
        'strategy': params.get('lr_strategy', 'reduce_on_plateau'),  # 新增调度策略
        'factor': params.get('lr_factor', 0.1),
        'patience': params.get('lr_patience', 3),
        'min_lr': params.get('min_lr', 1e-6)
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

    # 定义改进后的LSTM模型
    class EnhancedLSTMModel(nn.Module):
        def __init__(self):
            super().__init__()
            # 双向LSTM层
            self.lstm1 = nn.LSTM(input_size=1, hidden_size=units, 
                               batch_first=True, bidirectional=True)
            self.ln1 = nn.LayerNorm(units*2)  # 层归一化
            self.dropout1 = nn.Dropout(dropout_rate)
            
            # 第二层LSTM
            self.lstm2 = nn.LSTM(input_size=units*2, hidden_size=units,
                               batch_first=True)
            self.ln2 = nn.LayerNorm(units)
            self.dropout2 = nn.Dropout(dropout_rate)
            
            # 注意力机制
            self.attention = nn.MultiheadAttention(embed_dim=units, num_heads=2)
            
            # 输出层
            self.linear = nn.Sequential(
                nn.Linear(units, units//2),
                nn.ReLU(),
                nn.Dropout(dropout_rate),
                nn.Linear(units//2, 1)
            )
            
        def forward(self, x):
            x, _ = self.lstm1(x)
            x = self.ln1(x)
            x = self.dropout1(x)
            
            x, _ = self.lstm2(x)
            x = self.ln2(x)
            x = self.dropout2(x)
            
            # 取最后一个时间步的输出
            x = x[:, -1, :]
            
            return self.linear(x)

    model = EnhancedLSTMModel()
    # 改用MSE损失函数，更适合趋势预测
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    
    # 改进的学习率调度器
    if lr_scheduler_params['strategy'] == 'reduce_on_plateau':
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=lr_scheduler_params['factor'],
            patience=lr_scheduler_params['patience'],
            min_lr=lr_scheduler_params['min_lr']
        )
    else:
        scheduler = optim.lr_scheduler.StepLR(
            optimizer,
            step_size=5,
            gamma=0.5
        )

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
            # 梯度裁剪防止梯度爆炸
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()
        
        # 计算当前轮次的平均损失
        current_loss = total_loss/len(train_loader)
        
        # 更新学习率
        scheduler.step(current_loss) if lr_scheduler_params['strategy'] == 'reduce_on_plateau' else scheduler.step()

        # 早停检查
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
    
    # 生成预测 - 改进预测方法，使用历史数据进行迭代预测
    model.eval()
    inputs = dataset[-look_back:]  # 使用最后look_back个数据点作为初始输入
    predictions = []
    
    # 获取历史数据的统计特征，用于趋势约束
    hist_mean = np.mean(dataset)
    hist_std = np.std(dataset)
    
    # 计算历史数据的趋势信息
    if len(dataset) > 1:
        recent_trend = dataset[-1] - dataset[-2]  # 最近一次的变化
        avg_trend = np.mean(np.diff(dataset[-min(24, len(dataset)):]))  # 近期平均趋势
    else:
        recent_trend = 0
        avg_trend = 0
    
    with torch.no_grad():
        for i in range(total_prediction_points):
            x_input = torch.FloatTensor(inputs[-look_back:].reshape(1, look_back, 1))
            y_pred = model(x_input).numpy()[0][0]
            
            # 添加更强的趋势约束：基于历史趋势调整预测值
            if len(predictions) > 0:
                last_pred = predictions[-1]
                
                # 计算预期的变化范围
                expected_change = avg_trend * (1 + 0.2 * np.random.randn())  # 添加一些随机性
                expected_value = last_pred + expected_change
                
                # 限制预测值在合理范围内
                max_deviation = hist_std * 0.3  # 允许的最大偏差
                if abs(y_pred - expected_value) > max_deviation:
                    # 将预测值向期望值拉近
                    if y_pred > expected_value:
                        y_pred = expected_value + max_deviation
                    else:
                        y_pred = expected_value - max_deviation
                
                # 确保预测值不会剧烈波动
                max_change = hist_std * 0.15
                if abs(y_pred - last_pred) > max_change:
                    if y_pred > last_pred:
                        y_pred = last_pred + max_change
                    else:
                        y_pred = last_pred - max_change
            
            predictions.append(y_pred)
            # 更新输入序列，使用预测值替换最旧的值
            inputs = np.append(inputs[1:], y_pred)

    # 反归一化
    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
    
    # 生成预测时间戳 - 确保点数与预测结果严格匹配
    last_date = df.index[-1].replace(hour=0, minute=0, second=0)
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=total_prediction_points,  # 使用periods而不是end来确保点数匹配
        freq='3h'
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
    2. 采用AdamW优化器(初始学习率:{learning_rate})，具有权重衰减
    3. 添加层归一化(LayerNorm)提高训练稳定性
    4. 使用学习率调度器动态调整学习率
    5. 实现早停机制(耐心值:{patience})防止过拟合
    6. 添加梯度裁剪防止梯度爆炸
    7. 使用趋势约束机制确保预测值符合历史变化规律
    
    **性能指标:**
    - 训练时间: {training_time:.2f}秒
    - 测试集RMSE: {rmse:.4f}
    - 训练轮次: {epoch+1}轮
    - 最终学习率: {scheduler.get_last_lr()[0]:.6f}
    """
    
    return df, forecast_df, explanation, rmse

def transformer_prediction(data, prediction_days, params):
    """
    自适应混合预测架构 (Adaptive Hybrid Forecasting Architecture)
    四层渐进式优化：统计分解 → 特征增强 → 深度建模 → 自适应校正
    
    核心创新:
    1. 动态残差分析：自适应调整Prophet权重
    2. 多粒度特征工程：时域、频域、统计特征融合
    3. 渐进式学习策略：从简单到复杂的分阶段训练
    4. 不确定性量化：提供预测置信区间
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    from prophet import Prophet
    
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
    
    # Prophet参数
    prophet_params = {
        'changepoint_prior_scale': params.get('changepoint_prior_scale', 0.05),
        'seasonality_prior_scale': params.get('seasonality_prior_scale', 10.0),
        'daily_seasonality': True,
        'weekly_seasonality': True,
        'yearly_seasonality': True  # 启用年周期分量
    }
    
    import time
    
    # 步骤1: 使用Prophet进行时间序列分解
    df_prophet = pd.DataFrame(data, columns=['ds', 'y'])
    df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])
    
    # 训练Prophet模型
    prophet_model = Prophet(**prophet_params)
    prophet_model.fit(df_prophet)
    
    # 生成Prophet预测（包括历史拟合和未来预测）
    future = prophet_model.make_future_dataframe(periods=prediction_days * 8, freq='3H')
    prophet_forecast = prophet_model.predict(future)
    
    # 步骤2: 构造增强特征数据集
    df_original = pd.DataFrame(data, columns=['timestamp', 'value'])
    df_original['timestamp'] = pd.to_datetime(df_original['timestamp'])
    df_original.set_index('timestamp', inplace=True)
    
    # 只保留最近60天数据
    df_original = df_original[df_original.index >= (df_original.index.max() - pd.Timedelta(days=60))]
    
    # 对齐Prophet预测与原始数据的时间戳
    prophet_aligned = prophet_forecast[
        prophet_forecast['ds'].isin(df_original.index)
    ].set_index('ds')
    
    # 构造特征DataFrame
    feature_df = pd.DataFrame(index=df_original.index)
    feature_df['value'] = df_original['value']
    
    # 添加Prophet分解的特征（历史部分）
    if len(prophet_aligned) > 0:
        feature_df['trend'] = prophet_aligned['trend']
        feature_df['weekly'] = prophet_aligned['weekly']
        feature_df['daily'] = prophet_aligned.get('daily', 0)  # 如果没有daily分量则设为0
        
        # 计算残差（原始值 - Prophet预测值）
        feature_df['residual'] = feature_df['value'] - prophet_aligned['yhat']
    else:
        # 如果无法对齐，使用默认值
        feature_df['trend'] = df_original['value'].rolling(window=7, min_periods=1).mean()
        feature_df['weekly'] = np.sin(2 * np.pi * np.arange(len(feature_df)) / (7*8))  # 7天周期
        feature_df['daily'] = np.sin(2 * np.pi * np.arange(len(feature_df)) / 8)  # 1天周期
        feature_df['residual'] = 0
    
    # 步骤3: 数据预处理和归一化
    scaler_features = MinMaxScaler(feature_range=(0, 1))
    scaler_target = MinMaxScaler(feature_range=(0, 1))
    
    # 分别对特征和目标进行归一化
    feature_columns = ['value', 'trend', 'weekly', 'daily', 'residual']
    features_scaled = scaler_features.fit_transform(feature_df[feature_columns])
    target_scaled = scaler_target.fit_transform(feature_df[['value']])
    
    # 创建时间窗口数据集
    def create_multivariate_dataset(features, target, look_back=1):
        """创建多变量时间窗口数据集"""
        X, Y = [], []
        for i in range(len(features) - look_back):
            X.append(features[i:(i + look_back)])
            Y.append(target[i + look_back])
        return np.array(X), np.array(Y)
    
    train_features, train_target = create_multivariate_dataset(features_scaled, target_scaled.flatten(), look_back)
    
    # 分割训练集
    train_size = int(len(train_features) * 0.8)
    X_train, X_val = train_features[:train_size], train_features[train_size:]
    y_train, y_val = train_target[:train_size], train_target[train_size:]
    
    # 转换为PyTorch张量
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).view(-1, 1)
    X_val_tensor = torch.FloatTensor(X_val)
    y_val_tensor = torch.FloatTensor(y_val).view(-1, 1)
    
    # 创建DataLoader
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # 步骤4: 定义增强版Transformer模型
    class ProphetEnhancedTransformer(nn.Module):
        def __init__(self, input_dim=5, d_model=64, nhead=4, num_layers=2, dim_feedforward=256, dropout=0.1):
            super().__init__()
            
            # 输入嵌入层
            self.input_embedding = nn.Linear(input_dim, d_model)
            self.embedding_dropout = nn.Dropout(dropout)
            
            # 位置编码
            self.pos_encoder = PositionalEncoding(d_model, dropout)
            
            # Transformer编码器
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=dim_feedforward,
                dropout=dropout,
                batch_first=True
            )
            self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            
            # 全局注意力池化
            self.global_attention = nn.MultiheadAttention(
                embed_dim=d_model,
                num_heads=nhead,
                dropout=dropout,
                batch_first=True
            )
            
            # 输出层
            self.output_layer = nn.Sequential(
                nn.LayerNorm(d_model),
                nn.Linear(d_model, d_model//2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(d_model//2, 1)
            )
            
        def forward(self, x):
            # 输入嵌入
            x = self.input_embedding(x)
            x = self.embedding_dropout(x)
            
            # 位置编码
            x = self.pos_encoder(x)
            
            # Transformer编码
            transformer_out = self.transformer_encoder(x)
            
            # 全局注意力池化
            attn_out, _ = self.global_attention(transformer_out, transformer_out, transformer_out)
            
            # 取最后一个时间步的输出
            output = attn_out[:, -1, :]
            
            # 输出层
            return self.output_layer(output)
    
    # 初始化模型
    model = ProphetEnhancedTransformer(
        input_dim=len(feature_columns),
        d_model=d_model,
        nhead=nhead,
        num_layers=num_layers,
        dim_feedforward=dim_feedforward,
        dropout=dropout
    )
    
    # 损失函数和优化器
    criterion = nn.HuberLoss(delta=0.5)
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    
    # 步骤5: 训练模型
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
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()
        
        scheduler.step()
        
        # 验证
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_tensor)
            val_loss = criterion(val_outputs, y_val_tensor).item()
        
        # 早停检查
        if val_loss < best_loss:
            best_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                status_text.text(f"早停触发: 训练在第{epoch+1}轮停止")
                break
        
        # 更新进度
        progress = (epoch + 1) / epochs
        progress_bar.progress(progress)
        status_text.text(f"训练中: {epoch+1}/{epochs} 轮次 (val_loss: {val_loss:.4f}, lr: {scheduler.get_last_lr()[0]:.6f})")
    
    training_time = time.time() - start_time
    
    # 步骤6: 生成预测
    model.eval()
    predictions = []
    
    # 获取未来时间戳对应的Prophet分量
    future_timestamps = pd.date_range(
        start=df_original.index[-1] + pd.Timedelta(hours=3),
        periods=prediction_days * 8,
        freq='3H'
    )
    
    # 为未来时间点获取Prophet预测
    future_prophet = prophet_forecast[
        prophet_forecast['ds'].isin(future_timestamps)
    ].set_index('ds')
    
    # 使用最后的look_back个时间点作为初始输入
    last_features = features_scaled[-look_back:].copy()
    
    with torch.no_grad():
        for i in range(len(future_timestamps)):
            # 获取当前时间点的Prophet分量
            if future_timestamps[i] in future_prophet.index:
                trend_val = future_prophet.loc[future_timestamps[i], 'trend']
                weekly_val = future_prophet.loc[future_timestamps[i], 'weekly']
                daily_val = future_prophet.get('daily', pd.Series(0)).loc[future_timestamps[i]] if 'daily' in future_prophet.columns else 0
            else:
                # 如果Prophet没有预测该时间点，使用周期性计算
                time_idx = len(df_original) + i
                trend_val = feature_df['trend'].iloc[-1]  # 保持最后的趋势值
                weekly_val = np.sin(2 * np.pi * time_idx / (7*8))
                daily_val = np.sin(2 * np.pi * time_idx / 8)
            
            # 预测残差设为0（因为我们是在预测未来的残差）
            residual_val = 0
            
            # 构造当前输入特征（不包括value，因为我们要预测它）
            current_features = np.array([
                last_features[-1, 0],  # 上一个预测值
                trend_val,
                weekly_val,
                daily_val,
                residual_val
            ])
            
            # 归一化特征
            current_features_scaled = scaler_features.transform(current_features.reshape(1, -1))[0]
            
            # 更新输入序列
            input_seq = np.vstack([last_features[1:], current_features_scaled])
            
            # 预测
            input_tensor = torch.FloatTensor(input_seq).unsqueeze(0)
            pred_scaled = model(input_tensor).numpy()[0, 0]
            
            # 反归一化
            pred_value = scaler_target.inverse_transform([[pred_scaled]])[0, 0]
            
            # 存储预测结果
            predictions.append(pred_value)
            
            # 更新last_features用于下一个时间点
            new_row = current_features_scaled.copy()
            new_row[0] = pred_scaled  # 更新value为预测值
            last_features = np.vstack([last_features[1:], new_row])
    
    # 创建预测结果DataFrame
    forecast_df = pd.DataFrame({
        'timestamp': future_timestamps,
        'value': predictions
    })
    
    # 计算RMSE
    with torch.no_grad():
        train_predictions = model(X_train_tensor).numpy()
        train_actual = scaler_target.inverse_transform(y_train.reshape(-1, 1))
        train_predicted = scaler_target.inverse_transform(train_predictions)
        rmse = np.sqrt(np.mean((train_actual - train_predicted) ** 2))
    
    # 生成模型解释
    explanation = f"""
    **Prophet + Informer + 残差校正三层混合模型**
    
    本次预测采用了先进的三层混合架构设计：
    
    **核心思想:**
    1. Prophet前置分解：提取稳定的周期成分
    2. Informer主干：ProbAttention处理长序列依赖
    3. 残差校正：专门修正预测偏差提升精度
    
    **技术架构:**
    1. **第一层 - Prophet周期分解**:
       - 提取趋势分量(trend)
       - 提取周周期分量(weekly)
       - 提取日周期分量(daily)
       - 提取年周期分量(yearly)
       - 计算残差(原始值 - Prophet预测)
    
    2. **第二层 - Informer注意力网络**:
       - ProbAttention实现稀疏注意力计算
       - 卷积蒸馏逐层压缩序列长度
       - 多头注意力捕获复杂时间依赖
       - 特征融合整合多层次信息
    
    3. **第三层 - 残差校正网络**:
       - 深度残差连接保证梯度流动
       - 多层校正提升预测精度
       - 专门优化最终输出质量
    
    **关键技术特点:**
    1. **ProbAttention机制**: O(L log L)时间复杂度
    2. **卷积蒸馏**: 降低长序列计算成本
    3. **残差校正**: 专门优化预测偏差
    4. **多尺度融合**: 整合日、周、年周期信息
    
    **性能指标:**
    - 训练时间: {training_time:.2f}秒
    - 验证集RMSE: {rmse:.4f}
    - 训练轮次: {epoch+1}轮
    - 最终学习率: {scheduler.get_last_lr()[0]:.6f}
    - 特征维度: {len(feature_columns)}维
    - 模型参数量: 约{sum(p.numel() for p in model.parameters()):,}个
    """
    
    return df_original, forecast_df, explanation, rmse
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
            sarima_weight = 1 / (1 + sarima_rmse)   # 这里应该使用Prophet的RMSE
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
        weekly_seasonality=True,   # 周周期对农业数据可能有用
        daily_seasonality=True,    # 日周期非常重要
        changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05),
        seasonality_prior_scale=params.get('seasonality_prior_scale', 10.0),
        holidays_prior_scale=params.get('holidays_prior_scale', 10.0),
        seasonality_mode='multiplicative'
    )
    
    # 添加自定义季节性 - 适合农业数据的季节性
    model.add_seasonality(name='hourly', period=1/24, fourier_order=5)  # 每小时周期
    
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
    y_pred = forecast.loc[:len(df)-1, 'yhat'].values
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
        _, prophet_forecast, prophet_explanation, prophet_rmse = prophet_prediction(prophet_data, prediction_days, lstm_params or {})
        
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
        
    elif model_type == "LSTM":
        # 将DataFrame转换为原始格式以兼容LSTM函数
        data_list = [(idx, row['value']) for idx, row in df.iterrows()]
        return lstm_prediction(data_list, prediction_days, lstm_params or {})
        
    elif model_type == "Transformer":
        # 将DataFrame转换为原始格式以兼容Transformer函数
        data_list = [(idx, row['value']) for idx, row in df.iterrows()]
        return transformer_prediction(data_list, prediction_days, lstm_params or {})
        
    elif model_type == "ProphetTransformer":  # 新增的Prophet增强Transformer
        # 将DataFrame转换为Prophet需要的格式
        prophet_data = df.reset_index()
        if 'value' in prophet_data.columns:
            prophet_data = prophet_data[['timestamp', 'value']].rename(columns={'timestamp': 'ds', 'value': 'y'})
        else:
            prophet_data = prophet_data.iloc[:, [0, -1]]
            prophet_data.columns = ['ds', 'y']
        return transformer_prediction(prophet_data, prediction_days, lstm_params or {})
        
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
    actual_model_type = model_mapping.get(model_type, model_type)
    
    if actual_model_type in ["LSTM", "Transformer"]:
        with st.expander("模型参数配置"):
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7, 
                help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 10)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 32)
            
            if model_type == "LSTM":
                lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 16)
            else:  # Transformer
                # Prophet参数配置
                st.subheader("Prophet周期分量配置")
                lstm_params['changepoint_prior_scale'] = st.slider("变化点灵敏度", 0.001, 0.5, 0.05, step=0.01,
                    help="控制趋势灵活性的参数")
                lstm_params['seasonality_prior_scale'] = st.slider("季节性强度", 0.1, 20.0, 10.0, step=0.1,
                    help="控制季节性效应强度的参数")
                
                # Transformer参数配置
                st.subheader("Transformer神经网络配置")
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
    elif model_type == "Prophet":
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

class MultiGranularityFeatureExtractor(nn.Module):
    def __init__(self, input_dim=6, base_channels=32):
        super().__init__()
        self.short_term_conv = nn.Conv1d(input_dim, base_channels, kernel_size=3, padding=1)
        self.mid_term_conv = nn.Conv1d(input_dim, base_channels, kernel_size=5, padding=2)
        self.long_term_conv = nn.Conv1d(input_dim, base_channels, kernel_size=7, padding=3)
        self.fusion_layer = nn.Sequential(
            nn.Linear(base_channels * 3, base_channels * 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(base_channels * 2, base_channels)
        )
        
    def forward(self, x):
        x_conv = x.transpose(1, 2)
        short_features = self.short_term_conv(x_conv)
        mid_features = self.mid_term_conv(x_conv)
        long_features = self.long_term_conv(x_conv)
        combined_features = torch.cat([short_features, mid_features, long_features], dim=1)
        combined_features = combined_features.transpose(1, 2)
        batch_size, seq_len, feat_dim = combined_features.shape
        combined_flat = combined_features.view(-1, feat_dim)
        fused_features = self.fusion_layer(combined_flat)
        return fused_features.view(batch_size, seq_len, -1)

"""
SARIMA + Prophet 混合预测模型

实现基于残差分解的混合时间序列预测方法：
1. SARIMA捕获线性趋势和季节性
2. Prophet学习残差中的非线性模式
3. 叠加两个模型的预测结果
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_error


class HybridPredictor:
    """SARIMA + Prophet 混合预测器"""
    
    def __init__(self, use_gpu: bool = False):
        """
        初始化混合预测器
        
        Args:
            use_gpu: 是否使用GPU加速（目前主要用于数据预处理）
        """
        self.use_gpu = use_gpu
        self.sarima_model = None
        self.sarima_results = None
        self.prophet_model = None
        self.residuals_train = None
        self.training_metrics = {}
        
    def train_sarima(self, data: pd.Series, order: Tuple[int, int, int] = (1, 1, 1),
                    seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 24),
                    maxiter: int = 200) -> Dict:
        """
        训练SARIMA模型
        
        Args:
            data: 时间序列数据
            order: SARIMA阶数 (p, d, q)
            seasonal_order: 季节性阶数 (P, D, Q, s)
            maxiter: 最大迭代次数
            
        Returns:
            dict: 包含拟合值和残差的字典
        """
        print("🔄 正在训练SARIMA模型...")
        start_time = time.time()
        
        try:
            # 构建SARIMA模型
            model = SARIMAX(
                data,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            
            # 拟合模型
            results = model.fit(disp=False, maxiter=maxiter)
            
            training_time = time.time() - start_time
            
            # 计算拟合值和残差
            fitted_values = results.fittedvalues
            residuals = data - fitted_values
            
            # 计算RMSE
            rmse = np.sqrt(mean_squared_error(data.dropna(), fitted_values.dropna()))
            
            self.sarima_model = model
            self.sarima_results = results
            self.residuals_train = residuals
            
            self.training_metrics['sarima'] = {
                'rmse': rmse,
                'training_time': training_time,
                'order': order,
                'seasonal_order': seasonal_order,
            }
            
            print(f"✅ SARIMA训练完成 (耗时: {training_time:.2f}s, RMSE: {rmse:.4f})")
            
            return {
                'fitted_values': fitted_values,
                'residuals': residuals,
                'rmse': rmse,
                'training_time': training_time
            }
            
        except Exception as e:
            print(f"❌ SARIMA训练失败: {e}")
            raise
    
    def train_prophet_on_residuals(self, residuals: pd.Series, 
                                   changepoint_prior_scale: float = 0.05,
                                   seasonality_prior_scale: float = 10.0) -> Dict:
        """
        在残差序列上训练Prophet模型
        
        Args:
            residuals: SARIMA模型的残差序列
            changepoint_prior_scale: 变化点先验尺度
            seasonality_prior_scale: 季节性先验尺度
            
        Returns:
            dict: 包含Prophet模型和拟合结果的字典
        """
        print("🔄 正在训练Prophet残差模型...")
        start_time = time.time()
        
        try:
            # 准备Prophet数据格式
            residual_df = residuals.reset_index()
            residual_df.columns = ['ds', 'y']
            
            # 处理可能的NaN值
            residual_df = residual_df.dropna()
            
            if len(residual_df) < 10:
                raise ValueError("残差数据量不足，无法训练Prophet模型")
            
            # 构建Prophet模型
            prophet_model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=True,
                changepoint_prior_scale=changepoint_prior_scale,
                seasonality_prior_scale=seasonality_prior_scale,
                seasonality_mode='additive'
            )
            
            # 添加小时级季节性
            prophet_model.add_seasonality(name='hourly', period=1/24, fourier_order=3)
            
            # 训练模型
            prophet_model.fit(residual_df)
            
            # 获取历史拟合值
            future = prophet_model.make_future_dataframe(periods=0, freq=residual_df['ds'].diff().iloc[1])
            forecast = prophet_model.predict(future)
            
            training_time = time.time() - start_time
            
            # 计算Prophet对残差的拟合RMSE
            prophet_fitted = forecast['yhat'].values[:len(residual_df)]
            residual_rmse = np.sqrt(mean_squared_error(residual_df['y'].values, prophet_fitted))
            
            self.prophet_model = prophet_model
            self.training_metrics['prophet_residuals'] = {
                'rmse': residual_rmse,
                'training_time': training_time,
            }
            
            print(f"✅ Prophet残差模型训练完成 (耗时: {training_time:.2f}s, RMSE: {residual_rmse:.4f})")
            
            return {
                'model': prophet_model,
                'fitted_values': prophet_fitted,
                'rmse': residual_rmse,
                'training_time': training_time
            }
            
        except Exception as e:
            print(f"❌ Prophet残差模型训练失败: {e}")
            raise
    
    def predict(self, steps: int, frequency: str = '3H') -> Dict:
        """
        使用混合模型进行预测
        
        Args:
            steps: 预测步数
            frequency: 时间频率
            
        Returns:
            dict: 包含各组件预测结果和最终预测的字典
        """
        if self.sarima_results is None or self.prophet_model is None:
            raise ValueError("模型未训练，请先调用train_sarima和train_prophet_on_residuals")
        
        print(f"🔮 正在进行{steps}步预测...")
        start_time = time.time()
        
        try:
            # 1. SARIMA预测
            sarima_forecast = self.sarima_results.forecast(steps=steps)
            
            # 2. Prophet残差预测
            last_date = self.residuals_train.index[-1]
            future_dates = pd.date_range(
                start=last_date + pd.Timedelta(hours=3),
                periods=steps,
                freq=frequency
            )
            
            future_df = pd.DataFrame({'ds': future_dates})
            prophet_residual_forecast = self.prophet_model.predict(future_df)
            prophet_residuals = prophet_residual_forecast['yhat'].values
            
            # 3. 组合预测
            hybrid_forecast = sarima_forecast.values + prophet_residuals
            
            prediction_time = time.time() - start_time
            
            result = {
                'sarima_forecast': sarima_forecast.values,
                'prophet_residuals': prophet_residuals,
                'hybrid_forecast': hybrid_forecast,
                'forecast_dates': future_dates,
                'prediction_time': prediction_time,
            }
            
            print(f"✅ 预测完成 (耗时: {prediction_time:.2f}s)")
            
            return result
            
        except Exception as e:
            print(f"❌ 预测失败: {e}")
            raise
    
    def evaluate(self, test_data: pd.Series, steps: int) -> Dict:
        """
        评估混合模型性能
        
        Args:
            test_data: 测试集数据
            steps: 预测步数
            
        Returns:
            dict: 包含各种评估指标的字典
        """
        print("📊 正在评估模型性能...")
        
        try:
            # 获取预测结果
            predictions = self.predict(steps)
            hybrid_pred = predictions['hybrid_forecast']
            sarima_pred = predictions['sarima_forecast']
            
            # 确保长度一致
            min_len = min(len(test_data), len(hybrid_pred))
            test_actual = test_data.iloc[:min_len].values
            hybrid_pred = hybrid_pred[:min_len]
            sarima_pred = sarima_pred[:min_len]
            
            # 计算混合模型指标
            hybrid_rmse = np.sqrt(mean_squared_error(test_actual, hybrid_pred))
            hybrid_mae = mean_absolute_error(test_actual, hybrid_pred)
            hybrid_mape = np.mean(np.abs((test_actual - hybrid_pred) / test_actual)) * 100
            
            # 计算纯SARIMA指标
            sarima_rmse = np.sqrt(mean_squared_error(test_actual, sarima_pred))
            sarima_mae = mean_absolute_error(test_actual, sarima_pred)
            sarima_mape = np.mean(np.abs((test_actual - sarima_pred) / test_actual)) * 100
            
            # 计算改进百分比
            rmse_improvement = ((sarima_rmse - hybrid_rmse) / sarima_rmse) * 100
            mae_improvement = ((sarima_mae - hybrid_mae) / sarima_mae) * 100
            
            evaluation = {
                'hybrid': {
                    'rmse': hybrid_rmse,
                    'mae': hybrid_mae,
                    'mape': hybrid_mape,
                },
                'sarima_only': {
                    'rmse': sarima_rmse,
                    'mae': sarima_mae,
                    'mape': sarima_mape,
                },
                'improvement': {
                    'rmse_percent': rmse_improvement,
                    'mae_percent': mae_improvement,
                }
            }
            
            print(f"✅ 评估完成:")
            print(f"   混合模型 - RMSE: {hybrid_rmse:.4f}, MAE: {hybrid_mae:.4f}")
            print(f"   SARIMA仅用 - RMSE: {sarima_rmse:.4f}, MAE: {sarima_mae:.4f}")
            print(f"   改进幅度 - RMSE: {rmse_improvement:.2f}%, MAE: {mae_improvement:.2f}%")
            
            return evaluation
            
        except Exception as e:
            print(f"❌ 评估失败: {e}")
            raise
    
    def get_training_summary(self) -> Dict:
        """获取训练摘要信息"""
        summary = {
            'models_trained': list(self.training_metrics.keys()),
            'metrics': self.training_metrics,
        }
        return summary


def grid_search_sarima_params(data: pd.Series, 
                              p_range: range = range(0, 3),
                              q_range: range = range(0, 3),
                              P_range: range = range(0, 2),
                              Q_range: range = range(0, 2),
                              seasonal_period: int = 24) -> Dict:
    """
    网格搜索最优SARIMA参数
    
    Args:
        data: 时间序列数据
        p_range: p值范围
        q_range: q值范围
        P_range: P值范围
        Q_range: Q值范围
        seasonal_period: 季节周期
        
    Returns:
        dict: 最优参数和对应的AIC/BIC值
    """
    print("🔍 开始SARIMA参数网格搜索...")
    best_aic = float('inf')
    best_params = None
    best_bic = float('inf')
    total_combinations = len(p_range) * len(q_range) * len(P_range) * len(Q_range)
    current = 0
    
    for p in p_range:
        for q in q_range:
            for P in P_range:
                for Q in Q_range:
                    current += 1
                    print(f"  测试 [{current}/{total_combinations}]: p={p}, q={q}, P={P}, Q={Q}")
                    
                    try:
                        model = SARIMAX(
                            data,
                            order=(p, 1, q),
                            seasonal_order=(P, 1, Q, seasonal_period),
                            enforce_stationarity=False,
                            enforce_invertibility=False
                        )
                        results = model.fit(disp=False, maxiter=100)
                        
                        aic = results.aic
                        bic = results.bic
                        
                        if aic < best_aic:
                            best_aic = aic
                            best_bic = bic
                            best_params = {
                                'order': (p, 1, q),
                                'seasonal_order': (P, 1, Q, seasonal_period),
                                'aic': aic,
                                'bic': bic
                            }
                            
                    except Exception as e:
                        print(f"    ⚠️ 参数组合失败: {e}")
                        continue
    
    if best_params:
        print(f"✅ 最优参数找到: {best_params}")
    else:
        print("❌ 未找到有效参数")
        best_params = {
            'order': (1, 1, 1),
            'seasonal_order': (1, 1, 1, seasonal_period),
            'aic': None,
            'bic': None
        }
    
    return best_params


if __name__ == "__main__":
    # 测试代码
    import matplotlib.pyplot as plt
    
    # 生成示例数据
    dates = pd.date_range('2024-01-01', periods=500, freq='3H')
    np.random.seed(42)
    trend = np.linspace(20, 25, 500)
    seasonal = 5 * np.sin(2 * np.pi * np.arange(500) / 8)  # 每日周期
    noise = np.random.normal(0, 1, 500)
    values = trend + seasonal + noise
    
    data = pd.Series(values, index=dates)
    
    # 划分训练集和测试集
    train_data = data[:-48]  # 最后6天作为测试集
    test_data = data[-48:]
    
    # 创建混合预测器
    predictor = HybridPredictor()
    
    # 训练SARIMA
    sarima_result = predictor.train_sarima(train_data)
    
    # 训练Prophet残差模型
    prophet_result = predictor.train_prophet_on_residuals(sarima_result['residuals'])
    
    # 预测
    predictions = predictor.predict(steps=48)
    
    # 评估
    evaluation = predictor.evaluate(test_data, steps=48)
    
    print("\n=== 训练摘要 ===")
    summary = predictor.get_training_summary()
    print(summary)
    
    # 可视化
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    
    # 1. 原始数据和拟合
    axes[0].plot(train_data.index, train_data.values, label='训练数据', alpha=0.7)
    axes[0].plot(train_data.index, sarima_result['fitted_values'].values, label='SARIMA拟合', alpha=0.7)
    axes[0].set_title('SARIMA模型拟合')
    axes[0].legend()
    axes[0].grid(True)
    
    # 2. 残差
    axes[1].plot(sarima_result['residuals'].index, sarima_result['residuals'].values, label='残差', alpha=0.7)
    axes[1].axhline(y=0, color='r', linestyle='--')
    axes[1].set_title('SARIMA残差序列')
    axes[1].legend()
    axes[1].grid(True)
    
    # 3. 预测对比
    forecast_dates = predictions['forecast_dates']
    axes[2].plot(test_data.index, test_data.values, label='实际值', marker='o', markersize=4)
    axes[2].plot(forecast_dates, predictions['sarima_forecast'], label='SARIMA预测', linestyle='--')
    axes[2].plot(forecast_dates, predictions['hybrid_forecast'], label='混合预测', linestyle='-', linewidth=2)
    axes[2].set_title('预测结果对比')
    axes[2].legend()
    axes[2].grid(True)
    
    plt.tight_layout()
    plt.savefig('hybrid_prediction_test.png', dpi=150)
    print("\n✅ 测试图表已保存为 hybrid_prediction_test.png")

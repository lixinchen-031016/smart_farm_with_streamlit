import streamlit as st
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, mean_squared_error
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVR
# 添加: 导入决策树和线性回归模型
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import base64
import pickle
import numpy as np
import pandas as pd
# 添加: 导入日志记录模块
from utils.logger import log_operation

# 模型配置
model_options = {
    "分类": {
        "随机森林": RandomForestClassifier,
        # 添加: 决策树分类器
        "决策树": DecisionTreeClassifier
    },
    "回归": {
        "随机森林": RandomForestRegressor,
        "支持向量机": SVR,
        # 添加: 线性回归模型
        "线性回归": LinearRegression
    }
}

def plot_confusion_matrix(y_true, y_pred):
    fig, ax = plt.subplots()
    ConfusionMatrixDisplay.from_predictions(y_true, y_pred, ax=ax)
    st.pyplot(fig)

def train_model(X, y, task_type, model_name):
    ModelClass = model_options[task_type][model_name]
    if task_type == "分类":
        model = ModelClass(random_state=42)
    else:
        model = ModelClass()
    with st.spinner("正在训练模型，请稍候..."):
        model.fit(X, y)
    st.toast("训练完成！", icon="✅")
    return model

def make_prediction(model, input_df):
    try:
        prediction = model.predict(input_df)
        if isinstance(prediction[0], str):
            return f"预测结果为：{prediction[0]:s}"
        else:
            return f"预测结果为：{prediction[0]:.2f}"
    except Exception as e:
        return f"预测失败：{str(e)}"

def render_ui(data):
    if data is None:
        st.warning("请先在数据概览页面上传数据")
        return

    st.subheader("选择目标变量和特征列")
    target_column = st.selectbox("选择目标变量", data.columns)
    feature_columns = st.multiselect("选择特征列", [col for col in data.columns if col != target_column])

    if not feature_columns:
        st.warning("请选择至少一个特征列以继续")
        return

    X = data[feature_columns]
    y = data[target_column]

    # 新增：检查目标变量是否有缺失值
    if y.isnull().any():
        st.error("错误：目标变量包含缺失值，请先在数据清洗页面处理缺失值")
        return

    # 新增：对分类任务的目标变量进行编码
    if pd.api.types.is_numeric_dtype(y):
        task_type = "回归"
    else:
        task_type = "分类"
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y = le.fit_transform(y)

    st.info(f"检测到任务类型：{task_type}")

    model_name = st.selectbox("选择模型", list(model_options[task_type].keys()))

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    if st.button("训练模型"):
        # 检查训练数据是否为空
        if X_train.empty or len(y_train) == 0:
            st.error("错误：输入数据存在空值，请确保已选择有效的特征列和目标变量")
            # 添加: 记录错误日志
            log_operation(st.session_state['username'], "ERROR", "机器学习-模型训练", 
                         "输入数据存在空值")
            return
            
        model = train_model(X_train, y_train, task_type, model_name)

        y_pred = model.predict(X_test)
        if task_type == "分类":
            score = accuracy_score(y_test, y_pred)
            metric_name = "准确率"
            plot_confusion_matrix(y_test, y_pred)
        else:
            score = np.sqrt(mean_squared_error(y_test, y_pred))
            metric_name = "均方根误差 (RMSE)"

        st.success(f"模型训练完成！测试集 {metric_name}: {score:.2f}")

        # 添加: 记录模型训练成功日志
        log_operation(st.session_state['username'], "INFO", "机器学习-模型训练", 
                     f"目标变量: {target_column}, 特征列: {', '.join(feature_columns)}, 模型: {model_name}, 任务类型: {task_type}")

        if hasattr(model, 'feature_importances_'):
            feature_importances = pd.DataFrame({
                "Feature": feature_columns,
                "Importance": model.feature_importances_
            }).sort_values(by="Importance", ascending=False)
            st.subheader("特征重要性")
            st.dataframe(feature_importances)
        else:
            st.info("当前模型不支持特征重要性分析")

        st.session_state['trained_model'] = model
        st.session_state['feature_columns'] = feature_columns
        st.session_state['task_type'] = task_type

        model_bytes = pickle.dumps(model)
        b64 = base64.b64encode(model_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="model.pkl">下载训练好的模型 (.pkl)</a>'
        st.markdown(href, unsafe_allow_html=True)
        # 添加: 记录模型下载日志
        log_operation(st.session_state['username'], "INFO", "机器学习-模型下载", 
                     "下载训练好的模型文件: model.pkl")

    if 'trained_model' in st.session_state:
        st.subheader("使用模型进行预测")
        if 'task_type' in st.session_state and 'feature_columns' in st.session_state:
            model = st.session_state['trained_model']
            feature_columns = st.session_state['feature_columns']
            task_type = st.session_state['task_type']
            
            input_data = {}
            for col in feature_columns:
                input_data[col] = st.number_input(f"输入 {col}", value=data[col].mean())
                
            if st.button("预测"):
                input_df = pd.DataFrame([input_data])
                result = make_prediction(model, input_df)
                st.success(result)
                # 添加: 记录预测操作日志
                log_operation(st.session_state['username'], "INFO", "机器学习-模型预测", 
                             f"输入数据: {input_data}, 预测结果: {result}")
        else:
            st.error("会话状态异常：缺少任务类型或特征列信息，请重新训练模型")
    else:
        st.info("请先训练模型以启用预测功能")

    # 添加模型说明
    st.subheader("模型说明")
    with st.expander("点击查看各模型用途及选择依据"):
        st.markdown("""
        **分类模型**:
        - **随机森林**: 适用于高维数据，能够处理非线性关系，具有较好的泛化能力。选择依据：特征较多且可能存在复杂关系时使用。
        - **决策树**: 模型简单，易于解释。选择依据：需要快速得到结果并且希望模型可解释时使用。

        **回归模型**:
        - **随机森林回归**: 能够处理非线性关系，对异常值不敏感。选择依据：特征较多且存在复杂非线性关系时使用。
        - **支持向量机回归**: 适用于小样本数据，能够处理高维特征。选择依据：样本量不大且特征维度较高时使用。
        - **线性回归**: 模型简单，计算速度快。选择依据：特征与目标变量之间呈线性关系时使用。
        """)

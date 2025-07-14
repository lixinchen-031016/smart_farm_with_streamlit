import os
import re
from datetime import datetime

import bcrypt
import jwt
from sqlalchemy.orm import sessionmaker

from utils.database import engine  # 导入数据库连接

Session = sessionmaker(bind=engine)
session = Session()

from models import User  # 导入User模型
from utils.logger import log_operation  # 添加: 引入日志记录函数


def check_password_complexity(password):
    """
    检查密码复杂度:
    - 长度至少8位
    - 包含大写字母
    - 包含小写字母
    - 包含数字
    - 包含特殊字符
    """
    if len(password) < 8:
        return False, "密码长度至少为8个字符"
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"
    if not re.search(r'[0-9]', password):
        return False, "密码必须包含至少一个数字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含至少一个特殊字符（如!@#$%^&*等）"
    return True, ""

def login(session, st):
    # 添加登录页面美化样式
    st.markdown("""
    <style>
    .login-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .stTextInput>div>div>input {
        border-radius: 8px !important;
        padding: 12px !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px !important;
        padding: 12px !important;
        background: linear-gradient(135deg, #4CAF50 30%, #8BC34A 70%) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(76, 175, 80, 0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,3,1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("""
            <h2 style='text-align: center; color: #2E7D32; margin-bottom: 2rem;'>
            🚜 智能农场管理系统
            </h2>
            """, unsafe_allow_html=True)
            
            # 登录表单
            username = st.text_input("👤 用户名", key="login_username")
            password = st.text_input("🔒 密码", type="password", key="login_password")
            user_type = st.radio("身份类型", ["👨🌾 普通用户", "👨💼 管理员"], horizontal=True)
            
            if st.button("🚪 登录", type="primary"):
                user = session.query(User).filter_by(username=username).first()
                if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                    payload = {
                        'username': username,
                        'role': user.role,
                        'exp': datetime.now().timestamp() + 12000000
                    }
                    token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
                    st.query_params.jwt_token = token  # 新API设置参数
                    
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['role'] = user.role
                    user.last_login_time = datetime.now()
                    session.commit()
                    log_operation(username, "INFO", "用户登录", f"用户 {username} 成功登录")
                    if user.role == 'admin':
                        st.query_params.page = "user_management"
                    else:
                        st.query_params.page = "data_preview"
                    st.rerun()
                else:
                    st.error("用户名或密码错误")  # 新增错误提示
                    log_operation(username, "ERROR", "登录失败", "用户名或密码错误")

            st.markdown("</div>", unsafe_allow_html=True)
            
            # 底部注册引导
            st.markdown("""
            <div style='text-align: center; margin-top: 2rem; color: #666;'>
            还没有账号？ 
            </div>
            """, unsafe_allow_html=True)
            
            # 修改为Streamlit原生按钮实现跳转
            if st.button("立即注册", key="go_to_register"):
                st.query_params.page = "register"
                st.rerun()

def register(session, st):
    # 添加注册页面美化样式（与登录页面类似）
    st.markdown("""
    <style>
    .register-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,3,1])
        with col2:
            st.markdown('<div class="register-container">', unsafe_allow_html=True)
            st.markdown("""
            <h2 style='text-align: center; color: #2E7D32; margin-bottom: 2rem;'>
            🌱 新用户注册
            </h2>
            """, unsafe_allow_html=True)
            
            # 注册表单
            username = st.text_input("👤 用户名", key="register_username")
            password = st.text_input("🔒 密码", type="password", key="register_password")
            confirm_password = st.text_input("🔁 确认密码", type="password", key="confirm_password")
            
            if st.button("📝 立即注册", type="primary"):
                if password != confirm_password:
                    st.error("密码不一致")
                else:
                    # 添加密码复杂度检查
                    is_complex, msg = check_password_complexity(password)
                    if not is_complex:
                        st.error(msg)
                        log_operation(username, "ERROR", "用户注册", f"密码复杂度不足: {msg}")
                        return
                    
                    existing_user = session.query(User).filter_by(username=username).first()
                    if existing_user:
                        st.error("用户名已存在")
                    else:
                        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                        new_user = User(username=username, password=hashed_password.decode('utf-8'),
                                        last_login_time=datetime.now())
                        session.add(new_user)
                        session.commit()
                        log_operation(username, "INFO", "用户注册", f"用户 {username} 注册成功")
                        st.success("注册成功，请登录")
                        st.query_params.page = "login"
                        st.rerun()  # 新增: 注册成功后强制跳转回登录页

            st.markdown("</div>", unsafe_allow_html=True)
            
            # 底部登录引导
            st.markdown("""
            <div style='text-align: center; margin-top: 2rem; color: #666;'>
            已有账号？ 
            </div>
            """, unsafe_allow_html=True)
            
            # 修改为Streamlit原生按钮实现跳转
            if st.button("立即登录", key="go_to_login"):
                st.query_params.page = "login"
                st.rerun()

import base64
import os
import random
import re
import string
from datetime import datetime
from io import BytesIO

import bcrypt
import jwt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from sqlalchemy.orm import sessionmaker

from utils.database import engine  # 导入数据库连接

Session = sessionmaker(bind=engine)
session = Session()

from models import User  # 导入User模型
from utils.logger import log_operation  # 添加: 引入日志记录函数

# 添加登录尝试记录字典
login_attempts = {}

# 添加检查登录尝试的函数
def check_login_attempts(username, max_attempts=10, lockout_time=30):
    """
    检查用户登录尝试次数
    :param username: 用户名
    :param max_attempts: 最大尝试次数
    :param lockout_time: 锁定时间(秒)
    :return: (是否允许登录, 剩余锁定时间)
    """
    current_time = datetime.now()
    
    if username not in login_attempts:
        login_attempts[username] = {'attempts': 0, 'last_attempt': current_time}
        return True, 0
    
    user_attempts = login_attempts[username]
    
    # 如果已经超过了锁定时间，重置尝试次数
    if (current_time - user_attempts['last_attempt']).seconds > lockout_time:
        user_attempts['attempts'] = 0
    
    # 如果尝试次数已达到上限，返回剩余锁定时间
    if user_attempts['attempts'] >= max_attempts:
        remaining_lockout = lockout_time - (current_time - user_attempts['last_attempt']).seconds
        return False, max(0, remaining_lockout)
    
    return True, 0

# 添加记录登录失败的函数
def record_failed_login(username):
    """
    记录登录失败尝试
    :param username: 用户名
    """
    current_time = datetime.now()
    if username not in login_attempts:
        login_attempts[username] = {'attempts': 1, 'last_attempt': current_time}
    else:
        login_attempts[username]['attempts'] += 1
        login_attempts[username]['last_attempt'] = current_time

# 添加重置登录尝试记录的函数
def reset_login_attempts(username):
    """
    重置用户的登录尝试记录
    :param username: 用户名
    """
    if username in login_attempts:
        del login_attempts[username]

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

# 添加生成验证码的函数
def generate_captcha():
    """
    生成4位随机验证码及图片
    """
    # 生成随机验证码
    captcha_text = ''.join(random.choices(string.digits, k=4))
    
    # 创建更大尺寸的图片以提高清晰度
    width, height = 200, 80
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 使用更大更清晰的字体
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", 45)
    except:
        # 如果没有系统字体，使用默认字体但增大尺寸
        font = ImageFont.load_default()
    
    # 绘制文字，增大字体和调整位置
    for i, char in enumerate(captcha_text):
        # 随机颜色
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        # 更大的字符间距和居中位置
        x = 25 + i * 45 + random.randint(-5, 5)
        y = random.randint(10, 20)
        draw.text((x, y), char, fill=color, font=font)
    
    # 增加干扰线数量，提高安全性
    for _ in range(random.randint(8, 12)):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), width=1)
    
    # 增加干扰点数量，提高安全性
    for _ in range(random.randint(80, 120)):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # 添加轻微模糊效果
    image = image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.2, 0.8)))
    
    # 将图片转换为base64编码
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return captcha_text, img_str

def login(session, st):
    # 统一登录和注册页面的样式设计
    st.markdown("""
    <style>
    .auth-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .stTextInput>div>div>input {
        border-radius: 8px !important;
        padding: 12px !important;
        border: 1px solid #ddd !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px !important;
        padding: 12px !important;
        background: linear-gradient(135deg, #4CAF50 30%, #8BC34A 70%) !important;
        transition: all 0.3s ease !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(76, 175, 80, 0.4) !important;
    }
    .captcha-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 15px;
        margin: 20px 0;
        padding: 15px;
        background: #f9f9f9;
        border-radius: 10px;
        border: 1px dashed #4CAF50;
    }
    .captcha-header {
        font-weight: 500;
        color: #333;
        margin: 0;
    }
    .captcha-content {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .captcha-image {
        border: 2px solid #4CAF50;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .captcha-image:hover {
        transform: scale(1.05);
    }
    .refresh-captcha {
        cursor: pointer;
        background: linear-gradient(135deg, #2196F3, #21CBF3);
        border: none;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 18px;
        box-shadow: 0 2px 5px rgba(33, 150, 243, 0.4);
        transition: all 0.3s ease;
    }
    .refresh-captcha:hover {
        transform: rotate(90deg);
        box-shadow: 0 4px 8px rgba(33, 150, 243, 0.6);
    }
    .auth-header {
        text-align: center; 
        color: #2E7D32; 
        margin-bottom: 2rem;
    }
    .auth-footer {
        text-align: center; 
        margin-top: 2rem; 
        color: #666;
    }
    .auth-link-button {
        background: none !important;
        border: none !important;
        color: #4CAF50 !important;
        cursor: pointer !important;
        text-decoration: underline !important;
        padding: 0 !important;
        margin: 0 !important;
        font-size: inherit !important;
    }
    .auth-link-button:hover {
        color: #388E3C !important;
        transform: none !important;
        box-shadow: none !important;
    }
    .form-divider {
        text-align: center;
        margin: 20px 0;
        position: relative;
        color: #777;
    }
    .form-divider::before {
        content: "";
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 1px;
        background: #ddd;
        z-index: 1;
    }
    .form-divider span {
        background: white;
        position: relative;
        z-index: 2;
        padding: 0 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,3,1])
        with col2:
            st.markdown("""
            <h2 class="auth-header">
            🚜 智能农场管理系统
            </h2>
            <h3 class="auth-header">用户登录</h3>
            """, unsafe_allow_html=True)
            
            # 登录表单
            username = st.text_input("👤 用户名", key="login_username")
            password = st.text_input("🔒 密码", type="password", key="login_password")
            
            # 添加验证码功能
            if 'login_captcha' not in st.session_state or 'login_captcha_image' not in st.session_state:
                captcha_text, captcha_image = generate_captcha()
                st.session_state['login_captcha'] = captcha_text
                st.session_state['login_captcha_image'] = captcha_image
            
            # 显示验证码
            st.markdown('<p class="captcha-header">🔐 安全验证</p>', unsafe_allow_html=True)
            st.markdown('<div class="captcha-content">', unsafe_allow_html=True)
            
            # 创建两列布局，将验证码图片和刷新按钮放在同一行
            col_captcha_img, col_refresh_btn = st.columns([4, 1])
            with col_captcha_img:
                st.markdown(f'<img class="captcha-image" src="data:image/png;base64,{st.session_state["login_captcha_image"]}" width="200" height="80">', unsafe_allow_html=True)
            with col_refresh_btn:
                # 刷新验证码按钮
                if st.button("↻", key="refresh_login_captcha", help="点击刷新验证码", type="secondary"):
                    captcha_text, captcha_image = generate_captcha()
                    st.session_state['login_captcha'] = captcha_text
                    st.session_state['login_captcha_image'] = captcha_image
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            captcha_input = st.text_input("🔢 请输入验证码", key="login_captcha_input", max_chars=4)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("🚪 登录", type="primary"):
                # 检查登录尝试次数
                can_login, remaining_time = check_login_attempts(username)
                if not can_login:
                    st.error(f"登录尝试次数过多，请 {remaining_time} 秒后再试")
                    log_operation(username, "ERROR", "登录失败", f"因多次尝试失败被锁定，剩余锁定时间: {remaining_time}秒")
                    # 刷新验证码
                    captcha_text, captcha_image = generate_captcha()
                    st.session_state['login_captcha'] = captcha_text
                    st.session_state['login_captcha_image'] = captcha_image
                    return
                
                # 验证验证码
                if captcha_input != st.session_state['login_captcha']:
                    st.error("验证码错误")
                    record_failed_login(username)  # 记录失败尝试
                    log_operation(username, "ERROR", "登录失败", "验证码错误")
                    # 刷新验证码
                    captcha_text, captcha_image = generate_captcha()
                    st.session_state['login_captcha'] = captcha_text
                    st.session_state['login_captcha_image'] = captcha_image
                else:
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
                        st.session_state['just_logged_in'] = True  # 标记刚登录
                        user.last_login_time = datetime.now()
                        session.commit()
                        reset_login_attempts(username)  # 重置登录尝试记录
                        log_operation(username, "INFO", "用户登录", f"用户 {username} 成功登录")
                        # 登录成功后刷新验证码
                        if 'login_captcha' in st.session_state:
                            del st.session_state['login_captcha']
                        if 'login_captcha_image' in st.session_state:
                            del st.session_state['login_captcha_image']
                        st.query_params.page = "integrated_dashboard"
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")  # 新增错误提示
                        record_failed_login(username)  # 记录失败尝试
                        log_operation(username, "ERROR", "登录失败", "用户名或密码错误")
                        # 刷新验证码
                        captcha_text, captcha_image = generate_captcha()
                        st.session_state['login_captcha'] = captcha_text
                        st.session_state['login_captcha_image'] = captcha_image

            st.markdown("</div>", unsafe_allow_html=True)
            
            # 底部注册引导
            st.markdown("""
            <div class="form-divider">
                <span>还没有账号？</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 修改为Streamlit原生按钮实现跳转
            col_center1, col_center2, col_center3 = st.columns([1,2,1])
            with col_center2:
                if st.button("立即注册", key="go_to_register", help="点击前往注册页面", use_container_width=True):
                    # 刷新验证码
                    if 'login_captcha' in st.session_state:
                        del st.session_state['login_captcha']
                    if 'login_captcha_image' in st.session_state:
                        del st.session_state['login_captcha_image']
                    st.query_params.page = "register"
                    st.rerun()

def register(session, st):
    # 统一注册页面样式设计（与登录页面保持一致）
    st.markdown("""
    <style>
    .auth-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .stTextInput>div>div>input {
        border-radius: 8px !important;
        padding: 12px !important;
        border: 1px solid #ddd !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px !important;
        padding: 12px !important;
        background: linear-gradient(135deg, #4CAF50 30%, #8BC34A 70%) !important;
        transition: all 0.3s ease !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(76, 175, 80, 0.4) !important;
    }
    .captcha-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 15px;
        margin: 20px 0;
        padding: 15px;
        background: #f9f9f9;
        border-radius: 10px;
        border: 1px dashed #4CAF50;
    }
    .captcha-header {
        font-weight: 500;
        color: #333;
        margin: 0;
    }
    .captcha-content {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .captcha-image {
        border: 2px solid #4CAF50;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .captcha-image:hover {
        transform: scale(1.05);
    }
    .refresh-captcha {
        cursor: pointer;
        background: linear-gradient(135deg, #2196F3, #21CBF3);
        border: none;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 18px;
        box-shadow: 0 2px 5px rgba(33, 150, 243, 0.4);
        transition: all 0.3s ease;
    }
    .refresh-captcha:hover {
        transform: rotate(90deg);
        box-shadow: 0 4px 8px rgba(33, 150, 243, 0.6);
    }
    .auth-header {
        text-align: center; 
        color: #2E7D32; 
        margin-bottom: 2rem;
    }
    .auth-footer {
        text-align: center; 
        margin-top: 2rem; 
        color: #666;
    }
    .auth-link-button {
        background: none !important;
        border: none !important;
        color: #4CAF50 !important;
        cursor: pointer !important;
        text-decoration: underline !important;
        padding: 0 !important;
        margin: 0 !important;
        font-size: inherit !important;
    }
    .auth-link-button:hover {
        color: #388E3C !important;
        transform: none !important;
        box-shadow: none !important;
    }
    .form-divider {
        text-align: center;
        margin: 20px 0;
        position: relative;
        color: #777;
    }
    .form-divider::before {
        content: "";
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 1px;
        background: #ddd;
        z-index: 1;
    }
    .form-divider span {
        background: white;
        position: relative;
        z-index: 2;
        padding: 0 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,3,1])
        with col2:
            st.markdown("""
            <h2 class="auth-header">
            🚜 智能农场管理系统
            </h2>
            <h3 class="auth-header">新用户注册</h3>
            """, unsafe_allow_html=True)
            
            # 注册表单
            username = st.text_input("👤 用户名", key="register_username")
            password = st.text_input("🔒 密码", type="password", key="register_password")
            confirm_password = st.text_input("🔁 确认密码", type="password", key="confirm_password")
            
            # 添加身份选择
            user_type = st.radio("身份类型", ["👨🌾 普通用户", "👨💼 管理员"], horizontal=True)
            
            # 添加验证码功能
            if 'register_captcha' not in st.session_state or 'register_captcha_image' not in st.session_state:
                captcha_text, captcha_image = generate_captcha()
                st.session_state['register_captcha'] = captcha_text
                st.session_state['register_captcha_image'] = captcha_image
            
            # 显示验证码
            st.markdown('<p class="captcha-header">🔐 安全验证</p>', unsafe_allow_html=True)
            st.markdown('<div class="captcha-content">', unsafe_allow_html=True)
            
            # 创建两列布局，将验证码图片和刷新按钮放在同一行
            col_captcha_img, col_refresh_btn = st.columns([4, 1])
            with col_captcha_img:
                st.markdown(f'<img class="captcha-image" src="data:image/png;base64,{st.session_state["register_captcha_image"]}" width="200" height="80">', unsafe_allow_html=True)
            with col_refresh_btn:
                # 刷新验证码按钮
                if st.button("↻", key="refresh_register_captcha", help="点击刷新验证码", type="secondary"):
                    captcha_text, captcha_image = generate_captcha()
                    st.session_state['register_captcha'] = captcha_text
                    st.session_state['register_captcha_image'] = captcha_image
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            captcha_input = st.text_input("🔢 请输入验证码", key="register_captcha_input", max_chars=4)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("📝 立即注册", type="primary"):
                # 验证验证码
                if captcha_input != st.session_state['register_captcha']:
                    st.error("验证码错误")
                    log_operation(username, "ERROR", "注册失败", "验证码错误")
                    # 刷新验证码
                    captcha_text, captcha_image = generate_captcha()
                    st.session_state['register_captcha'] = captcha_text
                    st.session_state['register_captcha_image'] = captcha_image
                elif password != confirm_password:
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
                        # 根据用户选择设置角色
                        # 修改逻辑：如果用户选择管理员，则标记为待审批状态
                        if user_type == "👨💼 管理员":
                            new_user = User(username=username, 
                                          password=hashed_password.decode('utf-8'),
                                          last_login_time=datetime.now(), 
                                          role='user',  # 默认为普通用户
                                          admin_request=True,  # 标记为管理员申请
                                          admin_request_time=datetime.now())
                            session.add(new_user)
                            session.commit()
                            log_operation(username, "INFO", "用户注册", f"用户 {username} 申请注册为管理员，等待审批")
                            # 注册成功后刷新验证码
                            if 'register_captcha' in st.session_state:
                                del st.session_state['register_captcha']
                            if 'register_captcha_image' in st.session_state:
                                del st.session_state['register_captcha_image']
                            st.success("注册申请已提交，请等待管理员审批。审批通过前将以普通用户身份登录。")
                        else:
                            new_user = User(username=username, 
                                          password=hashed_password.decode('utf-8'),
                                          last_login_time=datetime.now(), 
                                          role='user')
                            session.add(new_user)
                            session.commit()
                            log_operation(username, "INFO", "用户注册", f"用户 {username} 注册成功，角色: user")
                            # 注册成功后刷新验证码
                            if 'register_captcha' in st.session_state:
                                del st.session_state['register_captcha']
                            if 'register_captcha_image' in st.session_state:
                                del st.session_state['register_captcha_image']
                            st.success("注册成功，请登录")
                        st.query_params.page = "login"
                        st.rerun()  # 新增: 注册成功后强制跳转回登录页

            st.markdown("</div>", unsafe_allow_html=True)
            
            # 底部登录引导
            st.markdown("""
            <div class="form-divider">
                <span>已有账号？</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 修改为Streamlit原生按钮实现跳转
            col_center1, col_center2, col_center3 = st.columns([1,2,1])
            with col_center2:
                if st.button("立即登录", key="go_to_login", help="点击前往登录页面", use_container_width=True):
                    # 刷新验证码
                    if 'register_captcha' in st.session_state:
                        del st.session_state['register_captcha']
                    if 'register_captcha_image' in st.session_state:
                        del st.session_state['register_captcha_image']
                    st.query_params.page = "login"
                    st.rerun()
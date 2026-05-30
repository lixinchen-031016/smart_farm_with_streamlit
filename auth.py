"""用户认证模块

提供用户登录、注册、密码管理和验证码功能，确保系统的安全性和用户身份验证。

主要功能：
- 用户登录与身份验证
- 新用户注册
- 密码强度评估与检查
- 登录尝试限制与锁定
- 验证码生成与验证
"""

import base64
import os
import random
import re
import string
from datetime import datetime
from io import BytesIO
from typing import Tuple, List, Optional

import bcrypt
import jwt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from sqlalchemy.orm import sessionmaker

from utils.captcha_utils import (  # 导入验证码工具
    generate_captcha,
    refresh_captcha,
    verify_captcha,
    create_captcha_widget
)
from utils.database import engine  # 导入数据库连接
from utils.ui_styles import render_login_styles, render_register_styles  # 导入公共 CSS 样式

Session = sessionmaker(bind=engine)
session = Session()

from models import User  # 导入User模型
from utils.logger import log_operation  # 添加: 引入日志记录函数

# 添加登录尝试记录字典
login_attempts = {}


# 添加检查登录尝试的函数
def check_login_attempts(username, max_attempts=10, lockout_time=30):
    """检查用户登录尝试次数

    检查用户的登录尝试次数，防止暴力破解。当尝试次数超过上限时，会暂时锁定用户。

    Args:
        username (str): 用户名
        max_attempts (int, optional): 最大尝试次数，默认为10
        lockout_time (int, optional): 锁定时间(秒)，默认为30

    Returns:
        Tuple[bool, int]: (是否允许登录, 剩余锁定时间)

    Examples:
        >>> can_login, remaining_time = check_login_attempts("admin")
        >>> print(f"是否允许登录: {can_login}, 剩余锁定时间: {remaining_time}秒")
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
    """记录登录失败尝试

    记录用户的登录失败尝试，用于后续的登录尝试限制。

    Args:
        username (str): 用户名

    Examples:
        >>> record_failed_login("admin")
    """
    current_time = datetime.now()
    if username not in login_attempts:
        login_attempts[username] = {'attempts': 1, 'last_attempt': current_time}
    else:
        login_attempts[username]['attempts'] += 1
        login_attempts[username]['last_attempt'] = current_time


# 添加重置登录尝试记录的函数
def reset_login_attempts(username):
    """重置用户的登录尝试记录

    当用户成功登录后，重置其登录尝试记录。

    Args:
        username (str): 用户名

    Examples:
        >>> reset_login_attempts("admin")
    """
    if username in login_attempts:
        del login_attempts[username]


def evaluate_password_strength(password):
    """评估密码强度并返回详细信息

    评估密码的强度，包括长度、字符类型、复杂性等因素，并返回详细的反馈信息。

    Args:
        password (str): 要评估的密码

    Returns:
        Tuple[str, int, List[str]]: (强度等级, 分数, 详细反馈)
            - 强度等级: low(红色), medium(黄色), high(绿色)
            - 分数: 0-100之间的分数
            - 详细反馈: 包含密码强度评估的详细信息列表

    Examples:
        >>> strength, score, feedback = evaluate_password_strength("StrongPass123!")
        >>> print(f"密码强度: {strength}, 分数: {score}")
        >>> for item in feedback:
        ...     print(f"- {item}")
    """
    if not password:
        return "low", 0, []

    score = 0
    feedback = []

    # 长度检查
    if len(password) >= 12:
        score += 25
        feedback.append("✅ 密码长度充足 (≥12位)")
    elif len(password) >= 8:
        score += 15
        feedback.append("⚠️ 密码长度一般 (8-11位)")
    else:
        feedback.append("❌ 密码长度不足 (<8位)")

    # 字符类型检查
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\/_+=~-]', password))

    char_types = sum([has_lower, has_upper, has_digit, has_special])

    if char_types >= 3:
        score += 30
        feedback.append("✅ 包含多种字符类型")
    elif char_types == 2:
        score += 15
        feedback.append("⚠️ 字符类型较少")
    else:
        feedback.append("❌ 字符类型单一")

    # 复杂性加分
    if has_lower and has_upper:
        score += 15
    if has_digit:
        score += 10
    if has_special:
        score += 20

    # 常见模式扣分
    if re.search(r'(.)\1{2,}', password):  # 连续重复字符
        score -= 10
        feedback.append("❌ 存在连续重复字符")

    if re.search(r'(012|123|234|345|456|567|678|789|890)', password):  # 连续数字
        score -= 10
        feedback.append("❌ 存在连续数字序列")

    if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk)', password.lower()):  # 连续字母
        score -= 10
        feedback.append("❌ 存在连续字母序列")

    # 确定强度等级
    if score >= 70:
        strength = "high"
    elif score >= 40:
        strength = "medium"
    else:
        strength = "low"

    return strength, max(0, min(100, score)), feedback


def check_password_complexity(password):
    """检查密码复杂度

    检查密码是否满足复杂度要求，包括长度、字符类型等。

    Args:
        password (str): 要检查的密码

    Returns:
        Tuple[bool, str]: (是否满足复杂度要求, 错误信息)
            - 如果满足要求，返回 (True, "")
            - 如果不满足要求，返回 (False, 错误信息)

    Examples:
        >>> is_complex, msg = check_password_complexity("StrongPass123!")
        >>> print(f"密码是否复杂: {is_complex}, 消息: {msg}")
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
    """生成4位随机验证码及图片

    生成包含4位数字的验证码图片，用于登录和注册时的安全验证。

    Returns:
        Tuple[str, str]: (验证码文本, 验证码图片的base64编码)

    Examples:
        >>> captcha_text, captcha_image = generate_captcha()
        >>> print(f"验证码: {captcha_text}")
        >>> # captcha_image 可以直接用于HTML中的img标签
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
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                  width=1)

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
    """用户登录函数

    显示登录表单，处理用户登录请求，包括验证码验证、密码验证和登录尝试限制。

    Args:
        session (sqlalchemy.orm.Session): 数据库会话
        st (streamlit): Streamlit 实例

    Examples:
        >>> # 在 Streamlit 应用中使用
        >>> login(session, st)
    """
    # 使用公共 CSS 样式模块 (TD-001 优化)
    render_login_styles()

    with st.container():
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.markdown("""
            <h2 class="auth-header">
            🚜 智慧大棚数据管理系统
            </h2>
            <h3 class="auth-header">用户登录</h3>
            """, unsafe_allow_html=True)

            # 登录表单
            username = st.text_input("👤 用户名", key="login_username")
            password = st.text_input("🔒 密码", type="password", key="login_password")

            # 使用验证码工具模块 (TD-002 优化)
            st.markdown('<p class="captcha-header">🔐 安全验证</p>', unsafe_allow_html=True)
            create_captcha_widget('login_captcha', show_refresh_button=True)
            captcha_input = st.text_input("🔢 请输入验证码", key="login_captcha_input", max_chars=4)

            if st.button("🚪 登录", type="primary"):
                # 检查登录尝试次数
                can_login, remaining_time = check_login_attempts(username)
                if not can_login:
                    st.error(f"登录尝试次数过多，请 {remaining_time} 秒后再试")
                    log_operation(username, "ERROR", "登录失败",
                                  f"因多次尝试失败被锁定，剩余锁定时间: {remaining_time}秒")
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
                            'exp': datetime.now().timestamp() + 2400
                        }
                        token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
                        st.query_params.jwt_token = token  # 新API设置参数

                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.session_state['role'] = user.role
                        st.session_state['just_logged_in'] = True  # 标记刚登录
                        # 初始化菜单选择状态
                        st.session_state.menu_selection = "综合监控仪表板"
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
            col_center1, col_center2, col_center3 = st.columns([1, 2, 1])
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
    """用户注册函数

    显示注册表单，处理用户注册请求，包括密码强度评估、验证码验证和用户创建。

    Args:
        session (sqlalchemy.orm.Session): 数据库会话
        st (streamlit): Streamlit 实例

    Examples:
        >>> # 在 Streamlit 应用中使用
        >>> register(session, st)
    """
    # 使用公共 CSS 样式模块 (TD-001 优化)
    render_register_styles()

    with st.container():
        col1, col2, col3 = st.columns([1, 3, 1])
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

            # 实时显示密码强度
            if password:
                strength, score, feedback = evaluate_password_strength(password)

                # 显示强度指示条
                strength_labels = {"low": "弱", "medium": "中等", "high": "强"}
                strength_colors = {"low": "red", "medium": "yellow", "high": "green"}

                st.markdown(f'''
                <div class="password-strength-container">
                    <div class="strength-label strength-{strength}-text">密码强度: {strength_labels[strength]} ({score}/100)</div>
                    <div class="strength-meter">
                        <div class="strength-fill strength-{strength}"></div>
                    </div>
                    <div class="feedback-list">
                        {''.join([f'<div class="feedback-item">{item}</div>' for item in feedback])}
                    </div>
                </div>
                ''', unsafe_allow_html=True)

            confirm_password = st.text_input("🔁 确认密码", type="password", key="confirm_password")

            # 添加身份选择
            user_type = st.radio("身份类型", ["👨🌾 普通用户", "👨💼 管理员"], horizontal=True)

            # 使用验证码工具模块 (TD-002 优化)
            st.markdown('<p class="captcha-header">🔐 安全验证</p>', unsafe_allow_html=True)
            create_captcha_widget('register_captcha', show_refresh_button=True)
            captcha_input = st.text_input("🔢 请输入验证码", key="register_captcha_input", max_chars=4)

            if st.button("📝 立即注册", type="primary"):
                # 验证验证码 (TD-002 优化)
                if not verify_captcha(captcha_input, 'register_captcha'):
                    st.error("验证码错误")
                    log_operation(username, "ERROR", "注册失败", "验证码错误")
                    refresh_captcha('register_captcha')  # 自动刷新验证码
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
            col_center1, col_center2, col_center3 = st.columns([1, 2, 1])
            with col_center2:
                if st.button("立即登录", key="go_to_login", help="点击前往登录页面", use_container_width=True):
                    # 刷新验证码
                    if 'register_captcha' in st.session_state:
                        del st.session_state['register_captcha']
                    if 'register_captcha_image' in st.session_state:
                        del st.session_state['register_captcha_image']
                    st.query_params.page = "login"
                    st.rerun()

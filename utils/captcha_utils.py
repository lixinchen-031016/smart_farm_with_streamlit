"""
验证码工具模块

提供验证码生成、会话管理和验证功能
用于消除 auth.py 中登录和注册页面的验证码重复代码
"""

import base64
import random
import string
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def generate_captcha():
    """生成 4 位随机验证码及图片

    生成包含4位数字的验证码图片，添加干扰线和干扰点，提高安全性。

    Returns:
        tuple: (验证码文本，Base64 编码的图片字符串)

    Examples:
        >>> captcha_text, captcha_image = generate_captcha()
        >>> print(len(captcha_text))
        4
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
        draw.line([(x1, y1), (x2, y2)], 
                  fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                  width=1)

    # 增加干扰点数量，提高安全性
    for _ in range(random.randint(80, 120)):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

    # 添加轻微模糊效果
    image = image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.2, 0.8)))

    # 将图片转换为 base64 编码
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return captcha_text, img_str


def initialize_captcha_session(session_key='captcha'):
    """初始化验证码会话状态

    初始化验证码会话状态，生成新的验证码并存储到会话中。

    Args:
        session_key (str, optional): 会话状态的键名前缀，默认为'captcha'
                                    实际会存储 {session_key} 和 {session_key}_image

    Returns:
        tuple: (验证码文本，Base64 编码的图片字符串)

    Examples:
        >>> # 登录页面
        >>> captcha_text, captcha_image = initialize_captcha_session('login_captcha')
        >>> # 注册页面
        >>> captcha_text, captcha_image = initialize_captcha_session('register_captcha')
    """
    if session_key not in st.session_state or f'{session_key}_image' not in st.session_state:
        captcha_text, captcha_image = generate_captcha()
        st.session_state[session_key] = captcha_text
        st.session_state[f'{session_key}_image'] = captcha_image
        return captcha_text, captcha_image
    
    return st.session_state[session_key], st.session_state[f'{session_key}_image']


def refresh_captcha(session_key='captcha'):
    """刷新验证码（生成新的验证码并更新会话状态）

    生成新的验证码并更新会话状态中的验证码信息。

    Args:
        session_key (str, optional): 会话状态的键名前缀，默认为'captcha'

    Returns:
        tuple: (新的验证码文本，新的 Base64 编码图片字符串)

    Examples:
        >>> new_captcha_text, new_captcha_image = refresh_captcha('login_captcha')
    """
    captcha_text, captcha_image = generate_captcha()
    st.session_state[session_key] = captcha_text
    st.session_state[f'{session_key}_image'] = captcha_image
    return captcha_text, captcha_image


def verify_captcha(user_input, session_key='captcha'):
    """验证用户输入的验证码是否正确

    验证用户输入的验证码是否与会话中存储的验证码匹配。

    Args:
        user_input: 用户输入的验证码字符串
        session_key (str, optional): 会话状态的键名前缀，默认为'captcha'

    Returns:
        bool: 验证码是否正确

    Examples:
        >>> if verify_captcha(user_input, 'login_captcha'):
        ...     st.success("验证码正确")
        ... else:
        ...     st.error("验证码错误")
    """
    if session_key not in st.session_state:
        return False
    
    expected_captcha = st.session_state[session_key]
    
    # 不区分大小写比较（虽然数字验证码没有大小写区别，但保持通用性）
    return str(user_input).strip().lower() == str(expected_captcha).strip().lower()


def create_captcha_widget(session_key='captcha', show_refresh_button=True):
    """创建验证码 UI 组件（包含图片和可选的刷新按钮）

    创建验证码UI组件，显示验证码图片和可选的刷新按钮。

    Args:
        session_key (str, optional): 会话状态的键名前缀，默认为'captcha'
        show_refresh_button (bool, optional): 是否显示刷新按钮，默认为True

    Returns:
        None: 无返回值，直接在页面上显示内容

    Examples:
        >>> # 在登录页面使用
        >>> create_captcha_widget('login_captcha')
        >>> # 在注册页面使用（带刷新按钮）
        >>> create_captcha_widget('register_captcha', show_refresh_button=True)
    """
    import streamlit as st
    
    # 初始化验证码
    captcha_text, captcha_image = initialize_captcha_session(session_key)
    
    # 创建验证码显示容器
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 显示验证码图片
            st.markdown(
                f'<img src="data:image/png;base64,{captcha_image}" class="captcha-image" />',
                unsafe_allow_html=True
            )
        
        if show_refresh_button:
            with col2:
                # 刷新按钮
                if st.button("🔄", key=f'refresh_{session_key}', help="刷新验证码"):
                    refresh_captcha(session_key)
                    st.rerun()


def validate_captcha_input(user_input, session_key='captcha', field_name="验证码"):
    """验证验证码输入并提供友好的错误提示

    验证用户输入的验证码是否正确，并在验证失败时显示友好的错误提示。

    Args:
        user_input: 用户输入的验证码
        session_key (str, optional): 会话状态的键名前缀，默认为'captcha'
        field_name (str, optional): 字段名称，用于错误提示，默认为"验证码"

    Returns:
        bool: 验证是否通过

    Examples:
        >>> if not validate_captcha_input(captcha_input, 'login_captcha', "登录验证码"):
        ...     return False  # 验证失败，中断后续操作
    """
    import streamlit as st
    
    if not user_input or not user_input.strip():
        st.error(f"请输入{field_name}")
        return False
    
    if not verify_captcha(user_input, session_key):
        st.error(f"{field_name}错误，请重新输入")
        refresh_captcha(session_key)  # 验证失败后自动刷新验证码
        return False
    
    return True

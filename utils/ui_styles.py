"""
认证页面公共 CSS 样式模块

提取自 auth.py，用于消除登录和注册页面的 CSS 重复代码
包含：基础样式、验证码样式、表单样式、密码强度样式
"""


# 认证页面基础 CSS 样式（登录和注册共用）
AUTH_BASE_CSS = """
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
"""

# 注册页面专属 CSS 样式（密码强度指示条）
PASSWORD_STRENGTH_CSS = """
<style>
/* 密码强度指示条样式 */
.password-strength-container {
    margin: 10px 0 20px 0;
    padding: 15px;
    border-radius: 10px;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
}
.strength-meter {
    height: 12px;
    border-radius: 6px;
    background: #e9ecef;
    overflow: hidden;
    margin-bottom: 12px;
    position: relative;
}
.strength-fill {
    height: 100%;
    border-radius: 6px;
    transition: all 0.3s ease;
    width: 0%;
}
.strength-low { background: #dc3545; width: 33%; }
.strength-medium { background: #ffc107; width: 66%; }
.strength-high { background: #28a745; width: 100%; }
.strength-label {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 8px;
    text-align: center;
}
.strength-low-text { color: #dc3545; }
.strength-medium-text { color: #ffc107; }
.strength-high-text { color: #28a745; }
.feedback-list {
    font-size: 12px;
    line-height: 1.4;
    color: #666;
}
.feedback-item {
    margin: 3px 0;
    padding-left: 15px;
    position: relative;
}
.feedback-item::before {
    content: "•";
    position: absolute;
    left: 0;
    color: #666;
}
</style>
"""


def get_login_css():
    """
    获取登录页面的完整 CSS
    
    Returns:
        str: 完整的 CSS 样式字符串
    """
    return AUTH_BASE_CSS


def get_register_css():
    """
    获取注册页面的完整 CSS（包含密码强度样式）
    
    Returns:
        str: 完整的 CSS 样式字符串
    """
    return AUTH_BASE_CSS + PASSWORD_STRENGTH_CSS


def render_login_styles():
    """
    在 Streamlit 页面中渲染登录页面样式
    
    使用示例:
        from utils.ui_styles import render_login_styles
        render_login_styles()
    """
    import streamlit as st
    st.markdown(AUTH_BASE_CSS, unsafe_allow_html=True)


def render_register_styles():
    """
    在 Streamlit 页面中渲染注册页面样式
    
    使用示例:
        from utils.ui_styles import render_register_styles
        render_register_styles()
    """
    import streamlit as st
    st.markdown(AUTH_BASE_CSS + PASSWORD_STRENGTH_CSS, unsafe_allow_html=True)

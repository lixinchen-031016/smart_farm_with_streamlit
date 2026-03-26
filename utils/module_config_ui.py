"""
模块配置管理UI界面
提供图形界面用于管理模块的启用/禁用状态
"""

import streamlit as st

from utils.logger import log_operation
from utils.module_manager import get_module_manager


def show_module_config_ui(username: str, is_admin: bool = False):
    """显示模块配置管理界面"""
    if not is_admin:
        st.error("仅管理员可以访问模块配置管理")
        return

    # 添加返回主界面按钮
    if st.button("⬅️ 返回主界面"):
        # 根据用户角色或上一个页面动态设置返回链接
        # 默认返回数据预览页面
        return_page = "data_preview"

        # 如果是管理员，优先返回用户管理页面
        if is_admin:
            return_page = "user_management"

        # 如果 session_state 中有上一个页面信息，则返回上一个页面
        if 'previous_page' in st.session_state:
            return_page = st.session_state['previous_page']

        st.query_params.page = return_page
        # 更新 previous_page 为当前页面，为下一次导航做准备
        st.session_state['previous_page'] = "module_config"
        st.rerun()

    st.title("🔧 模块配置管理")

    # 添加说明
    st.markdown("""
    在此页面可以管理系统中各个功能模块的启用状态。
    禁用不需要的模块可以提高系统性能并简化用户界面。
    """)

    # 获取模块管理器
    module_manager = get_module_manager()

    # 获取所有分类
    categories = module_manager.get_all_categories()

    # 创建选项卡
    tabs = st.tabs(categories)

    # 为每个分类创建一个选项卡
    for i, category in enumerate(categories):
        with tabs[i]:
            st.subheader(f"{category}模块")

            # 获取该分类下的所有模块
            modules = [m for m in module_manager.modules.values() if m.category == category]

            if not modules:
                st.info("该分类下暂无模块")
                continue

            # 为每个模块创建配置项
            for module in modules:
                with st.expander(f"{module.display_name} ({'已启用' if module.enabled else '已禁用'})",
                                 expanded=False):
                    # 显示模块信息
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**描述:** {module.description}")
                        st.markdown(f"**模块名称:** {module.name}")
                        if module.dependencies:
                            st.markdown(f"**依赖模块:** {', '.join(module.dependencies)}")
                        st.markdown(f"**权限:** {'仅管理员' if module.admin_only else '所有用户'}")

                    with col2:
                        # 启用/禁用开关
                        enabled = st.toggle(
                            "启用模块",
                            value=module.enabled,
                            key=f"toggle_{module.name}",
                            help="启用或禁用此模块"
                        )

                        # 如果状态发生变化，更新配置
                        if enabled != module.enabled:
                            if enabled:
                                if module_manager.enable_module(module.name):
                                    st.success(f"已启用模块: {module.display_name}")
                                    log_operation(username, "INFO", "模块管理",
                                                  f"启用模块: {module.name}")
                                    st.rerun()
                                else:
                                    st.error(f"启用模块失败: {module.display_name}")
                            else:
                                if module_manager.disable_module(module.name):
                                    st.success(f"已禁用模块: {module.display_name}")
                                    log_operation(username, "INFO", "模块管理",
                                                  f"禁用模块: {module.name}")
                                    st.rerun()
                                else:
                                    st.error(f"禁用模块失败: {module.display_name}（可能有其他模块依赖此模块）")
                                    # 重置开关状态
                                    st.rerun()

                        # 添加权限设置
                        admin_only = st.toggle(
                            "仅管理员可用",
                            value=module.admin_only,
                            key=f"admin_only_{module.name}",
                            help="设置模块是否仅管理员可用"
                        )

                        # 如果权限设置发生变化，更新配置
                        if admin_only != module.admin_only:
                            if module_manager.update_module(module.name, admin_only=admin_only):
                                st.success(f"已更新模块权限: {module.display_name}")
                                log_operation(username, "INFO", "模块管理",
                                              f"更新模块权限: {module.name} -> {'仅管理员' if admin_only else '所有用户'}")
                                st.rerun()
                            else:
                                st.error(f"更新模块权限失败: {module.display_name}")
                                # 重置开关状态
                                st.rerun()

    # 添加模块状态概览
    st.subheader("📊 模块状态概览")

    # 统计信息
    all_modules = list(module_manager.modules.values())
    enabled_modules = [m for m in all_modules if m.enabled]
    disabled_modules = [m for m in all_modules if not m.enabled]
    admin_only_modules = [m for m in all_modules if m.admin_only]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总模块数", len(all_modules))
    col2.metric("已启用", len(enabled_modules))
    col3.metric("已禁用", len(disabled_modules))
    col4.metric("管理员专用", len(admin_only_modules))

    # 显示模块列表表格
    st.subheader("📋 模块详细列表")

    # 准备表格数据
    table_data = []
    for module in all_modules:
        table_data.append({
            "模块名称": module.display_name,
            "分类": module.category,
            "状态": "✅ 已启用" if module.enabled else "❌ 已禁用",
            "权限": "管理员" if module.admin_only else "所有用户",
            "依赖": ", ".join(module.dependencies) if module.dependencies else "无"
        })

    # 显示表格
    st.dataframe(table_data, use_container_width=True)

    # 添加重置配置按钮
    st.subheader("🔄 配置管理")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存配置"):
            module_manager.save_config()
            st.success("配置已保存")
            log_operation(username, "INFO", "模块管理", "手动保存模块配置")

    with col2:
        if st.button("🔄 恢复默认配置"):
            # 这里我们重新加载默认配置
            module_manager._load_default_modules()
            module_manager.save_config()
            st.success("已恢复默认配置")
            log_operation(username, "INFO", "模块管理", "恢复默认模块配置")
            st.rerun()


def get_enabled_modules_for_sidebar(is_admin: bool = False) -> list:
    """
    获取侧边栏应显示的启用模块
    返回格式: [(display_name, icon), ...]
    """
    module_manager = get_module_manager()
    enabled_modules = module_manager.get_enabled_modules_for_user(is_admin)

    # 按照预定义的顺序排序
    module_order = [
        "dashboard", "data_preview", "data_overview", "data_cleaning", "data_analysis",
        "data_visualization", "advanced_analysis", "ai_insights", "history_report_viewer",
        "data_prediction",
        "machine_learning", "sync_manager", "decision_engine",
        "user_management", "system_monitoring", "log_viewer",
        "data_backup", "data_restore", "instruction_manual", "debug_info"
    ]

    # 按顺序排列启用的模块
    ordered_modules = []
    module_dict = {m.name: m for m in enabled_modules}

    for module_name in module_order:
        if module_name in module_dict:
            module = module_dict[module_name]
            ordered_modules.append((module.display_name, module.icon))

    return ordered_modules


def is_module_enabled(module_name: str) -> bool:
    """检查指定模块是否启用"""
    module_manager = get_module_manager()
    return module_manager.is_enabled(module_name)

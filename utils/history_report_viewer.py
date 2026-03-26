"""历史报告查看器

用于查看和管理历史 AI 洞察和数据预测生成的 Markdown 报告文件。
支持按时间排序、搜索、预览和删除等功能。
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import streamlit as st


class HistoryReportViewer:
    """历史报告查看器类
    
    用于浏览、搜索和管理 AI 洞察和数据预测的历史 Markdown 报告。
    支持分类查看、时间排序、关键词搜索等功能。
    """
    
    def __init__(self):
        """初始化历史报告查看器"""
        # 获取项目根目录
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        # AI 洞察导出目录
        self.ai_insights_dir = os.path.join(self.base_dir, 'ai_insights_exports')
        # 数据预测导出目录（假设有单独的目录）
        self.predictions_dir = os.path.join(self.base_dir, 'predictions_exports')
        
    def get_md_files(self, directory: str) -> List[Dict]:
        """获取指定目录下的所有 Markdown 文件
        
        Args:
            directory (str): 要扫描的目录路径
            
        Returns:
            List[Dict]: 文件信息列表，每个元素包含文件名、路径、创建时间等信息
        """
        if not os.path.exists(directory):
            return []
        
        files = []
        for filename in os.listdir(directory):
            if filename.endswith('.md'):
                filepath = os.path.join(directory, filename)
                try:
                    # 从文件名提取时间戳
                    timestamp = self._extract_timestamp_from_filename(filename)
                    
                    # 读取文件前几行获取标题
                    title = self._extract_title(filepath)
                    
                    # 获取文件大小
                    file_size = os.path.getsize(filepath)
                    
                    files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'timestamp': timestamp,
                        'title': title,
                        'size': file_size,
                        'size_formatted': self._format_file_size(file_size)
                    })
                except Exception as e:
                    st.error(f"读取文件 {filename} 失败：{str(e)}")
        
        # 按时间戳降序排序（最新的在前）
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        return files
    
    def _extract_timestamp_from_filename(self, filename: str) -> datetime:
        """从文件名中提取时间戳
        
        Args:
            filename (str): 文件名
            
        Returns:
            datetime: 提取的时间戳，如果提取失败则返回当前时间
        """
        try:
            # 支持多种命名格式
            # 格式 1: AI_Insights_20260324_232730.md
            match = re.search(r'(\d{8}_\d{6})', filename)
            if match:
                time_str = match.group(1)
                return datetime.strptime(time_str, '%Y%m%d_%H%M%S')
            
            # 格式 2: prediction_2026-03-24_23-27-30.md
            match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
            if match:
                time_str = match.group(1)
                return datetime.strptime(time_str, '%Y-%m-%d_%H-%M-%S')
            
            # 格式 3: report_20260324.md
            match = re.search(r'(\d{8})', filename)
            if match:
                time_str = match.group(1)
                return datetime.strptime(time_str, '%Y%m%d')
                
        except Exception:
            pass
        
        # 如果无法提取，使用文件修改时间
        try:
            filepath = os.path.join(
                self.ai_insights_dir if 'AI_Insights' in filename else self.predictions_dir,
                filename
            )
            mtime = os.path.getmtime(filepath)
            return datetime.fromtimestamp(mtime)
        except Exception:
            return datetime.now()
    
    def _extract_title(self, filepath: str) -> str:
        """从 Markdown 文件中提取标题
        
        Args:
            filepath (str): 文件路径
            
        Returns:
            str: 提取的标题，如果提取失败则返回文件名
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # 读取前 10 行查找标题
                for _ in range(10):
                    line = f.readline()
                    if line.startswith('# '):
                        return line[2:].strip()
                return os.path.basename(filepath)
        except Exception:
            return os.path.basename(filepath)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小
        
        Args:
            size_bytes (int): 文件大小（字节）
            
        Returns:
            str: 格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def read_file_content(self, filepath: str, max_lines: Optional[int] = None) -> str:
        """读取文件内容
        
        Args:
            filepath (str): 文件路径
            max_lines (int, optional): 最大读取行数，None 表示读取全部
            
        Returns:
            str: 文件内容
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if max_lines is None:
                    return f.read()
                else:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    return ''.join(lines)
        except Exception as e:
            return f"读取文件失败：{str(e)}"
    
    def search_reports(self, keyword: str, category: str = 'all') -> List[Dict]:
        """搜索报告
        
        Args:
            keyword (str): 搜索关键词
            category (str): 报告类别，'all'、'ai_insights' 或 'predictions'
            
        Returns:
            List[Dict]: 匹配的报告列表
        """
        results = []
        
        # 确定要搜索的目录
        directories = []
        if category in ['all', 'ai_insights']:
            directories.append(('ai_insights', self.ai_insights_dir))
        if category in ['all', 'predictions']:
            directories.append(('predictions', self.predictions_dir))
        
        for dir_name, directory in directories:
            files = self.get_md_files(directory)
            for file_info in files:
                # 在文件名、标题和内容中搜索
                try:
                    content = self.read_file_content(file_info['filepath'], max_lines=50)
                    if (keyword.lower() in file_info['filename'].lower() or
                        keyword.lower() in file_info['title'].lower() or
                        keyword.lower() in content.lower()):
                        
                        file_info['category'] = dir_name
                        results.append(file_info)
                except Exception:
                    continue
        
        return results
    
    def delete_report(self, filepath: str) -> bool:
        """删除报告文件
        
        Args:
            filepath (str): 文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            st.error(f"删除文件失败：{str(e)}")
            return False
    
    def get_statistics(self) -> Dict:
        """获取统计信息
        
        Returns:
            Dict: 包含各类报告数量和总大小的统计信息
        """
        ai_files = self.get_md_files(self.ai_insights_dir)
        pred_files = self.get_md_files(self.predictions_dir)
        
        total_size = sum(f['size'] for f in ai_files) + sum(f['size'] for f in pred_files)
        
        return {
            'ai_insights_count': len(ai_files),
            'predictions_count': len(pred_files),
            'total_count': len(ai_files) + len(pred_files),
            'total_size': total_size,
            'total_size_formatted': self._format_file_size(total_size)
        }


def show_history_reports_ui():
    """显示历史报告查看器 UI
    
    在 Streamlit 页面中显示历史报告查看器界面，包括：
    - 统计信息
    - 分类筛选
    - 搜索功能
    - 报告列表
    - 报告预览
    
    Returns:
        None: 无返回值，直接在页面上显示内容
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return
    
    st.title("📄 历史报告查看器")
    st.caption("查看和管理 AI 洞察与数据预测的历史报告")
    
    # 初始化查看器
    viewer = HistoryReportViewer()
    
    # 显示统计信息
    stats = viewer.get_statistics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("AI 洞察报告", stats['ai_insights_count'])
    with col2:
        st.metric("数据预测报告", stats['predictions_count'])
    with col3:
        st.metric("总占用空间", stats['total_size_formatted'])
    
    st.divider()
    
    # 搜索和筛选
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search_keyword = st.text_input("🔍 搜索关键词", placeholder="输入关键词搜索报告内容...")
    with col2:
        category = st.selectbox(
            "报告类别",
            ["全部", "AI 洞察", "数据预测"],
            help="选择要查看的报告类别"
        )
    with col3:
        sort_order = st.selectbox(
            "排序",
            ["最新优先", "最旧优先"],
            help="按时间排序"
        )
    
    # 映射类别
    category_map = {
        "全部": "all",
        "AI 洞察": "ai_insights",
        "数据预测": "predictions"
    }
    selected_category = category_map[category]
    
    # 获取报告列表
    if search_keyword:
        reports = viewer.search_reports(search_keyword, selected_category)
        st.info(f"找到 {len(reports)} 个匹配的报告")
    else:
        reports = []
        if selected_category in ['all', 'ai_insights']:
            reports.extend(viewer.get_md_files(viewer.ai_insights_dir))
        if selected_category in ['all', 'predictions']:
            reports.extend(viewer.get_md_files(viewer.predictions_dir))
        
        # 排序
        reverse = (sort_order == "最新优先")
        reports.sort(key=lambda x: x['timestamp'], reverse=reverse)
    
    st.divider()
    
    # 显示报告列表
    if not reports:
        st.warning("没有找到任何报告")
        return
    
    # 使用标签页展示不同的报告
    tabs = st.tabs([f"报告 {i+1}" for i in range(min(len(reports), 10))])
    
    for idx, (tab, report) in enumerate(zip(tabs, reports[:10])):
        with tab:
            # 显示报告基本信息
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {report['title']}")
                st.caption(f"生成时间：{report['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            with col2:
                st.info(f"📄 {report['size_formatted']}")
            
            # 显示类别标签
            category_badge = "🤖 AI 洞察" if 'ai_insights' in report.get('category', '') or 'AI_Insights' in report['filename'] else "📊 数据预测"
            st.markdown(f"**类别**: {category_badge}")
            
            # 预览内容（前 50 行）
            st.markdown("#### 📖 内容预览")
            preview_content = viewer.read_file_content(report['filepath'], max_lines=50)
            st.markdown(preview_content)
            
            # 操作按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                # 下载按钮
                with open(report['filepath'], 'r', encoding='utf-8') as f:
                    content = f.read()
                st.download_button(
                    label="📥 下载报告",
                    data=content,
                    file_name=report['filename'],
                    mime="text/markdown",
                    use_container_width=True
                )
            with col2:
                # 在新窗口打开
                st.link_button(
                    label="🔗 在新窗口打开",
                    url=f"file://{report['filepath']}",
                    use_container_width=True
                )
            with col3:
                # 删除按钮
                if st.button("🗑️ 删除报告", use_container_width=True, key=f"delete_{idx}"):
                    if viewer.delete_report(report['filepath']):
                        st.success("删除成功！")
                        st.rerun()
                    else:
                        st.error("删除失败")
    
    # 如果报告超过 10 个，显示提示
    if len(reports) > 10:
        st.info(f"💡 仅显示前 10 个报告，共有 {len(reports)} 个报告")


def show_single_report_page(filepath: str):
    """显示单个报告的完整页面
    
    Args:
        filepath (str): 报告文件路径
        
    Returns:
        None: 无返回值，直接在页面上显示内容
    """
    viewer = HistoryReportViewer()
    
    # 读取报告信息
    filename = os.path.basename(filepath)
    title = viewer._extract_title(filepath)
    timestamp = viewer._extract_timestamp_from_filename(filename)
    file_size = os.path.getsize(filepath)
    
    st.title("📄 报告详情")
    
    # 显示基本信息
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"# {title}")
        st.caption(f"生成时间：{timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        st.info(f"📄 {viewer._format_file_size(file_size)}")
    
    st.divider()
    
    # 显示完整内容
    content = viewer.read_file_content(filepath)
    st.markdown(content)
    
    st.divider()
    
    # 操作按钮
    col1, col2 = st.columns(2)
    with col1:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        st.download_button(
            label="📥 下载报告",
            data=content,
            file_name=filename,
            mime="text/markdown",
            use_container_width=True
        )
    with col2:
        if st.button("🔙 返回列表", use_container_width=True):
            st.query_params.page = "history_reports"
            st.rerun()

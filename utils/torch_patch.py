"""
PyTorch兼容性补丁
解决Streamlit与PyTorch之间的兼容性问题
"""
import sys


def apply_torch_patches():
    """
    应用所有PyTorch相关补丁
    通过monkey patch方式修复Streamlit的文件监视器
    """
    try:
        # 尝试导入Streamlit的监视器模块
        import streamlit.watcher.local_sources_watcher as lsw
        
        # 保存原始函数
        original_get_module_paths = lsw.get_module_paths
        original_extract_paths = lsw.extract_paths
        
        # 创建新的函数来处理异常
        def patched_get_module_paths(module):
            try:
                return original_get_module_paths(module)
            except RuntimeError as e:
                if "__path__._path" in str(e) or "torch::_classes" in str(e) or "Tried to instantiate class" in str(e):
                    # 忽略与torch._classes相关的错误
                    return []
                else:
                    # 重新抛出其他错误
                    raise
        
        def patched_extract_paths(module):
            try:
                return original_extract_paths(module)
            except RuntimeError as e:
                if "__path__._path" in str(e) or "torch::_classes" in str(e) or "Tried to instantiate class" in str(e):
                    # 忽略与torch._classes相关的错误
                    return []
                else:
                    # 重新抛出其他错误
                    raise
        
        # 应用补丁
        lsw.get_module_paths = patched_get_module_paths
        lsw.extract_paths = patched_extract_paths
        
        # 同时处理Bootstrap中的异常
        import streamlit.web.bootstrap as bootstrap
        original_run = bootstrap.run
        
        def patched_run(*args, **kwargs):
            try:
                return original_run(*args, **kwargs)
            except RuntimeError as e:
                if "no running event loop" in str(e):
                    # 忽略事件循环错误
                    pass
                else:
                    # 重新抛出其他错误
                    raise
        
        bootstrap.run = patched_run
        
    except ImportError:
        # 如果无法导入相关模块，则忽略
        pass
    except Exception:
        # 忽略任何其他错误
        pass


# 立即应用补丁
apply_torch_patches()
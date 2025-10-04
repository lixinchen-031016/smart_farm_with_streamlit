"""
延迟导入工具模块
通过只在需要时才导入模块来提高应用启动速度
"""

import importlib
import sys
from typing import Any, Callable, Optional


class LazyImporter:
    """
    延迟导入器类
    用于延迟导入模块，直到实际需要使用时才导入
    """
    
    def __init__(self):
        self._modules = {}
        self._functions = {}
    
    def lazy_import(self, module_name: str, function_name: Optional[str] = None) -> Callable:
        """
        创建延迟导入函数
        
        Args:
            module_name: 模块名称
            function_name: 函数名称（可选）
            
        Returns:
            延迟导入的函数
        """
        key = f"{module_name}.{function_name}" if function_name else module_name
        
        if key not in self._functions:
            self._functions[key] = self._create_lazy_function(module_name, function_name)
        
        return self._functions[key]
    
    def _create_lazy_function(self, module_name: str, function_name: Optional[str] = None) -> Callable:
        """
        创建延迟函数
        
        Args:
            module_name: 模块名称
            function_name: 函数名称（可选）
            
        Returns:
            延迟函数
        """
        def wrapper(*args, **kwargs):
            # 检查模块是否已经导入
            if module_name not in self._modules:
                self._modules[module_name] = importlib.import_module(module_name)
            
            module = self._modules[module_name]
            
            # 如果指定了函数名，则调用该函数
            if function_name:
                func = getattr(module, function_name)
                return func(*args, **kwargs)
            else:
                # 否则返回整个模块
                return module
        
        # 设置函数名称以便调试
        wrapper.__name__ = function_name or module_name
        wrapper.__qualname__ = f"LazyImporter.{wrapper.__name__}"
        
        return wrapper


# 创建全局延迟导入器实例
lazy_importer = LazyImporter()


def lazy_import(module_name: str, function_name: Optional[str] = None) -> Callable:
    """
    延迟导入函数的便捷接口
    
    Args:
        module_name: 模块名称
        function_name: 函数名称（可选）
        
    Returns:
        延迟导入的函数
    """
    return lazy_importer.lazy_import(module_name, function_name)
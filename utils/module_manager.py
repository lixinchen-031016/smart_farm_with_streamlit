"""
模块配置管理系统
用于管理应用中的各个功能模块，支持启用/禁用模块
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ModuleConfig:
    """模块配置数据类"""
    name: str  # 模块名称
    enabled: bool  # 是否启用
    display_name: str  # 显示名称
    description: str  # 描述
    category: str  # 分类
    icon: str  # 图标
    admin_only: bool  # 是否仅管理员可用
    dependencies: List[str]  # 依赖的模块


class ModuleManager:
    """模块管理器"""
    
    def __init__(self, config_file: str = "module_config.json"):
        self.config_file = config_file
        self.modules: Dict[str, ModuleConfig] = {}
        self._load_default_modules()
        self._load_config()
    
    def _load_default_modules(self):
        """加载默认模块配置"""
        default_modules = [
            ModuleConfig(
                name="dashboard",
                enabled=True,
                display_name="控制面板",
                description="查看定制化仪表板",
                category="核心功能",
                icon="grid-3x3-gap",
                admin_only=False,
                dependencies=[]
            ),
            ModuleConfig(
                name="data_preview",
                enabled=True,
                display_name="实时数据预览",
                description="实时查看农场环境数据",
                category="核心功能",
                icon="speedometer",
                admin_only=False,
                dependencies=[]
            ),
            ModuleConfig(
                name="data_overview",
                enabled=True,
                display_name="数据概览",
                description="查看和导出历史数据",
                category="核心功能",
                icon="table",
                admin_only=False,
                dependencies=[]
            ),
            ModuleConfig(
                name="data_cleaning",
                enabled=True,
                display_name="数据清洗",
                description="清洗和处理数据",
                category="数据处理",
                icon="brush",
                admin_only=False,
                dependencies=["data_overview"]
            ),
            ModuleConfig(
                name="data_analysis",
                enabled=True,
                display_name="数据分析",
                description="进行统计分析和相关性分析",
                category="数据分析",
                icon="bar-chart",
                admin_only=False,
                dependencies=["data_overview"]
            ),
            ModuleConfig(
                name="data_visualization",
                enabled=True,
                display_name="可视化",
                description="创建各种数据图表",
                category="数据处理",
                icon="graph-up",
                admin_only=False,
                dependencies=["data_overview"]
            ),
            ModuleConfig(
                name="advanced_analysis",
                enabled=True,
                display_name="高级分析",
                description="进行数据分组和聚合分析",
                category="数据分析",
                icon="gear",
                admin_only=False,
                dependencies=["data_overview"]
            ),
            ModuleConfig(
                name="data_prediction",
                enabled=True,
                display_name="本地数据预测",
                description="使用机器学习模型进行数据预测",
                category="预测分析",
                icon="robot",
                admin_only=False,
                dependencies=["data_overview"]
            ),
            ModuleConfig(
                name="machine_learning",
                enabled=True,
                display_name="机器学习",
                description="训练和使用机器学习模型",
                category="预测分析",
                icon="cpu",
                admin_only=False,
                dependencies=["data_overview"]
            ),
            ModuleConfig(
                name="user_management",
                enabled=True,
                display_name="用户管理",
                description="管理系统用户和权限",
                category="系统管理",
                icon="person",
                admin_only=True,
                dependencies=[]
            ),
            ModuleConfig(
                name="system_monitoring",
                enabled=True,
                display_name="系统监控",
                description="监控系统资源使用情况和性能分析",
                category="系统管理",
                icon="cloud-upload",
                admin_only=True,
                dependencies=[]
            ),
            ModuleConfig(
                name="log_viewer",
                enabled=True,
                display_name="日志查看",
                description="查看系统操作日志",
                category="系统管理",
                icon="save",
                admin_only=False,
                dependencies=[]
            ),
            ModuleConfig(
                name="data_backup",
                enabled=True,
                display_name="数据备份",
                description="备份系统数据",
                category="数据管理",
                icon="arrow-counterclockwise",
                admin_only=True,
                dependencies=[]
            ),
            ModuleConfig(
                name="data_restore",
                enabled=True,
                display_name="数据恢复",
                description="恢复备份的数据",
                category="数据管理",
                icon="arrow-clockwise",
                admin_only=True,
                dependencies=[]
            ),
            ModuleConfig(
                name="sync_manager",
                enabled=True,
                display_name="数据库同步",
                description="同步本地和云端数据库",
                category="数据管理",
                icon="arrow-repeat",
                admin_only=False,
                dependencies=[]
            ),
            ModuleConfig(
                name="decision_engine",
                enabled=True,
                display_name="自动化决策",
                description="基于数据分析生成决策建议",
                category="智能分析",
                icon="lightbulb",
                admin_only=False,
                dependencies=["data_preview"]
            ),
            ModuleConfig(
                name="debug_info",
                enabled=False,  # 默认禁用调试模块
                display_name="调试信息",
                description="查看系统调试信息",
                category="系统管理",
                icon="bug",
                admin_only=True,
                dependencies=[]
            ),
            ModuleConfig(
                name="instruction_manual",
                enabled=True,
                display_name="使用说明",
                description="查看系统使用说明",
                category="帮助",
                icon="question-circle",
                admin_only=False,
                dependencies=[]
            )
        ]
        
        for module in default_modules:
            self.modules[module.name] = module
    
    def _load_config(self):
        """从配置文件加载模块配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新模块配置
                for module_name, module_data in config_data.items():
                    if module_name in self.modules:
                        # 更新现有模块配置
                        for key, value in module_data.items():
                            if hasattr(self.modules[module_name], key):
                                setattr(self.modules[module_name], key, value)
                    else:
                        # 添加新模块配置
                        self.modules[module_name] = ModuleConfig(**module_data)
            except Exception as e:
                print(f"加载模块配置文件时出错: {e}")
    
    def save_config(self):
        """保存模块配置到文件"""
        try:
            # 转换为可序列化的字典
            config_data = {}
            for module_name, module_config in self.modules.items():
                config_data[module_name] = asdict(module_config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模块配置文件时出错: {e}")
    
    def get_module(self, name: str) -> Optional[ModuleConfig]:
        """获取指定模块配置"""
        return self.modules.get(name)
    
    def get_modules(self, category: Optional[str] = None, enabled_only: bool = True) -> List[ModuleConfig]:
        """获取模块列表"""
        modules = list(self.modules.values())
        
        # 按分类过滤
        if category:
            modules = [m for m in modules if m.category == category]
        
        # 按启用状态过滤
        if enabled_only:
            modules = [m for m in modules if m.enabled]
            
        return modules
    
    def get_all_categories(self) -> List[str]:
        """获取所有模块分类"""
        categories = set(module.category for module in self.modules.values())
        return sorted(list(categories))
    
    def enable_module(self, name: str) -> bool:
        """启用模块"""
        if name in self.modules:
            self.modules[name].enabled = True
            self.save_config()
            return True
        return False
    
    def disable_module(self, name: str) -> bool:
        """禁用模块"""
        # 检查是否有其他模块依赖此模块
        for module in self.modules.values():
            if module.enabled and name in module.dependencies:
                print(f"无法禁用模块 {name}，因为模块 {module.name} 依赖于它")
                return False
        
        if name in self.modules:
            self.modules[name].enabled = False
            self.save_config()
            return True
        return False
    
    def update_module(self, name: str, **kwargs) -> bool:
        """更新模块配置"""
        if name in self.modules:
            module = self.modules[name]
            for key, value in kwargs.items():
                if hasattr(module, key):
                    setattr(module, key, value)
            self.save_config()
            return True
        return False
    
    def is_enabled(self, name: str) -> bool:
        """检查模块是否启用"""
        module = self.get_module(name)
        return module.enabled if module else False
    
    def get_enabled_modules_for_user(self, is_admin: bool = False) -> List[ModuleConfig]:
        """获取用户可用的启用模块"""
        modules = []
        for module in self.modules.values():
            if module.enabled and (not module.admin_only or is_admin):
                modules.append(module)
        return modules


# 创建全局模块管理器实例
module_manager = ModuleManager()


def get_module_manager() -> ModuleManager:
    """获取模块管理器实例"""
    return module_manager
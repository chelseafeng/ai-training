# -*- coding: utf-8 -*-

import os
from typing import Dict, Any
from urllib.parse import urljoin

import yaml


def load_yaml_file(config_path: str) -> Dict[str, Any]:
    """
    安全地加载单个 YAML 文件。如果文件未找到、为空或加载失败，则返回空字典。
    
    Args:
        config_path: YAML文件路径
        
    Returns:
        加载的配置字典，失败时返回空字典
    """
    if not os.path.exists(config_path):
        print(f"警告: 配置文件 '{config_path}' 未找到。")
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            content = yaml.safe_load(file)
            return content if content is not None else {}
    except Exception as e:
        print(f"错误: 加载 YAML 文件 '{config_path}' 失败: {e}")
        return {}


def _deep_merge_dicts(base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归地将 override_dict 合并到 base_dict 中。
    对于嵌套的字典，会进行深层合并；其他类型的值，override_dict 中的会覆盖 base_dict 中的。
    
    Args:
        base_dict: 基础配置字典
        override_dict: 覆盖配置字典
        
    Returns:
        合并后的配置字典
    """
    merged = base_dict.copy()
    for key, value in override_dict.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _build_service_urls(config: Dict[str, Any]) -> None:
    """
    根据配置中结构化的服务定义，构建完整的 URL 并填充到配置字典中。
    
    Args:
        config: 配置字典，会被就地修改
    """
    # LLM 服务 URL 构建
    llm_config = config.get('llm_server', {})
    llm_base_url = llm_config.get('base_url')
    
    if llm_base_url:
        config['llm_server_base_url'] = llm_base_url
        
        for endpoint_key, path in llm_config.get('endpoints', {}).items():
            full_url = urljoin(llm_base_url, path.lstrip('/'))
            
            if endpoint_key == 'default_generate_doc':
                config['llm_server_url'] = full_url
            else:
                config[f'llm_server_url_{endpoint_key}'] = full_url
    
    # AI 任务服务 URL 构建
    ai_task_config = config.get('ai_task_service', {})
    ai_task_base_url = ai_task_config.get('base_url')
    
    if ai_task_base_url:
        for endpoint_key, path in ai_task_config.get('endpoints', {}).items():
            full_url = urljoin(ai_task_base_url, path.lstrip('/'))
            config[f'ai_task_{endpoint_key}_url'] = full_url
    
    # 清理临时结构块
    config.pop('llm_server', None)
    config.pop('ai_task_service', None)


def get_config() -> Dict[str, Any]:
    """
    加载、合并并处理应用配置，生成最终的扁平化配置。
    
    Returns:
        处理后的配置字典
    """
    # 计算项目根目录路径（从 src 目录向上一级）
    current_dir = os.path.dirname(__file__)
    src_dir = os.path.dirname(current_dir)  # src 目录
    root_project_dir = os.path.dirname(src_dir)  # 项目根目录（src和envs的父目录）
    
    # 加载通用配置
    common_config_path = os.path.join(root_project_dir, "envs", "config.yaml")
    common_config = load_yaml_file(common_config_path)
    
    # 获取环境名称，默认为 'dev'
    env_name = common_config.get('env', 'dev')
    if not common_config.get('env'):
        print(f"警告: 'env' 键未在 'config.yaml' 中找到，使用默认值: {env_name}")
        common_config['env'] = env_name
    
    # 加载环境特定配置
    env_config_path = os.path.join(root_project_dir, "envs", f"config_{env_name}.yaml")
    env_config = load_yaml_file(env_config_path)
    
    # 合并配置
    merged_config = _deep_merge_dicts(common_config, env_config)
    
    # 构建服务URL
    _build_service_urls(merged_config)
    
    return merged_config


# 全局配置变量
CONFIG = get_config()

# 路径常量
ROOT_PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))  # 指向 src 目录
STATIC_FILE_PATH = os.path.join(ROOT_PROJECT_DIR, 'static')


if __name__ == '__main__':
    import json
    
    print(f"ROOT_PROJECT_DIR: {ROOT_PROJECT_DIR}")
    print(f"STATIC_FILE_PATH: {STATIC_FILE_PATH}")
    print(json.dumps(CONFIG, indent=2, ensure_ascii=False))
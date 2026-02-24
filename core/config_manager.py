import json
import os
import datetime
import hashlib
import sys
from typing import Dict, List, Optional

class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        # 检测是否在 Android 环境中运行
        if hasattr(sys, 'android'):
            # Android 应用私有目录，无需权限，可读写
            base_dir = os.environ.get('ANDROID_PRIVATE', os.path.dirname(sys.executable))
            self.config_dir = os.path.join(base_dir, config_dir)
        elif getattr(sys, 'frozen', False):
            # PyInstaller 单文件模式（Windows/Linux），配置放在 exe 同级
            base_dir = os.path.dirname(sys.executable)
            self.config_dir = os.path.join(base_dir, config_dir)
        else:
            # 开发环境，使用相对路径
            self.config_dir = config_dir

        self.app_config_file = os.path.join(self.config_dir, "app_config.json")
        self.format_config_file = os.path.join(self.config_dir, "format_config.json")
        self.current_vars_file = os.path.join(self.config_dir, "current_variables.json")

        self._ensure_config_dir()
        self._ensure_default_formats()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def _ensure_default_formats(self):
        """确保有默认的格式配置"""
        if not os.path.exists(self.format_config_file):
            default_formats = {
                "标准格式(文件)": {"template": "{学号} {姓名}{扩展名}", "is_folder": False},
                "标准格式(文件夹)": {"template": "{学号} {姓名}", "is_folder": True},
            }
            self._save_json(self.format_config_file, default_formats)

    # --- 以下方法与原代码完全相同，仅保留核心实现 ---
    def set_current_roster_columns(self, columns: List[str]):
        all_vars = list(set(columns + ['扩展名']))
        self._save_json(self.current_vars_file, all_vars)

    def get_current_roster_columns(self) -> List[str]:
        return self._load_json(self.current_vars_file) or []

    def get_format_names(self) -> List[str]:
        formats = self._load_json(self.format_config_file)
        return list(formats.keys()) if formats else []

    def get_format_config(self, format_name: str) -> Optional[Dict]:
        formats = self._load_json(self.format_config_file)
        return formats.get(format_name) if formats else None

    def save_format(self, format_name: str, format_config: Dict):
        formats = self._load_json(self.format_config_file) or {}
        formats[format_name] = format_config
        self._save_json(self.format_config_file, formats)

    def delete_format(self, format_name: str):
        formats = self._load_json(self.format_config_file)
        if formats and format_name in formats:
            del formats[format_name]
            self._save_json(self.format_config_file, formats)

    def load_app_config(self) -> Dict:
        return self._load_json(self.app_config_file) or {}

    def save_app_config(self, config: Dict):
        self._save_json(self.app_config_file, config)

    def _sort_folders_by_order(self, folders, order_mapping):
        valid_folders = [(order_mapping.get(f, 999), f) for f in folders if f in order_mapping]
        valid_folders.sort(key=lambda x: x[0])
        return [f for _, f in valid_folders]

    def save_folder_config(self, parent_dir: str, config: dict):
        dir_hash = hashlib.md5(parent_dir.encode('utf-8')).hexdigest()[:8]
        config_key = f"folder_config_{dir_hash}"
        all_configs = self._load_folder_configs()
        if not isinstance(all_configs, dict):
            all_configs = {}
        if 'selected_folders' in config and 'order_mapping' in config:
            selected = config['selected_folders']
            order_mapping = config['order_mapping']
            sorted_folders = self._sort_folders_by_order(selected, order_mapping)
            config['selected_folders'] = sorted_folders
            config['folder_order'] = sorted_folders
        all_configs[config_key] = {
            'parent_dir': parent_dir,
            'config': config,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self._save_folder_configs(all_configs)

    def load_folder_config(self, parent_dir: str) -> Optional[dict]:
        dir_hash = hashlib.md5(parent_dir.encode('utf-8')).hexdigest()[:8]
        config_key = f"folder_config_{dir_hash}"
        all_configs = self._load_folder_configs()
        if not isinstance(all_configs, dict):
            return None
        if config_key in all_configs:
            config = all_configs[config_key]['config']
            if 'selected_folders' in config and 'order_mapping' in config:
                selected = config['selected_folders']
                order_mapping = config['order_mapping']
                sorted_folders = self._sort_folders_by_order(selected, order_mapping)
                config['selected_folders'] = sorted_folders
                config['folder_order'] = sorted_folders
            return config
        return None

    def _load_folder_configs(self) -> dict:
        folder_config_file = os.path.join(self.config_dir, "folder_configs.json")
        try:
            if os.path.exists(folder_config_file):
                with open(folder_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    def _save_folder_configs(self, data: dict):
        folder_config_file = os.path.join(self.config_dir, "folder_configs.json")
        try:
            with open(folder_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存文件夹配置失败: {str(e)}")

    def _load_json(self, filepath: str) -> Optional[Dict]:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_json(self, filepath: str, data: Dict):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存配置文件失败: {str(e)}")
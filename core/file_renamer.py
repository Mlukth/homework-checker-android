# 文件路径: core/file_renamer.py
import os
import pandas as pd
from typing import Dict, Optional, Callable

class FileRenamer:
    def rename_files(self, df: pd.DataFrame, homework_dir: str,
                    rename_format: dict, log_callback: Optional[Callable] = None) -> int:
        """
        根据格式重命名文件
        """
        rename_count = 0

        if not os.path.exists(homework_dir):
            self._log(f"跳过不存在的文件夹：{homework_dir}", log_callback)
            return rename_count

        # 创建映射
        name_to_id = {row['姓名']: str(row['学号']) for _, row in df.iterrows()}
        id_to_name = {str(row['学号']): row['姓名'] for _, row in df.iterrows()}

        template = rename_format.get('template', '')
        is_folder_project = rename_format.get('is_folder', False)

        if is_folder_project:
            rename_count = self._rename_folders(homework_dir, df, name_to_id, id_to_name, template, log_callback)
        else:
            rename_count = self._rename_files(homework_dir, df, name_to_id, id_to_name, template, log_callback)

        return rename_count

    def _rename_folders(self, homework_dir: str, df: pd.DataFrame, name_to_id: Dict[str, str],
                       id_to_name: Dict[str, str], template: str,
                       log_callback: Optional[Callable]) -> int:
        """重命名文件夹"""
        rename_count = 0

        for item in os.listdir(homework_dir):
            item_path = os.path.join(homework_dir, item)
            if os.path.isdir(item_path):
                matched_name = self._find_matched_student(item, name_to_id, id_to_name)
                if matched_name:
                    # 获取学生完整信息
                    student_info = df[df['姓名'] == matched_name].iloc[0]
                    new_name = self._generate_new_name(template, student_info, "", is_folder=True)
                    new_path = os.path.join(homework_dir, new_name)
                    if not os.path.exists(new_path):
                        os.rename(item_path, new_path)
                        rename_count += 1
                        self._log(f"重命名文件夹: {item} -> {new_name}", log_callback)

        return rename_count

    def _rename_files(self, homework_dir: str, df: pd.DataFrame, name_to_id: Dict[str, str],
                     id_to_name: Dict[str, str], template: str,
                     log_callback: Optional[Callable]) -> int:
        """重命名文件【已修复：保留并附加原始文件扩展名】"""
        rename_count = 0

        for filename in os.listdir(homework_dir):
            filepath = os.path.join(homework_dir, filename)
            if filename.startswith('~$') or os.path.isdir(filepath):
                continue

            # ========== 关键修复开始 ==========
            # 1. 首先，分离原始文件的名称和扩展名[citation:3]
            original_name_without_ext, original_extension = os.path.splitext(filename)
            # ========== 关键修复结束 ==========

            matched_name = self._find_matched_student(original_name_without_ext, name_to_id, id_to_name)

            if matched_name:
                # 获取学生完整信息
                student_info = df[df['姓名'] == matched_name].iloc[0]
                # 2. 生成新文件名的主体部分（不包含扩展名）
                new_name_base = self._generate_new_name(template, student_info, "")
                # 3. 将原始文件的扩展名附加到新文件名上[citation:8]
                new_name = new_name_base + original_extension

                new_path = os.path.join(homework_dir, new_name)
                if not os.path.exists(new_path):
                    os.rename(filepath, new_path)
                    rename_count += 1
                    self._log(f"重命名文件: {filename} -> {new_name}", log_callback)

        return rename_count

    def _find_matched_student(self, search_text: str, name_to_id: Dict[str, str],
                            id_to_name: Dict[str, str]) -> Optional[str]:
        """查找匹配的学生"""
        # 先匹配姓名
        for name in name_to_id.keys():
            if name in search_text:
                return name

        # 再匹配学号
        for student_id, name in id_to_name.items():
            if student_id in search_text:
                return name

        return None

    def _generate_new_name(self, template: str, student_info: pd.Series,
                          file_ext: str, is_folder: bool = False) -> str:
        """生成新文件名（基础部分）"""
        # 这里可以添加课程名称和项目名称的提取逻辑
        course_name = "区块链2301"  # 可以从配置中获取
        project_name = "PROJECT"   # 可以从文件夹名称提取

        new_name = template

        # 替换标准变量
        new_name = new_name.replace('{学号}', self._safe_get_value(student_info, '学号'))
        new_name = new_name.replace('{姓名}', self._safe_get_value(student_info, '姓名'))
        new_name = new_name.replace('{课程名称}', course_name)
        new_name = new_name.replace('{项目名称}', project_name)

        # 替换自定义变量（花名册中的其他列）
        for column in student_info.index:
            if column not in ['学号', '姓名']:  # 避免重复替换
                variable = "{" + column + "}"
                if variable in new_name:
                    value = self._safe_get_value(student_info, column)
                    new_name = new_name.replace(variable, value)

        # 注意：这里不再自动添加 {扩展名}，因为扩展名会在外部处理
        # 如果模板中用户写了 {扩展名}，则替换为空字符串，防止出现多余内容
        if '{扩展名}' in new_name:
            new_name = new_name.replace('{扩展名}', '')

        return new_name

    def _safe_get_value(self, student_info: pd.Series, column: str) -> str:
        """安全获取值，处理NaN和空值"""
        value = student_info[column]

        # 检查是否为NaN或空值
        if pd.isna(value) or value == '' or str(value).strip() == 'nan':
            return '_'  # 用下划线代替空值

        return str(value).strip()

    def _log(self, message: str, log_callback: Optional[Callable]):
        """记录日志"""
        if log_callback:
            log_callback(message)
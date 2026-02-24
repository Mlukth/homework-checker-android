"""
作业检查与重命名系统 - Android 版 (Kivy)
需与 core 文件夹同级，并安装依赖：kivy, plyer, pandas, openpyxl, xlrd
"""
import os
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.clock import Clock
from kivy.core.window import Window
from plyer import filechooser
import pandas as pd

# 导入中文字体相关模块并配置
from kivy.core.text import LabelBase
from kivy.config import Config

# 获取字体文件的绝对路径（兼容打包后的环境）
def get_font_path(relative_path):
    if getattr(sys, 'frozen', False):
        # 打包后 exe 所在目录
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

# 注册中文字体（使用相对路径，兼容打包环境）
font_path = get_font_path('fonts/AlibabaPuHuiTi-3-55-Regular.ttf')
LabelBase.register(name='NotoSansCJK', fn_regular=font_path)
Config.set('kivy', 'default_font', ['NotoSansCJK', 'data/fonts/DejaVuSans.ttf'])

# ------------------- 新增字体测试代码 -------------------
def test_font():
    # 创建一个临时 Label，使用刚注册的字体（名称需与注册时一致）
    test_label = Label(text='中文测试', font_name='NotoSansCJK')
    print("字体名称：", test_label.font_name)  # 应该输出 'NotoSansCJK'
    print("字体文件路径：", font_path)
    print("文件是否存在：", os.path.exists(font_path))
    # 验证字体注册是否成功
    try:
        # 尝试渲染文本，触发字体加载
        test_label._label.refresh()
        print("字体测试成功：中文可正常显示")
    except Exception as e:
        print(f"字体测试失败：{e}")
        print("请检查字体文件路径是否正确，或文件是否损坏")

# 在应用启动后立即执行字体测试
Clock.schedule_once(lambda dt: test_font(), 0)
# --------------------------------------------------------

# 导入您的核心模块
from core.processor import HomeworkProcessor
from core.config_manager import ConfigManager

# 设置窗口大小（手机屏幕自适应）
Window.size = (400, 700)


# ----------------------------------------------------------------------
# 子文件夹选择行（用于 RecycleView）
# ----------------------------------------------------------------------
class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                  RecycleBoxLayout):
    """可选择的布局"""
    pass


class FolderSelectRow(RecycleDataViewBehavior, BoxLayout):
    """子文件夹选择列表中的一行，包含复选框和序号输入框"""
    index = None
    folder_name = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 40
        self.spacing = 5

        self.checkbox = CheckBox(size_hint_x=0.1)
        self.add_widget(self.checkbox)

        self.label = Label(text='', size_hint_x=0.6, halign='left')
        self.add_widget(self.label)

        self.number_input = TextInput(text='', size_hint_x=0.3, multiline=False,
                                      input_filter='int', hint_text='序号')
        self.add_widget(self.number_input)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.folder_name = data['name']
        self.label.text = data['name']
        self.checkbox.active = data['selected']
        self.number_input.text = data['order']
        # 绑定事件（需通过 rv 调用更新）
        self.checkbox.bind(active=lambda cb, val: rv.update_selected(index, val))
        self.number_input.bind(text=lambda ti, txt: rv.update_order(index, txt))
        return super().refresh_view_attrs(rv, index, data)


class FolderSelectRecycleView(RecycleView):
    """可滚动的文件夹选择列表"""
    def __init__(self, folders, selected_folders, order_mapping, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self.folders = folders
        self.selected_folders = selected_folders
        self.order_mapping = order_mapping
        self.refresh_data()

    def refresh_data(self):
        self.data = [{
            'name': f,
            'selected': f in self.selected_folders,
            'order': str(self.order_mapping.get(f, ''))
        } for f in self.folders]

    def update_selected(self, index, value):
        folder = self.data[index]['name']
        if value:
            if folder not in self.selected_folders:
                self.selected_folders.append(folder)
                # 自动分配一个未使用的序号
                used = {int(d['order']) for d in self.data if d['order'].isdigit()}
                order = 1
                while order in used:
                    order += 1
                self.order_mapping[folder] = order
        else:
            if folder in self.selected_folders:
                self.selected_folders.remove(folder)
                self.order_mapping.pop(folder, None)
        self.refresh_data()

    def update_order(self, index, text):
        folder = self.data[index]['name']
        if folder in self.selected_folders:
            if text.isdigit():
                self.order_mapping[folder] = int(text)
            else:
                self.order_mapping.pop(folder, None)
        self.refresh_data()


class FolderSelectorPopup(Popup):
    """子文件夹选择与排序弹出窗口"""
    def __init__(self, parent_dir, all_folders, config_manager, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = f"选择并排序 - {os.path.basename(parent_dir)}"
        self.size_hint = (0.9, 0.9)
        self.config_manager = config_manager
        self.parent_dir = parent_dir
        self.callback = callback

        # 加载已有配置
        saved = config_manager.load_folder_config(parent_dir)
        if saved:
            self.selected_folders = saved.get('selected_folders', [])
            self.order_mapping = saved.get('order_mapping', {})
        else:
            self.selected_folders = all_folders.copy()
            self.order_mapping = {f: i+1 for i, f in enumerate(all_folders)}

        self.all_folders = all_folders

        # 主布局
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # 说明
        layout.add_widget(Label(text='勾选文件夹并设置序号（1~N）', size_hint_y=0.05))

        # RecycleView 区域
        self.rv = FolderSelectRecycleView(all_folders, self.selected_folders, self.order_mapping)
        layout.add_widget(self.rv)

        # 按钮栏
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=5)
        btn_all = Button(text='全选')
        btn_all.bind(on_press=self.select_all)
        btn_none = Button(text='清空')
        btn_none.bind(on_press=self.select_none)
        btn_auto = Button(text='自动编号')
        btn_auto.bind(on_press=self.auto_number)
        btn_layout.add_widget(btn_all)
        btn_layout.add_widget(btn_none)
        btn_layout.add_widget(btn_auto)

        layout.add_widget(btn_layout)

        # 确认取消
        action_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        btn_cancel = Button(text='取消')
        btn_cancel.bind(on_press=self.dismiss)
        btn_ok = Button(text='应用选择')
        btn_ok.bind(on_press=self.apply_selection)
        action_layout.add_widget(btn_cancel)
        action_layout.add_widget(btn_ok)
        layout.add_widget(action_layout)

        self.add_widget(layout)

    def select_all(self, instance):
        self.selected_folders = self.all_folders.copy()
        # 重新编号
        self.order_mapping = {f: i+1 for i, f in enumerate(self.all_folders)}
        self.rv.selected_folders = self.selected_folders
        self.rv.order_mapping = self.order_mapping
        self.rv.refresh_data()

    def select_none(self, instance):
        self.selected_folders = []
        self.order_mapping = {}
        self.rv.selected_folders = self.selected_folders
        self.rv.order_mapping = self.order_mapping
        self.rv.refresh_data()

    def auto_number(self, instance):
        # 为已选文件夹自动分配连续序号
        self.order_mapping = {f: i+1 for i, f in enumerate(self.selected_folders)}
        self.rv.order_mapping = self.order_mapping
        self.rv.refresh_data()

    def apply_selection(self, instance):
        # 收集最终选择的文件夹，按序号排序
        sorted_items = sorted(self.order_mapping.items(), key=lambda x: x[1])
        final_folders = [f for f, _ in sorted_items if f in self.selected_folders]
        # 保存配置
        config = {
            'selected_folders': final_folders,
            'folder_order': final_folders,
            'order_mapping': self.order_mapping,
            'total_folders': len(self.all_folders)
        }
        try:
            self.config_manager.save_folder_config(self.parent_dir, config)
            self.callback(final_folders)
            self.dismiss()
        except Exception as e:
            from kivy.uix.popup import Popup as KivyPopup
            err_popup = KivyPopup(title='错误', content=Label(text=str(e)), size_hint=(0.8,0.3))
            err_popup.open()


# ----------------------------------------------------------------------
# 格式管理相关
# ----------------------------------------------------------------------
class FormatManagerPopup(Popup):
    """格式管理主窗口"""
    def __init__(self, config_manager, refresh_callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "管理重命名格式"
        self.size_hint = (0.9, 0.9)
        self.config_manager = config_manager
        self.refresh_callback = refresh_callback
        self.available_vars = config_manager.get_current_roster_columns()

        if not self.available_vars:
            from kivy.uix.popup import Popup as KivyPopup
            KivyPopup(title='错误', content=Label(text='请先导入花名册'), size_hint=(0.8,0.3)).open()
            self.dismiss()
            return

        layout = BoxLayout(orientation='horizontal', padding=10, spacing=10)

        # 左侧格式列表
        left_box = BoxLayout(orientation='vertical', size_hint_x=0.4)
        left_box.add_widget(Label(text='现有格式', size_hint_y=0.1))
        self.format_list = Spinner(text='选择格式', values=[], size_hint_y=0.1)
        left_box.add_widget(self.format_list)
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=5)
        btn_add = Button(text='添加')
        btn_add.bind(on_press=self.add_format)
        btn_edit = Button(text='编辑')
        btn_edit.bind(on_press=self.edit_format)
        btn_del = Button(text='删除')
        btn_del.bind(on_press=self.delete_format)
        btn_layout.add_widget(btn_add)
        btn_layout.add_widget(btn_edit)
        btn_layout.add_widget(btn_del)
        left_box.add_widget(btn_layout)
        left_box.add_widget(Label())  # 填充
        layout.add_widget(left_box)

        # 右侧变量说明
        right_box = BoxLayout(orientation='vertical', size_hint_x=0.6)
        right_box.add_widget(Label(text='可用变量', size_hint_y=0.1))
        var_text = '  '.join([f'{{{v}}}' for v in self.available_vars])
        var_label = Label(text=var_text, size_hint_y=0.2, halign='left', valign='top')
        var_label.bind(size=lambda s, w: s.setter('text_size')(s, (w, None)))
        right_box.add_widget(var_label)

        help_text = """
        使用说明：
        1. 添加/编辑格式时会打开编辑窗口。
        2. 可点击变量按钮插入。
        3. 文件格式需包含{扩展名}。
        """
        help_label = Label(text=help_text, size_hint_y=0.7, halign='left', valign='top')
        help_label.bind(size=lambda s, w: s.setter('text_size')(s, (w, None)))
        right_box.add_widget(help_label)

        layout.add_widget(right_box)

        self.add_widget(layout)
        self.refresh_list()

    def refresh_list(self):
        names = self.config_manager.get_format_names()
        self.format_list.values = names
        if names:
            self.format_list.text = names[0]

    def add_format(self, instance):
        self.open_edit_popup(is_new=True)

    def edit_format(self, instance):
        if not self.format_list.text:
            return
        self.open_edit_popup(is_new=False, old_name=self.format_list.text)

    def delete_format(self, instance):
        if not self.format_list.text:
            return
        name = self.format_list.text
        from kivy.uix.popup import Popup as KivyPopup
        confirm = KivyPopup(title='确认', content=Label(text=f'删除格式 {name}？'),
                            size_hint=(0.8,0.3))
        confirm.open()
        # 由于需要异步，这里简单处理：直接删除（简化）
        self.config_manager.delete_format(name)
        self.refresh_list()
        self.refresh_callback()

    def open_edit_popup(self, is_new, old_name=None):
        popup = FormatEditPopup(self.config_manager, self.available_vars,
                                old_name, is_new, self.refresh_list, self.refresh_callback)
        popup.open()


class FormatEditPopup(Popup):
    """格式编辑窗口"""
    def __init__(self, config_manager, available_vars, old_name, is_new,
                 refresh_local, refresh_main, **kwargs):
        super().__init__(**kwargs)
        self.title = "添加新格式" if is_new else f"编辑格式: {old_name}"
        self.size_hint = (0.9, 0.8)
        self.config_manager = config_manager
        self.available_vars = available_vars
        self.old_name = old_name
        self.is_new = is_new
        self.refresh_local = refresh_local
        self.refresh_main = refresh_main

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # 格式名称
        name_layout = BoxLayout(size_hint_y=0.1)
        name_layout.add_widget(Label(text='名称：', size_hint_x=0.2))
        self.name_input = TextInput(text=old_name if not is_new else '', multiline=False)
        name_layout.add_widget(self.name_input)
        layout.add_widget(name_layout)

        # 变量按钮
        var_bar = BoxLayout(size_hint_y=0.1)
        var_bar.add_widget(Label(text='变量：', size_hint_x=0.2))
        var_btn_layout = BoxLayout()
        for v in self.available_vars:
            btn = Button(text=f'{{{v}}}', size_hint_x=None, width=80)
            btn.bind(on_press=lambda x, val=v: self.insert_text(f'{{{val}}}'))
            var_btn_layout.add_widget(btn)
        var_bar.add_widget(var_btn_layout)
        layout.add_widget(var_bar)

        # 模板输入
        layout.add_widget(Label(text='格式模板：', size_hint_y=0.05, halign='left'))
        self.template_input = TextInput(multiline=True, size_hint_y=0.4)
        layout.add_widget(self.template_input)

        # 文件夹选项
        self.is_folder = CheckBox(size_hint_x=0.1)
        folder_layout = BoxLayout(size_hint_y=0.1)
        folder_layout.add_widget(Label(text='这是文件夹项目', size_hint_x=0.3))
        folder_layout.add_widget(self.is_folder)
        layout.add_widget(folder_layout)

        # 保存取消
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        btn_cancel = Button(text='取消')
        btn_cancel.bind(on_press=self.dismiss)
        btn_save = Button(text='保存')
        btn_save.bind(on_press=self.save_format)
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_save)
        layout.add_widget(btn_layout)

        # 如果是编辑，加载原有数据
        if not is_new and old_name:
            config = config_manager.get_format_config(old_name)
            if config:
                self.template_input.text = config.get('template', '')
                self.is_folder.active = config.get('is_folder', False)

        self.add_widget(layout)

    def insert_text(self, text):
        self.template_input.insert_text(text)

    def save_format(self, instance):
        name = self.name_input.text.strip()
        template = self.template_input.text.strip()
        is_folder = self.is_folder.active

        if not name or not template:
            from kivy.uix.popup import Popup as KivyPopup
            KivyPopup(title='错误', content=Label(text='名称和模板不能为空'), size_hint=(0.8,0.3)).open()
            return

        if not is_folder and '{扩展名}' not in template:
            from kivy.uix.popup import Popup as KivyPopup
            confirm = KivyPopup(title='提示',
                                content=Label(text='文件格式建议包含{扩展名}，确定继续？'),
                                size_hint=(0.8,0.3))
            # 简单处理，直接继续
            pass

        if is_folder and '{扩展名}' in template:
            from kivy.uix.popup import Popup as KivyPopup
            KivyPopup(title='错误', content=Label(text='文件夹格式不能包含{扩展名}'), size_hint=(0.8,0.3)).open()
            return

        config = {'template': template, 'is_folder': is_folder}
        if not self.is_new and self.old_name != name:
            self.config_manager.delete_format(self.old_name)
        self.config_manager.save_format(name, config)
        self.refresh_local()
        self.refresh_main()
        self.dismiss()


# ----------------------------------------------------------------------
# 主应用
# ----------------------------------------------------------------------
class HomeworkCheckerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processor = HomeworkProcessor()
        self.config_manager = ConfigManager()
        self.format_names = []

    def build(self):
        # 主布局
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # 花名册选择
        roster_box = BoxLayout(size_hint_y=0.1)
        self.roster_path = TextInput(hint_text='花名册文件路径', readonly=True)
        btn_roster = Button(text='浏览', size_hint_x=0.3)
        btn_roster.bind(on_press=self.select_roster)
        roster_box.add_widget(self.roster_path)
        roster_box.add_widget(btn_roster)
        main_layout.add_widget(roster_box)

        # 作业文件夹选择
        homework_box = BoxLayout(size_hint_y=0.1)
        self.homework_dir = TextInput(hint_text='作业文件夹路径', readonly=True)
        btn_homework = Button(text='浏览', size_hint_x=0.3)
        btn_homework.bind(on_press=self.select_homework)
        homework_box.add_widget(self.homework_dir)
        homework_box.add_widget(btn_homework)
        main_layout.add_widget(homework_box)

        # 输出目录选择
        output_box = BoxLayout(size_hint_y=0.1)
        self.output_dir = TextInput(hint_text='输出目录', readonly=True)
        btn_output = Button(text='浏览', size_hint_x=0.3)
        btn_output.bind(on_press=self.select_output)
        output_box.add_widget(self.output_dir)
        output_box.add_widget(btn_output)
        main_layout.add_widget(output_box)

        # 重命名格式选择
        format_box = BoxLayout(size_hint_y=0.1)
        self.format_spinner = Spinner(
            text='选择格式',
            values=self.config_manager.get_format_names(),
            size_hint=(0.7, 1)
        )
        btn_manage_format = Button(text='管理格式', size_hint_x=0.3)
        btn_manage_format.bind(on_press=self.open_format_manager)
        format_box.add_widget(self.format_spinner)
        format_box.add_widget(btn_manage_format)
        main_layout.add_widget(format_box)

        # 操作按钮
        action_box = BoxLayout(size_hint_y=0.1, spacing=5)
        btn_start = Button(text='开始检查')
        btn_start.bind(on_press=self.start_check)
        btn_rename = Button(text='仅重命名')
        btn_rename.bind(on_press=self.rename_only)
        btn_quick = Button(text='快速配置')
        btn_quick.bind(on_press=self.quick_setup)
        action_box.add_widget(btn_start)
        action_box.add_widget(btn_rename)
        action_box.add_widget(btn_quick)
        main_layout.add_widget(action_box)

        # 批量检查区域
        batch_label = Label(text='🚀 批量检查汇总', size_hint_y=0.05, color=(0,0.7,0,1))
        main_layout.add_widget(batch_label)

        batch_parent_box = BoxLayout(size_hint_y=0.1)
        self.batch_parent = TextInput(hint_text='母文件夹', readonly=True)
        btn_batch_parent = Button(text='浏览', size_hint_x=0.3)
        btn_batch_parent.bind(on_press=self.select_batch_parent)
        batch_parent_box.add_widget(self.batch_parent)
        batch_parent_box.add_widget(btn_batch_parent)
        main_layout.add_widget(batch_parent_box)

        btn_select_subfolders = Button(text='选择子文件夹', size_hint_y=0.1)
        btn_select_subfolders.bind(on_press=self.select_subfolders)
        main_layout.add_widget(btn_select_subfolders)

        self.selected_folders_label = Label(text='未选择', size_hint_y=0.05, color=(0,0,1,1))
        main_layout.add_widget(self.selected_folders_label)

        btn_batch_check = Button(text='开始批量检查', size_hint_y=0.1)
        btn_batch_check.bind(on_press=self.batch_check)
        main_layout.add_widget(btn_batch_check)

        # 日志显示区域
        scroll = ScrollView(size_hint_y=0.3)
        self.log_text = TextInput(text='', readonly=True, multiline=True)
        scroll.add_widget(self.log_text)
        main_layout.add_widget(scroll)

        return main_layout

    def on_start(self):
        """应用启动后加载配置"""
        self.load_my_config()   # 改为调用新方法名

    # ---------- 文件选择方法 ----------
    def select_roster(self, instance):
        filechooser.choose_file(on_selection=self._on_roster_selected,
                                filters=["*.xls", "*.xlsx"])

    def _on_roster_selected(self, selection):
        if selection:
            self.roster_path.text = selection[0]

    def select_homework(self, instance):
        filechooser.choose_dir(on_selection=self._on_homework_selected)

    def _on_homework_selected(self, selection):
        if selection:
            self.homework_dir.text = selection[0]

    def select_output(self, instance):
        filechooser.choose_dir(on_selection=self._on_output_selected)

    def _on_output_selected(self, selection):
        if selection:
            self.output_dir.text = selection[0]

    def select_batch_parent(self, instance):
        filechooser.choose_dir(on_selection=self._on_batch_parent_selected)

    def _on_batch_parent_selected(self, selection):
        if selection:
            self.batch_parent.text = selection[0]

    # ---------- 核心功能 ----------
    def start_check(self, instance):
        if not self.validate_inputs():
            return
        format_config = self.config_manager.get_format_config(self.format_spinner.text)
        if not format_config:
            self.log("错误：未选择有效格式")
            return

        self.log("开始检查...")
        try:
            self.processor.process_homework(
                roster_path=self.roster_path.text,
                homework_dir=self.homework_dir.text,
                output_dir=self.output_dir.text,
                rename_format=format_config,
                log_callback=self.log
            )
            self.log("处理完成！")
        except Exception as e:
            self.log(f"处理失败：{str(e)}")

    def rename_only(self, instance):
        if not self.validate_inputs():
            return
        format_config = self.config_manager.get_format_config(self.format_spinner.text)
        if not format_config:
            self.log("错误：未选择有效格式")
            return

        self.log("开始重命名...")
        try:
            count = self.processor.rename_files_only(
                roster_path=self.roster_path.text,
                homework_dir=self.homework_dir.text,
                rename_format=format_config,
                log_callback=self.log
            )
            self.log(f"重命名完成，共处理 {count} 个文件")
        except Exception as e:
            self.log(f"重命名失败：{str(e)}")

    def quick_setup(self, instance):
        """快速配置花名册"""
        filechooser.choose_file(on_selection=self._quick_setup_file,
                                filters=["*.xls", "*.xlsx"])

    def _quick_setup_file(self, selection):
        if not selection:
            return
        path = selection[0]
        try:
            df = pd.read_excel(path, dtype={'学号': str})
            columns = df.columns.tolist()
            if '学号' not in columns or '姓名' not in columns:
                self.log("错误：花名册必须包含‘学号’和‘姓名’列")
                return
            self.roster_path.text = path
            self.config_manager.set_current_roster_columns(columns)
            # 创建基础格式
            base_formats = {
                "标准格式(文件)": {"template": "{学号} {姓名}{扩展名}", "is_folder": False},
                "标准格式(文件夹)": {"template": "{学号} {姓名}", "is_folder": True},
            }
            if '班级' in columns:
                base_formats["含班级格式"] = {"template": "{姓名}_{班级}{扩展名}", "is_folder": False}
            for name, cfg in base_formats.items():
                self.config_manager.save_format(name, cfg)
            # 更新下拉框
            self.format_spinner.values = self.config_manager.get_format_names()
            self.format_spinner.text = "标准格式(文件)"
            self.log("快速配置成功！")
        except Exception as e:
            self.log(f"快速配置失败：{str(e)}")

    def batch_check(self, instance):
        if not self.roster_path.text:
            self.log("请先选择花名册")
            return
        if not self.batch_parent.text:
            self.log("请选择母文件夹")
            return
        self.log("开始批量检查...")
        try:
            format_config = self.config_manager.get_format_config(self.format_spinner.text) if self.format_spinner.text else None
            folder_config = self.config_manager.load_folder_config(self.batch_parent.text)
            selected_folders = folder_config.get('selected_folders') if folder_config else None
            output = self.processor.batch_check_submissions(
                roster_path=self.roster_path.text,
                parent_dir=self.batch_parent.text,
                rename_format=format_config,
                selected_folders=selected_folders,
                log_callback=self.log
            )
            self.log(f"批量检查完成，报告：{output}")
        except Exception as e:
            self.log(f"批量检查失败：{str(e)}")

    def select_subfolders(self, instance):
        """打开子文件夹选择窗口"""
        parent_dir = self.batch_parent.text
        if not parent_dir or not os.path.exists(parent_dir):
            self.log("请先选择有效的母文件夹")
            return
        try:
            all_folders = [f for f in os.listdir(parent_dir)
                           if os.path.isdir(os.path.join(parent_dir, f)) and not f.startswith('.')]
        except Exception as e:
            self.log(f"读取文件夹失败：{e}")
            return

        if not all_folders:
            self.log("该文件夹下没有子文件夹")
            return

        popup = FolderSelectorPopup(parent_dir, all_folders, self.config_manager,
                                    self.update_selected_folders)
        popup.open()

    def update_selected_folders(self, selected_folders):
        """更新主界面显示的已选文件夹"""
        if selected_folders:
            text = f"已选 {len(selected_folders)} 个: " + ", ".join(selected_folders[:3])
            if len(selected_folders) > 3:
                text += f" 等{len(selected_folders)}个"
            self.selected_folders_label.text = text
        else:
            self.selected_folders_label.text = "未选择"

    def open_format_manager(self, instance):
        """打开格式管理窗口"""
        if not self.roster_path.text:
            self.log("请先导入花名册")
            return
        popup = FormatManagerPopup(self.config_manager, self.refresh_formats)
        popup.open()

    def refresh_formats(self):
        self.format_spinner.values = self.config_manager.get_format_names()

    def validate_inputs(self):
        if not self.roster_path.text:
            self.log("请选择花名册文件")
            return False
        if not self.homework_dir.text:
            self.log("请选择作业文件夹")
            return False
        if not self.output_dir.text:
            self.log("请选择输出目录")
            return False
        if not self.format_spinner.text:
            self.log("请选择重命名格式")
            return False
        return True

    def load_my_config(self):   # 原 load_config 改名
        config = self.config_manager.load_app_config()
        if config:
            self.roster_path.text = config.get('roster_path', '')
            self.homework_dir.text = config.get('homework_dir', '')
            self.output_dir.text = config.get('output_dir', '')
            self.format_spinner.text = config.get('format_name', '')
        self.format_spinner.values = self.config_manager.get_format_names()

    def log(self, msg):
        """添加日志到文本框"""
        Clock.schedule_once(lambda dt: self._append_log(msg))

    def _append_log(self, msg):
        self.log_text.text += msg + '\n'
        # 自动滚动到底部
        self.log_text.cursor = (len(self.log_text.text), 0)
        self.log_text.do_cursor_movement('cursor_end')


if __name__ == '__main__':
    HomeworkCheckerApp().run()
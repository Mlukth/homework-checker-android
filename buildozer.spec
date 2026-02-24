[app]
# 应用信息
title = 作业检查工具
package.name = homeworkchecker
package.domain = org.yourname
source.dir = .
version = 0.1

# 包含的文件类型（字体、图片、JSON等）
source.include_exts = py,png,jpg,kv,atlas,txt,ttf,ttc,otf,json,xlsx

# 依赖库
requirements = python3,kivy,pandas,openpyxl,xlrd,plyer,cython

# 屏幕方向
orientation = portrait

# Android 特定配置
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.enable_androidx = True
android.copy_libs = 1
android.archs = arm64-v8a, armeabi-v7a

# 镜像加速（用于国内网络环境）
android.sdk_mirror = https://mirrors.tuna.tsinghua.edu.cn/android/repository/
android.ndk_mirror = https://mirrors.tuna.tsinghua.edu.cn/android/repository/

# 包含字体文件夹（如果有）
android.add_assets = fonts/

# Python-for-android 配置
p4a.bootstrap = sdl2
p4a.setup_py = false
p4a.extra_args = --pip-args="--index-url https://pypi.tuna.tsinghua.edu.cn/simple"

# 日志级别
[buildozer]
log_level = 2
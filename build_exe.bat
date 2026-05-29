@echo off
echo ============================================
echo  OpenAR 打包脚本
echo ============================================

REM 1. 安装 pyinstaller (如已安装可跳过)
echo.
echo [1/3] 安装 PyInstaller...
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if %errorlevel% neq 0 (
    echo 清华源失败, 换阿里源重试...
    pip install pyinstaller -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
)

REM 2. 清理旧构建
echo.
echo [2/3] 清理旧构建...
rmdir /s /q build dist 2>nul
del OpenAR.spec 2>nul

REM 3. 打包
echo.
echo [3/3] 开始打包...
pyinstaller --onefile ^
    --name OpenAR ^
    --add-data "openar;openar" ^
    openar_editor.py

echo.
echo ============================================
echo  打包完成!
echo  输出: dist\OpenAR.exe
echo  大小: 
powershell -Command "(Get-Item 'dist\OpenAR.exe').Length / 1MB"
echo ============================================

REM 首次运行需要下载 easyocr 模型 (~200MB)
REM 模型缓存在: %USERPROFILE%\.EasyOCR\model\
pause

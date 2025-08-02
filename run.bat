@echo off
echo Clash 配置自动更新工具
echo ========================
echo.
echo 正在检查 Python 环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python！请先安装 Python 3.7+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b
)

echo.
echo 正在检查虚拟环境...

if exist venv (
    echo 发现已存在的虚拟环境，正在激活...
    call venv\Scripts\activate.bat
) else (
    echo 创建新的虚拟环境...
    python -m venv venv
    
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
    
    echo 配置国内镜像源...
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com
    
    echo 正在安装依赖包...
    pip install --upgrade pip
    pip install -r requirements.txt
)

echo.
echo 正在安装新的依赖包（Flask）...
pip install -r requirements.txt

echo.
echo 正在启动 Flask Web 服务器...
echo.
echo ====================================
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务器
echo ====================================
echo.
python app.py

pause
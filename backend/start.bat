@echo off
echo ==============================================
echo 古代玉器沁色演化监测系统 - 启动脚本
echo ==============================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)
echo Python环境正常 ✓
echo.

echo [2/3] 安装依赖...
pip install numpy django djangorestframework pymongo django-cors-headers channels
echo 依赖安装完成 ✓
echo.

echo [3/3] 启动Django服务...
echo.
echo 服务地址: http://localhost:8000
echo 前端页面: frontend/index.html
echo.
echo 按 Ctrl+C 停止服务
echo.

python manage.py runserver 0.0.0.0:8000

pause

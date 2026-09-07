@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 若无管理员权限，先提权写防火墙规则（手机访问必需）
net session >nul 2>&1
if errorlevel 1 (
  echo 正在请求管理员权限以放行防火墙（手机访问需要）...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo [1/3] 重建章节数据...
python build-data.py
if errorlevel 1 (
  echo 数据重建失败，请检查 Python / source.json
  pause
  exit /b 1
)

set PORT=8080

echo.
echo [2/3] 放行防火墙端口 %PORT% ...
netsh advfirewall firewall delete rule name="读者评审本地服务" >nul 2>&1
netsh advfirewall firewall add rule name="读者评审本地服务" dir=in action=allow protocol=TCP localport=%PORT% profile=any >nul
if errorlevel 1 (
  echo 防火墙放行失败。
) else (
  echo 已放行 TCP %PORT%，手机可访问。
)

echo.
echo [3/3] 启动本地服务...
echo.
python serve.py %PORT%
if errorlevel 1 pause

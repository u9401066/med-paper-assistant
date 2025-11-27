@echo off
REM Med Paper Assistant - Windows 自動設定腳本 (Command Prompt)
REM 使用方式: 雙擊執行或在命令提示字元中執行 scripts\setup.bat

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo   Med Paper Assistant Setup
echo ========================================
echo.

REM 取得腳本所在目錄
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
cd /d "%PROJECT_DIR%"

echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo         Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

echo [2/6] Creating virtual environment...
if exist ".venv" (
    echo        Virtual environment already exists, skipping...
) else (
    python -m venv .venv
    echo        Done!
)
echo.

echo [3/6] Activating virtual environment...
call .venv\Scripts\activate.bat
echo.

echo [4/6] Installing dependencies...
pip install --upgrade pip --quiet
pip install -e . --quiet
echo        Done!
echo.

echo [5/6] Configuring VS Code MCP...
if not exist ".vscode" mkdir .vscode

(
echo {
echo   "inputs": [],
echo   "servers": {
echo     "mdpaper": {
echo       "command": "${workspaceFolder}/.venv/Scripts/python.exe",
echo       "args": ["-m", "med_paper_assistant.mcp_server.server"],
echo       "env": {
echo         "PYTHONPATH": "${workspaceFolder}/src"
echo       }
echo     }
echo   }
echo }
) > .vscode\mcp.json
echo        mcp.json created!
echo.

echo [6/6] Verifying installation...
python -c "from med_paper_assistant.mcp_server.server import mcp; print(f'        MCP Server loaded: {len(mcp._tool_manager._tools)} tools')"
echo.

echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Open VS Code
echo   2. Press Ctrl+Shift+P
echo   3. Type 'Developer: Reload Window'
echo   4. Type / in Copilot Chat to see mdpaper commands
echo.
echo Available commands:
echo   /mdpaper.project  - Setup research project
echo   /mdpaper.concept  - Develop research concept
echo   /mdpaper.strategy - Configure search strategy
echo   /mdpaper.draft    - Write paper draft
echo   /mdpaper.analysis - Analyze data
echo   /mdpaper.clarify  - Refine content
echo   /mdpaper.format   - Export to Word
echo.
pause

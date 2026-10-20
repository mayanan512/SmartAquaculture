@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo =================================================
echo   SmartAquaculture v0.2.0 Startup Launcher
echo =================================================

set "PY_CMD="
py -V >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=py"
    goto :FOUND
)
where python >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=python"
    goto :FOUND
)
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*" "C:\Python3*" "C:\Program Files\Python3*" "%UserProfile%\anaconda3" "%UserProfile%\miniconda3" "C:\ProgramData\Anaconda3" "D:\Anaconda3" "E:\Anaconda3") do (
    if exist "%%~D\python.exe" (
        set "PY_CMD="%%~D\python.exe""
        goto :FOUND
    )
)
echo [ERROR] Python not found.
pause
exit /b 1

:FOUND
echo [1/3] Checking dependencies...
%PY_CMD% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo [2/3] Initializing SQLite database...
%PY_CMD% -m database.init_db
echo [3/3] Starting Streamlit server...
%PY_CMD% -m streamlit run app.py --theme.base="dark" --theme.primaryColor="#00E5FF" --theme.backgroundColor="#061326" --theme.secondaryBackgroundColor="#0E2547" --theme.textColor="#F4FAFF"
pause

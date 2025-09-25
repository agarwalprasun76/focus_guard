@echo off
REM Focus Guard Integration Test Suite Runner
REM This script runs the comprehensive Phase 3 integration tests

echo ========================================
echo Focus Guard Integration Test Suite
echo ========================================

REM Change to the focus_guard root directory
cd /d "%~dp0..\..\..\"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not available in PATH
    echo Please ensure Python is installed and accessible
    pause
    exit /b 1
)

REM Check if pytest is installed
python -c "import pytest" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pytest and dependencies...
    pip install pytest pytest-asyncio pytest-json-report pytest-cov psutil
)

REM Create test reports directory
if not exist "test_reports" mkdir test_reports

REM Run the integration test suite
echo Running Focus Guard Integration Test Suite...
echo.

python deployment\tools\testing\integration_test_suite.py --output-dir test_reports

REM Check exit code
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Integration tests completed successfully!
    echo ========================================
    echo.
    echo Reports generated in: test_reports\
    echo - HTML report: integration_test_report_*.html
    echo - JSON report: integration_test_report_*.json
    echo - CSV summary: integration_test_summary_*.csv
) else if %errorlevel% equ 1 (
    echo.
    echo ========================================
    echo Integration tests completed with failures
    echo ========================================
    echo.
    echo Check the reports in test_reports\ for details
) else (
    echo.
    echo ========================================
    echo Integration test suite execution failed
    echo ========================================
    echo.
    echo Check the logs for error details
)

echo.
echo Press any key to exit...
pause >nul

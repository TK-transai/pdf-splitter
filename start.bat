@echo off
echo PDF分割ツールを起動します...
echo.

cd /d "%~dp0backend"

echo 依存関係をインストール中...
pip install -r requirements.txt

echo.
echo サーバーを起動中...
echo ブラウザで http://localhost:8000 を開いてください
echo 終了するには Ctrl+C を押してください
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

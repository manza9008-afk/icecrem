@echo off
cd /d "%~dp0"
echo Installing required packages...
pip install fastapi uvicorn SQLAlchemy asyncpg python-dotenv passlib[bcrypt] python-jose
echo Starting Backend Server...
python .runtime\run_backend.py
pause

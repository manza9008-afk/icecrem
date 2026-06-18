$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { 'postgresql+asyncpg://postgres:postgres@localhost:5432/hooren_erp' }
$env:CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001'

Set-Location 'C:\React_project\Manza-main\Manza-main\backend'

& 'C:\Users\STELLAR CONSULTANCY\AppData\Local\Python\pythoncore-3.14-64\python.exe' `
  -m uvicorn server:app --host 127.0.0.1 --port 8000

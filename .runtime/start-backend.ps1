$env:MONGO_URL = 'mongodb://127.0.0.1:27017'
$env:DB_NAME = 'test_database'
$env:CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001'

Set-Location 'C:\Users\STELLAR CONSULTANCY\Desktop\Manza-main\Manza-main\backend'

& 'C:\Users\STELLAR CONSULTANCY\AppData\Local\Python\pythoncore-3.14-64\python.exe' `
  -m uvicorn server:app --host 127.0.0.1 --port 8000

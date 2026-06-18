const { spawn } = require('child_process');

const child = spawn(
  'C:\\Users\\STELLAR CONSULTANCY\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe',
  ['C:\\React_project\\Manza-main\\Manza-main\\.runtime\\run_backend.py'],
  {
    cwd: 'C:\\React_project\\Manza-main\\Manza-main',
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
    env: {
      ...process.env,
      DATABASE_URL: process.env.DATABASE_URL || 'postgresql+asyncpg://postgres:postgres@localhost:5432/hooren_erp',
      CORS_ORIGINS: process.env.CORS_ORIGINS || 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001',
    },
  }
);

console.log(child.pid);
child.unref();

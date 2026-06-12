const { spawn } = require('child_process');

const child = spawn(
  'C:\\Users\\STELLAR CONSULTANCY\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe',
  ['C:\\Users\\STELLAR CONSULTANCY\\Desktop\\Manza-main\\Manza-main\\.runtime\\run_backend.py'],
  {
    cwd: 'C:\\Users\\STELLAR CONSULTANCY\\Desktop\\Manza-main\\Manza-main',
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  }
);

console.log(child.pid);
child.unref();

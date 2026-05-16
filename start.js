// scripts/start.js
const { spawn, execSync } = require('child_process');
const path = require('path');

// 设置 NODE_ENV 为 development
process.env.NODE_ENV = 'development';

// ── 启动前清理残留进程，避免单实例锁冲突导致白屏 ──
function cleanupStaleProcesses() {
  const platform = process.platform;
  try {
    if (platform === 'win32') {
      // Windows: 通过窗口标题或可执行文件名匹配
      execSync('taskkill /F /IM "electron.exe" /FI "WINDOWTITLE eq super-agent-party*" 2>nul', { stdio: 'ignore' });
    } else {
      // macOS / Linux: 精确匹配本项目的 Electron 主进程
      const cwd = process.cwd();
      const ps = execSync('ps ax -o pid,command', { encoding: 'utf8' });
      const lines = ps.split('\n');
      for (const line of lines) {
        // 匹配 Electron.app/.../Electron . 且路径包含本项目目录
        if (line.includes('Electron') && line.includes(cwd) && line.includes('Electron .')) {
          const pid = parseInt(line.trim(), 10);
          if (pid && pid !== process.pid && pid !== process.ppid) {
            process.kill(pid, 'SIGTERM');
            console.log(`🧹 已清理残留 Electron 进程 (PID ${pid})`);
          }
        }
      }
    }
  } catch (_) {
    // 清理失败不阻塞启动
  }
}

cleanupStaleProcesses();

const platform = process.platform;
let cmd, args, options;

if (platform === 'win32') {
  // Windows: 先切换代码页为 UTF-8，再启动 electron
  cmd = 'cmd.exe';
  args = ['/c', 'chcp 65001 >nul && electron .'];
} else {
  // macOS / Linux: 直接运行 electron
  cmd = 'electron';
  args = ['.'];
}

options = {
  stdio: 'inherit',
  shell: false, // 非 Windows 不需要 shell；Windows 已用 cmd.exe
  env: process.env,
  cwd: process.cwd(),
};

const child = spawn(cmd, args, options);

child.on('exit', (code) => {
  process.exit(code);
});
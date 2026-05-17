# 常见问题排查

## 启动后空白 / 无窗口出现

### 症状

- `npm run dev` 执行后终端立即回到提示符，没有 Electron 窗口弹出
- 或窗口弹出但白屏，`Cmd+R` 刷新无反应
- 终端日志里只有 Debugger 相关输出，没有 `[PY]` 前缀的后端日志

### 根因

本项目使用 Electron 的 `app.requestSingleInstanceLock()` 保证只运行一个实例。如果上次运行的 Electron 进程没有正常退出（例如渲染进程崩溃、`write EIO` 导致主进程挂起、手动关闭终端但进程未被回收等），旧进程会继续持有单实例锁。此时再执行 `npm run dev`，新实例检测到锁被占用后直接调用 `app.quit()` 退出，表现为"闪退 / 无窗口"。

相关代码（`main.js`）：

```js
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
  return;
}
```

### 排查步骤

```bash
# 1. 检查是否有残留 Electron 进程
ps aux | grep 'Electron.app/Contents/MacOS/Electron \.' | grep -v grep

# 2. 如果看到旧进程（注意 PID 和启动时间），杀掉它
kill <PID>

# 如果 kill 无效，强杀
kill -9 <PID>

# 3. 同时检查是否有残留 Python 后端进程占用端口
ps aux | grep 'python.*server.py' | grep -v grep

# 4. 确认清理干净后重新启动
npm run dev
```

### 快速一键清理

```bash
# 杀掉所有本项目的 Electron 和 Python 后端进程
pkill -f 'Electron.app/Contents/MacOS/Electron \.' 2>/dev/null
pkill -f 'python.*server\.py' 2>/dev/null
sleep 1
npm run dev
```

> **注意**：`pkill` 会匹配所有符合模式的进程。如果同时在开发其他 Electron 应用，请用 `ps aux | grep ...` 确认 PID 后精确 `kill`。

---

## `write EIO` 致命错误弹窗

### 症状

`Cmd+R` 刷新后连续弹出多个标题为「致命错误」的弹窗，内容为「未捕获异常: write EIO」。

### 根因

Electron 渲染进程崩溃或终端断开后，主进程的 `process.stdout` 管道已断裂，但代码仍尝试向其写入 Python 后端日志，触发 `EIO` 错误。`uncaughtException` 处理函数内又尝试写 stdout/stderr，形成反复弹窗。

### 已有修复

`main.js` 中已添加以下防护：

1. Python 输出转发包裹 `try/catch`：
   ```js
   try { process.stdout.write(`[PY] ${output}`); } catch (_) {}
   ```

2. `uncaughtException` 处理函数忽略 `EIO`：
   ```js
   process.on('uncaughtException', (err) => {
     if (err.code === 'EIO') return;
     // ...
   });
   ```

如果仍然遇到此问题，按上一节的方法清理残留进程后重启即可。

---

## 自动清理机制

`start.js` 在启动 Electron 之前会自动检测并清理本项目的残留 Electron 进程，避免单实例锁冲突。正常使用 `npm run dev` 启动时无需手动清理。

如果自动清理未能覆盖（例如进程名不匹配），仍可使用上面的手动排查步骤。

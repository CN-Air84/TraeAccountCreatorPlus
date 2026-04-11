import asyncio
import json
import os
import sys
import threading
import queue
import re
from pathlib import Path
from aiohttp import web
import aiohttp
from aiohttp.web_response import Response

BASE_DIR = Path(__file__).parent
REGISTER_SCRIPT = BASE_DIR / "register.py"
MAIL_CLIENT_SCRIPT = BASE_DIR / "mail_client.py"

class RegistrationManager:
    def __init__(self):
        self.running = False
        self.stop_event = threading.Event()
        self.worker = None
        self.log_queue = queue.Queue()
        self.success_count = 0
        self.fail_count = 0
        self.total_count = 0
        self.api_key = None
    
    def set_api_key(self, api_key):
        """设置 API Key 到 mail_client"""
        self.api_key = api_key
        mail_client_path = MAIL_CLIENT_SCRIPT
        if mail_client_path.exists():
            content = mail_client_path.read_text(encoding='utf-8')
            # 替换 API_KEY 的值
            pattern = r'API_KEY\s*=\s*["\'].*?["\']'
            replacement = f'API_KEY = "{api_key}"'
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                mail_client_path.write_text(new_content, encoding='utf-8')
    
    def worker_thread(self, total, concurrency, cd):
        """工作线程"""
        import subprocess
        
        indices = list(range(1, total + 1))
        self.success_count = 0
        self.fail_count = 0
        
        for idx in indices:
            if self.stop_event.is_set():
                self.log_queue.put({"type": "warning", "message": f"收到停止信号，退出"})
                break
            
            self.log_queue.put({"type": "info", "message": f"开始注册第 {idx}/{total} 个账号..."})
            
            try:
                # 使用 python 命令运行 register.py
                result = subprocess.run(
                    [sys.executable, str(REGISTER_SCRIPT), "1", "1", str(cd)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=str(BASE_DIR)
                )
                
                output = result.stdout + result.stderr
                
                for line in output.strip().split('\n'):
                    if line.strip():
                        self.log_queue.put({"type": "detail", "message": line})
                        
                        if "[API]" in line:
                            self.log_queue.put({"type": "api", "message": line})
                        elif "[API 错误]" in line:
                            self.log_queue.put({"type": "fail", "message": line})
                
                if "注册成功" in output or "注册成功检查超时" in output or "默认成功" in output:
                    self.success_count += 1
                    self.log_queue.put({"type": "success", "message": f"第 {idx}/{total} 个账号完成 - 成功"})
                else:
                    self.fail_count += 1
                    self.log_queue.put({"type": "fail", "message": f"第 {idx}/{total} 个账号完成 - 失败"})
                    
            except subprocess.TimeoutExpired:
                self.fail_count += 1
                self.log_queue.put({"type": "fail", "message": f"第 {idx}/{total} 个账号超时"})
            except Exception as e:
                self.fail_count += 1
                self.log_queue.put({"type": "fail", "message": f"异常：{str(e)}"})
        
        self.log_queue.put({"type": "info", "message": "任务完成"})
        self.running = False
    
    def start(self, total, concurrency, cd):
        """开始注册"""
        if self.running:
            return False
        
        self.running = True
        self.stop_event.clear()
        self.total_count = total
        
        self.worker = threading.Thread(
            target=self.worker_thread,
            args=(total, concurrency, cd),
            daemon=True
        )
        self.worker.start()
        return True
    
    def stop(self):
        """停止注册"""
        self.stop_event.set()
    
    def get_status(self):
        """获取状态"""
        return {
            "running": self.running,
            "success": self.success_count,
            "fail": self.fail_count,
            "total": self.total_count
        }

manager = RegistrationManager()

async def index_handler(request):
    """提供网页界面"""
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return web.FileResponse(index_path)
    return web.Response(text="index.html not found", status=404)

async def api_register_handler(request):
    """开始注册 API"""
    try:
        data = await request.json()
        api_key = data.get("api_key", "")
        total = int(data.get("total", 1))
        concurrency = int(data.get("concurrency", 1))
        cd = int(data.get("cd", 10))
        
        if not api_key:
            return web.json_response({"error": "API Key 不能为空"}, status=400)
        
        # 设置 API Key
        manager.set_api_key(api_key)
        
        # 开始注册
        if not manager.start(total, concurrency, cd):
            return web.json_response({"error": "注册任务已在运行"}, status=400)
        
        # 创建 SSE 流
        async def stream():
            while manager.running or not manager.log_queue.empty():
                try:
                    msg = manager.log_queue.get_nowait()
                    data = f"data: {json.dumps(msg)}\n\n"
                    yield data
                except queue.Empty:
                    await asyncio.sleep(0.1)
            
            # 发送最终状态
            status = manager.get_status()
            data = f"data: {json.dumps({'type': 'done', **status})}\n\n"
            yield data
        
        return Response(
            stream(),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_stop_handler(request):
    """停止注册 API"""
    manager.stop()
    return web.json_response({"status": "stopped"})

async def api_status_handler(request):
    """获取状态 API"""
    status = manager.get_status()
    return web.json_response(status)

def create_app():
    """创建应用"""
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_post('/api/register', api_register_handler)
    app.router.add_post('/api/stop', api_stop_handler)
    app.router.add_get('/api/status', api_status_handler)
    return app

def main():
    """主函数"""
    print("=" * 60)
    print("Trae 账号注册 - Web 版")
    print("=" * 60)
    print("访问地址：http://localhost:8080")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080, print=None)

if __name__ == "__main__":
    main()

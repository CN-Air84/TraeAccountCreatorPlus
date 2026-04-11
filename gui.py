import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import subprocess
import queue
import time
import os
import sys
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTER_SCRIPT = os.path.join(SCRIPT_DIR, "register.py")

class RegisterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(" ")
        self.root.geometry("1000x750")
        self.root.resizable(True, True)

        self.running = False
        self.threads = []
        self.stop_event = threading.Event()
        self.success_count = 0
        self.fail_count = 0
        self.total_count = 0
        self.log_queues = {}
        self.count_lock = threading.Lock()
        self.quota_remaining = tk.StringVar(value="配额: --")
        self.rate_info = tk.StringVar(value="速率: --/--/s")
        self.domains_info = tk.StringVar(value="域名: --")

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="注册数量:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.total_var = tk.StringVar(value="1")
        self.total_entry = ttk.Entry(control_frame, textvariable=self.total_var, width=10)
        self.total_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="并发数:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.concurrency_var = tk.StringVar(value="1")
        self.concurrency_entry = ttk.Entry(control_frame, textvariable=self.concurrency_var, width=10)
        self.concurrency_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(control_frame, text="检查CD(s):").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.cd_var = tk.StringVar(value="10")
        self.cd_entry = ttk.Entry(control_frame, textvariable=self.cd_var, width=8)
        self.cd_entry.grid(row=0, column=5, padx=5, pady=5)

        self.start_btn = ttk.Button(control_frame, text="开始", command=self.start_registration)
        self.start_btn.grid(row=0, column=6, padx=10, pady=5)

        self.stop_btn = ttk.Button(control_frame, text="停止", command=self.stop_registration, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=7, padx=5, pady=5)

        ttk.Button(control_frame, text="清空日志", command=self.clear_log).grid(row=0, column=8, padx=5, pady=5)

        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.status_frame, text="成功:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.success_label = ttk.Label(self.status_frame, text="0", foreground="green", font=("Arial", 10, "bold"))
        self.success_label.grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(self.status_frame, text="失败:").grid(row=0, column=2, padx=10, sticky=tk.W)
        self.fail_label = ttk.Label(self.status_frame, text="0", foreground="red", font=("Arial", 10, "bold"))
        self.fail_label.grid(row=0, column=3, padx=5, sticky=tk.W)

        ttk.Label(self.status_frame, text="进度:").grid(row=0, column=4, padx=10, sticky=tk.W)
        self.progress_label = ttk.Label(self.status_frame, text="0/0", font=("Arial", 10, "bold"))
        self.progress_label.grid(row=0, column=5, padx=5, sticky=tk.W)

        self.api_frame = ttk.Frame(main_frame)
        self.api_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.api_frame, textvariable=self.rate_info, foreground="gray", font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.api_frame, textvariable=self.quota_remaining, foreground="gray", font=("Consolas", 9)).pack(side=tk.LEFT, padx=15)
        ttk.Label(self.api_frame, textvariable=self.domains_info, foreground="gray", font=("Consolas", 9)).pack(side=tk.LEFT, padx=15)

        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

    def _create_log_frame(self, worker_id):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f"线程 {worker_id}")

        log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9))
        log_text.pack(fill=tk.BOTH, expand=True)
        log_text.tag_config("success", foreground="green")
        log_text.tag_config("fail", foreground="red")
        log_text.tag_config("info", foreground="blue")
        log_text.tag_config("warning", foreground="orange")
        log_text.tag_config("detail", foreground="gray")
        log_text.tag_config("api", foreground="purple")

        q = queue.Queue()
        self.log_queues[worker_id] = q

        def update_loop():
            try:
                while True:
                    msg = q.get_nowait()
                    if isinstance(msg, dict) and "message" in msg:
                        log_text.insert(tk.END, msg["message"] + "\n", msg.get("tag"))
                        log_text.see(tk.END)
            except queue.Empty:
                pass
            self.root.after(100, update_loop)

        update_loop()
        return frame

    def _parse_api_info(self, line):
        # 新格式: [API]剩余配额: 994
        quota_match = re.search(r'\[API\]剩余配额:\s*(\S+)', line)
        if quota_match:
            self.quota_remaining.set(f"配额: {quota_match.group(1)}")
        
        # 兼容旧格式: 速率限制: 60/60/s | 剩余配额: 994
        rate_match = re.search(r'速率限制:\s*(\S+)/(\S+)/s\s*\|\s*剩余配额:\s*(\S+)', line)
        if rate_match:
            self.rate_info.set(f"速率: {rate_match.group(1)}/{rate_match.group(2)}/s")
            self.quota_remaining.set(f"配额: {rate_match.group(3)}")
        
        # 解析域名加载信息: 从配置文件加载了 X 个可用域名
        domains_match = re.search(r'从配置文件加载了\s*(\d+)\s*个可用域名', line)
        if domains_match:
            self.domains_info.set(f"域名: {domains_match.group(1)}个(缓存)")
        
        # 解析从API获取域名: 已将 X 个域名保存到配置文件
        save_match = re.search(r'已将\s*(\d+)\s*个域名保存到配置文件', line)
        if save_match:
            self.domains_info.set(f"域名: {save_match.group(1)}个(新获取)")

    def _log(self, worker_id, message, tag=None):
        timestamp = time.strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        if worker_id in self.log_queues:
            self.log_queues[worker_id].put({"message": full_msg, "tag": tag})

    def _log_detail(self, worker_id, message, tag="detail"):
        if worker_id in self.log_queues:
            self.log_queues[worker_id].put({"message": message, "tag": tag})

    def _update_stats(self):
        with self.count_lock:
            completed = self.success_count + self.fail_count
            self.success_label.config(text=str(self.success_count))
            self.fail_label.config(text=str(self.fail_count))
            self.progress_label.config(text=f"{completed}/{self.total_count}")
            if self.total_count > 0:
                self.progress_bar.config(value=(completed / self.total_count) * 100)

    def start_registration(self):
        try:
            total = int(self.total_var.get())
            concurrency = int(self.concurrency_var.get())
            cd = int(self.cd_var.get())
        except ValueError:
            self._log(0, "错误：请输入有效的数字", "fail")
            return

        if total <= 0 or concurrency <= 0:
            self._log(0, "错误：数量和并发数必须大于 0", "fail")
            return

        if cd <= 1:
            self._log(0, "错误：邮件检查CD必须大于1秒", "fail")
            return

        self.running = True
        self.stop_event.clear()
        self.success_count = 0
        self.fail_count = 0
        self.total_count = total
        self.threads = []
        self.log_queues = {}

        for widget in self.notebook.winfo_children():
            widget.destroy()

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.total_entry.config(state=tk.DISABLED)
        self.concurrency_entry.config(state=tk.DISABLED)
        self.cd_entry.config(state=tk.DISABLED)

        self._log(0, f"开始批量注册，总数：{total}，并发：{concurrency}，CD：{cd}s", "info")
        self._update_stats()

        for i in range(concurrency):
            self._create_log_frame(i + 1)

        for i in range(concurrency):
            t = threading.Thread(target=self._worker, args=(i + 1, total, concurrency, cd), daemon=True)
            t.start()
            self.threads.append(t)

    def _worker(self, worker_id, total, concurrency, cd):
        # 使用 'python' 命令而不是 sys.executable，确保使用正确的环境
        python_exe = 'python'

        indices = list(range(worker_id, total + 1, concurrency))

        for idx in indices:
            if not self.running:
                self._log(worker_id, "收到停止信号，退出", "warning")
                break

            self._log(worker_id, f"开始注册第 {idx}/{total} 个账号...", "info")

            try:
                result = subprocess.run(
                    [python_exe, REGISTER_SCRIPT, str(1), str(1), str(cd)],
                    capture_output=True,
                    text=True,
                    timeout=180
                )

                output = result.stdout + result.stderr

                self._log_detail(worker_id, "=== 子进程输出 ===")
                for line in output.strip().split('\n'):
                    self._parse_api_info(line)
                    if "[API]" in line:
                        self._log_detail(worker_id, line, "api")
                    elif "[API错误]" in line:
                        self._log_detail(worker_id, line, "fail")
                    else:
                        self._log_detail(worker_id, line)
                self._log_detail(worker_id, "=== 输出结束 ===")

                if "注册成功" in output or "注册成功检查超时" in output or "默认成功" in output:
                    with self.count_lock:
                        self.success_count += 1
                    self._log(worker_id, f"第 {idx}/{total} 个账号完成 - 成功", "success")
                else:
                    with self.count_lock:
                        self.fail_count += 1
                    self._log(worker_id, f"第 {idx}/{total} 个账号完成 - 失败", "fail")

            except subprocess.TimeoutExpired:
                with self.count_lock:
                    self.fail_count += 1
                self._log(worker_id, f"第 {idx}/{total} 个账号超时", "fail")
            except Exception as e:
                with self.count_lock:
                    self.fail_count += 1
                self._log(worker_id, f"异常：{str(e)}", "fail")

            self._update_stats()

        self._log(worker_id, "任务完成", "info")

        if self.running:
            all_done = True
            for t in self.threads:
                if t.is_alive():
                    all_done = False
                    break
            if all_done:
                self.root.after(0, self._on_all_finished)

    def stop_registration(self):
        self.running = False
        self.stop_event.set()
        self._log(0, "正在停止...", "warning")

    def _on_all_finished(self):
        self._log(0, f"全部完成！成功：{self.success_count}，失败：{self.fail_count}", "info")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.total_entry.config(state=tk.NORMAL)
        self.concurrency_entry.config(state=tk.NORMAL)
        self.cd_entry.config(state=tk.NORMAL)

    def clear_log(self):
        for q in self.log_queues.values():
            q.put({"message": "", "tag": None})
        self.notebook.select(0)
        for widget in self.notebook.winfo_children():
            if hasattr(widget, 'delete'):
                widget.delete(1.0, tk.END)

def main():
    root = tk.Tk()
    app = RegisterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

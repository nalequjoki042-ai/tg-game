import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import queue
import re
import urllib.request
import urllib.parse
import json
from datetime import datetime

APP_VERSION = "0.1.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

PYTHON_EXE = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
CLOUDFLARED_EXE = os.path.join(BASE_DIR, "cloudflared.exe")
ENV_PATH = os.path.join(BASE_DIR, ".env")


def load_env() -> dict:
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env


def update_telegram_bot_url(bot_token: str, new_url: str) -> str:
    """Update the Mini App button URL via Telegram Bot API."""
    payload = json.dumps({
        "menu_button": {
            "type": "web_app",
            "text": "\U0001f3ae \u0418\u0433\u0440\u0430\u0442\u044c",
            "web_app": {"url": new_url}
        }
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/setChatMenuButton",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return f"\u2705 Telegram bot URL \u043e\u0431\u043d\u043e\u0432\u043b\u0451\u043d: {new_url}"
            else:
                return f"\u26a0\ufe0f Telegram API \u043e\u0448\u0438\u0431\u043a\u0430: {result}"
    except Exception as e:
        return f"\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c Telegram: {e}"


class ProcessManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"\u041f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f TG \u0418\u0433\u0440\u043e\u0439  |  v{APP_VERSION}")
        self.geometry("900x650")
        self.processes = {}
        self.queues = {}
        self.current_url = ""

        style = ttk.Style(self)
        style.theme_use('clam')

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.btn_start = ttk.Button(top_frame, text="\u25b6 \u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0432\u0441\u0451", command=self.start_all)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(top_frame, text="\u23f9 \u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0432\u0441\u0451", command=self.stop_all, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_pull = ttk.Button(top_frame, text="\U0001f504 \u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441 GitHub", command=self.git_pull)
        self.btn_pull.pack(side=tk.LEFT, padx=5)

        btn_open_logs = ttk.Button(top_frame, text="\U0001f4c2 \u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0430\u043f\u043a\u0443 \u043b\u043e\u0433\u043e\u0432", command=self.open_logs_dir)
        btn_open_logs.pack(side=tk.LEFT, padx=5)

        self.url_label = ttk.Label(top_frame, text="URL: \u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 Cloudflare...", foreground="blue", cursor="hand2")
        self.url_label.pack(side=tk.LEFT, padx=15)
        self.url_label.bind("<Button-1>", lambda e: self.copy_url())

        self.status_var = tk.StringVar(value="\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e")
        status_label = ttk.Label(top_frame, textvariable=self.status_var, font=('Arial', 10, 'bold'))
        status_label.pack(side=tk.RIGHT, padx=10)

        version_label = ttk.Label(top_frame, text=f"v{APP_VERSION}", foreground="gray", font=('Arial', 9))
        version_label.pack(side=tk.RIGHT, padx=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tabs = {}
        self.add_tab("\U0001f310 Cloudflare", "cloudflare", [CLOUDFLARED_EXE, "tunnel", "--url", "http://localhost:8000"])
        self.add_tab("\u2699\ufe0f \u0421\u0435\u0440\u0432\u0435\u0440 (FastAPI)", "server", [PYTHON_EXE, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"])
        self.add_tab("\U0001f916 \u0411\u043e\u0442 (Telegram)", "bot", [PYTHON_EXE, os.path.join(BASE_DIR, "backend", "bot.py")])

        self.after(100, self.update_logs)

    def copy_url(self):
        if self.current_url:
            self.clipboard_clear()
            self.clipboard_append(self.current_url)
            messagebox.showinfo("\u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u043e", f"URL \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d:\n{self.current_url}")

    def add_tab(self, name, proc_id, cmd):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=name)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=2)

        btn_copy = ttk.Button(toolbar, text="\U0001f4cb \u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043b\u043e\u0433\u0438", command=lambda p=proc_id: self.copy_tab_logs(p))
        btn_copy.pack(side=tk.LEFT)

        st = scrolledtext.ScrolledText(frame, state='disabled', bg='#1e1e1e', fg='#cccccc', font=('Consolas', 10))
        st.pack(fill=tk.BOTH, expand=True)

        self.tabs[proc_id] = {'cmd': cmd, 'st': st, 'name': name}
        self.queues[proc_id] = queue.Queue()

    def open_logs_dir(self):
        os.startfile(LOGS_DIR)

    def git_pull(self):
        if messagebox.askyesno("\u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435", "\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u044b \u0438 \u0441\u043a\u0430\u0447\u0430\u0442\u044c \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0441 GitHub?"):
            self.stop_all()
            self.log("server", "\n--- \u041e\u0411\u041d\u041e\u0412\u041b\u0415\u041d\u0418\u0415 \u0421 GITHUB ---\n")
            try:
                result = subprocess.run(['git', 'pull', 'origin', 'main'], capture_output=True, text=True, cwd=BASE_DIR)
                self.log("server", result.stdout)
                if result.stderr:
                    self.log("server", f"\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435/\u041e\u0448\u0438\u0431\u043a\u0430: {result.stderr}")
                messagebox.showinfo("\u0413\u043e\u0442\u043e\u0432\u043e", "\u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e!")
            except Exception as e:
                messagebox.showerror("\u041e\u0448\u0438\u0431\u043a\u0430", f"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c\u0441\u044f: {e}")

    def copy_tab_logs(self, proc_id):
        st = self.tabs[proc_id]['st']
        logs = st.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(logs)
        messagebox.showinfo("\u0423\u0441\u043f\u0435\u0445", "\u041b\u043e\u0433\u0438 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u044b!")

    def start_all(self):
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("\u0420\u0430\u0431\u043e\u0442\u0430\u0435\u0442")

        for proc_id, info in self.tabs.items():
            if proc_id not in self.processes or self.processes[proc_id].poll() is not None:
                self.log(proc_id, f"--- \u0417\u0430\u043f\u0443\u0441\u043a {info['name']} ({datetime.now().strftime('%H:%M:%S')}) ---\n")

                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                try:
                    p = subprocess.Popen(
                        info['cmd'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        startupinfo=startupinfo,
                        encoding='utf-8',
                        errors='replace',
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        cwd=BASE_DIR
                    )
                    self.processes[proc_id] = p
                    t = threading.Thread(target=self.read_output, args=(p, proc_id), daemon=True)
                    t.start()
                except Exception as e:
                    self.log(proc_id, f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430: {e}\n")

    def stop_all(self):
        self.status_var.set("\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430...")
        for proc_id, p in list(self.processes.items()):
            if p.poll() is None:
                self.log(proc_id, f"\n--- \u041e\u0421\u0422\u0410\u041d\u041e\u0412\u041a\u0410 {self.tabs[proc_id]['name']} ---\n")
                try:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
                except Exception as e:
                    self.log(proc_id, f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0435: {e}\n")
        self.processes.clear()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e")

    def read_output(self, process, proc_id):
        log_file_path = os.path.join(LOGS_DIR, f"{proc_id}.log")
        for line in process.stdout:
            self.queues[proc_id].put(line)
            try:
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except:
                pass

    def update_logs(self):
        for proc_id, q in self.queues.items():
            while not q.empty():
                line = q.get_nowait()
                self.log(proc_id, line)

                if proc_id == "cloudflare" and "trycloudflare.com" in line:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        url = match.group(0)
                        if url != self.current_url:
                            self.current_url = url
                            self.url_label.config(text=f"URL: {url} (\u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u0447\u0442\u043e\u0431\u044b \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c)")
                            self.update_env_url(url)
                            self.log("cloudflare", f"\n\u2705 URL \u041e\u0411\u041d\u041e\u0412\u041b\u0415\u041d: {url}\n")
                            threading.Thread(
                                target=self.notify_telegram,
                                args=(url,),
                                daemon=True
                            ).start()

        self.after(50, self.update_logs)

    def notify_telegram(self, new_url: str):
        env = load_env()
        bot_token = env.get("BOT_TOKEN", "")
        if not bot_token:
            self.log("cloudflare", "\u274c BOT_TOKEN \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u0432 .env\n")
            return
        result = update_telegram_bot_url(bot_token, new_url)
        self.log("cloudflare", result + "\n")
        self.restart_bot()

    def restart_bot(self):
        bot_proc = self.processes.get("bot")
        if bot_proc and bot_proc.poll() is None:
            self.log("bot", "\n--- \u041f\u0415\u0420\u0415\u0417\u0410\u041f\u0423\u0421\u041a \u0411\u041e\u0422\u0410 (\u043d\u043e\u0432\u044b\u0439 URL) ---\n")
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(bot_proc.pid)], capture_output=True)
            except:
                pass
        import time
        time.sleep(1)
        info = self.tabs["bot"]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            p = subprocess.Popen(
                info['cmd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=BASE_DIR
            )
            self.processes["bot"] = p
            t = threading.Thread(target=self.read_output, args=(p, "bot"), daemon=True)
            t.start()
            self.log("bot", "\u2705 \u0411\u043e\u0442 \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0449\u0435\u043d \u0441 \u043d\u043e\u0432\u044b\u043c URL\n")
        except Exception as e:
            self.log("bot", f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u043a\u0430 \u0431\u043e\u0442\u0430: {e}\n")

    def update_env_url(self, new_url):
        try:
            if os.path.exists(ENV_PATH):
                with open(ENV_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = re.sub(r'APP_URL=.*', f'APP_URL={new_url}', content)
                with open(ENV_PATH, 'w', encoding='utf-8') as f:
                    f.write(new_content)
        except Exception as e:
            self.log("cloudflare", f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f .env: {e}\n")

    def log(self, proc_id, message):
        st = self.tabs[proc_id]['st']
        st.config(state='normal')
        st.insert(tk.END, message)
        st.see(tk.END)
        st.config(state='disabled')

    def on_closing(self):
        self.stop_all()
        self.destroy()


if __name__ == "__main__":
    app = ProcessManager()
    app.mainloop()

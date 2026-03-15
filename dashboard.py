import tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import queue
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

PYTHON_EXE = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
CLOUDFLARED_EXE = os.path.join(BASE_DIR, "cloudflared.exe")
ENV_PATH = os.path.join(BASE_DIR, ".env")

class ProcessManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Панель управления TG Игрой")
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
        
        self.btn_start = ttk.Button(top_frame, text="▶ Запустить всё", command=self.start_all)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(top_frame, text="⏹ Остановить всё", command=self.stop_all, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        btn_open_logs = ttk.Button(top_frame, text="📂 Открыть папку логов", command=self.open_logs_dir)
        btn_open_logs.pack(side=tk.LEFT, padx=5)

        self.url_label = ttk.Label(top_frame, text="URL: Ожидание Cloudflare...", foreground="blue", cursor="hand2")
        self.url_label.pack(side=tk.LEFT, padx=15)
        self.url_label.bind("<Button-1>", lambda e: self.clipboard_clear() or self.clipboard_append(self.current_url) if self.current_url else None)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Остановлено")
        status_label = ttk.Label(top_frame, textvariable=self.status_var, font=('Arial', 10, 'bold'))
        status_label.pack(side=tk.RIGHT, padx=10)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tabs = {}
        self.add_tab("🌐 Cloudflare", "cloudflare", [CLOUDFLARED_EXE, "tunnel", "--url", "http://localhost:8000"])
        self.add_tab("⚙️ Сервер (FastAPI)", "server", [PYTHON_EXE, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"])
        self.add_tab("🤖 Бот (Telegram)", "bot", [PYTHON_EXE, os.path.join(BASE_DIR, "backend", "bot.py")])
        
        self.after(100, self.update_logs)

    def add_tab(self, name, proc_id, cmd):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=name)
        
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        btn_copy = ttk.Button(toolbar, text="📋 Копировать логи", command=lambda p=proc_id: self.copy_tab_logs(p))
        btn_copy.pack(side=tk.LEFT)
        
        st = scrolledtext.ScrolledText(frame, state='disabled', bg='#1e1e1e', fg='#cccccc', font=('Consolas', 10))
        st.pack(fill=tk.BOTH, expand=True)
        
        self.tabs[proc_id] = {'cmd': cmd, 'st': st, 'name': name}
        self.queues[proc_id] = queue.Queue()

    def open_logs_dir(self):
        os.startfile(LOGS_DIR)

    def copy_tab_logs(self, proc_id):
        st = self.tabs[proc_id]['st']
        logs = st.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(logs)
        messagebox.showinfo("Успех", f"Логи из '{self.tabs[proc_id]['name']}' скопированы!")

    def start_all(self):
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Работает")
        
        for proc_id, info in self.tabs.items():
            if proc_id not in self.processes or self.processes[proc_id].poll() is not None:
                self.log(proc_id, f"--- Запуск {info['name']} ({datetime.now().strftime('%H:%M:%S')}) ---\n")
                
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
                    self.log(proc_id, f"Ошибка запуска: {e}\n")

    def stop_all(self):
        self.status_var.set("Остановка...")
        for proc_id, p in list(self.processes.items()):
            if p.poll() is None:
                self.log(proc_id, f"\n--- Остановка {self.tabs[proc_id]['name']} ---\n")
                try:
                    p.terminate()
                    p.wait(timeout=3)
                except Exception:
                    p.kill()
        self.processes.clear()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Остановлено")

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
                            self.url_label.config(text=f"URL: {url} (Нажмите, чтобы скопировать)")
                            self.update_env_url(url)
                            self.log("cloudflare", f"\nURL ОБНОВЛЕН: {url}\n")

        self.after(50, self.update_logs)

    def update_env_url(self, new_url):
        try:
            if os.path.exists(ENV_PATH):
                with open(ENV_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = re.sub(r'APP_URL=.*', f'APP_URL={new_url}', content)
                with open(ENV_PATH, 'w', encoding='utf-8') as f:
                    f.write(new_content)
        except Exception as e:
            self.log("cloudflare", f"Ошибка обновления .env: {e}\n")

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
    import tkinter as tk # исправляю опечатку импорта
    app = ProcessManager()
    app.mainloop()

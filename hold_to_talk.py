import ctypes
import io
import locale
import os
import queue
import re
import sys
import threading
import time
import wave
import winsound

import keyboard
import numpy as np
import pyperclip
import sounddevice as sd
from openai import AuthenticationError, OpenAI

KEY = os.environ.get('HOLD_TO_TALK_KEY', 'right ctrl')
SEND_KEY = os.environ.get('HOLD_TO_TALK_SEND_KEY') or None
LANGUAGE = os.environ.get('HOLD_TO_TALK_LANG') or None
WORDS = os.environ.get('HOLD_TO_TALK_WORDS') or None
BUTTON = os.environ.get('HOLD_TO_TALK_BUTTON', '1') != '0'
RATE = 16000
SILENCE = 0.004
CHUNK, SLACK = 25, 10
HERE = os.path.dirname(os.path.abspath(__file__))
BUTTON_POS = os.path.join(HERE, 'button-position.txt')
PT = (locale.getlocale()[0] or '').lower().startswith(('pt', 'portuguese'))
TEXT = {
    'nokey': (
        'No OpenAI key found, so dictation cannot start.\n\n'
        '1. Create a key at https://platform.openai.com/api-keys\n'
        '2. Run this in a command window: setx OPENAI_API_KEY "your-key"\n'
        '3. Close this window and open it again.',
        'Nao achei a chave da OpenAI, entao o ditado nao pode comecar.\n\n'
        '1. Crie uma chave em https://platform.openai.com/api-keys\n'
        '2. Rode isto numa janela de comando: setx OPENAI_API_KEY "sua-chave"\n'
        '3. Feche esta janela e abra de novo.',
    ),
    'badkey': (
        'OpenAI refused this key, so dictation cannot start.\n\n'
        'Check it at https://platform.openai.com/api-keys and set it again:\n'
        'setx OPENAI_API_KEY "your-key"',
        'A OpenAI recusou essa chave, entao o ditado nao pode comecar.\n\n'
        'Confira em https://platform.openai.com/api-keys e defina de novo:\n'
        'setx OPENAI_API_KEY "sua-chave"',
    ),
    'mic': ('Using microphone:', 'Usando o microfone:'),
    'ready': (f'Ready. Hold {KEY}, speak and release. Close this window to quit.',
              f'Pronto. Segure {KEY}, fale e solte. Feche esta janela pra desligar.'),
    'send': (f'Hold {SEND_KEY} to paste and press Enter in a terminal.',
             f'Segure {SEND_KEY} pra colar e dar Enter no terminal.'),
    'button': ('Button (green dot): click to speak, click again to paste. Drag to move it.',
               'Botao (bolinha verde): clique pra falar, clique de novo pra colar. Arraste pra mudar de lugar.'),
    'nobutton': ('(the button did not open, the key still works:', '(o botao nao abriu, a tecla continua valendo:'),
    'silence': ('(silence: nothing heard on this microphone)', '(silencio: nao ouvi nada nesse microfone)'),
    'stuck': ('(the previous dictation got stuck, skipping it)', '(a fala anterior travou, pulando ela)'),
    'error': ('error:', 'erro:'),
}
PHANTOM = (r'amara\.org|legendas pela comunidade|obrigad[oa] por assistir|inscreva-se'
           r'|thanks? for watching|subscribe|^\W*context\s*:|^\W*#+\W*$')
NO_TEXT = ('CabinetWClass', 'ExploreWClass', 'Progman', 'WorkerW', 'Shell_TrayWnd')
user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32


def t(name):
    return TEXT[name][1 if PT else 0]


# Printing happens on its own thread: selecting text in this window pauses console output,
# and that pause must never freeze recording, transcription or pasting.
_screen = queue.Queue()


def _printer():
    while True:
        print(*_screen.get(), flush=True)


threading.Thread(target=_printer, daemon=True).start()


def show(*parts):
    _screen.put(parts)


def allow_selection():
    try:
        handle = kernel32.GetStdHandle(-10)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0040 | 0x0080)
    except Exception:
        pass


def stop(name):
    winsound.Beep(300, 400)
    sys.exit(t(name))


allow_selection()
if not os.environ.get('OPENAI_API_KEY'):
    stop('nokey')
# Without a limit a dropped connection waits up to 10 minutes and every dictation queues behind it.
client = OpenAI(timeout=25, max_retries=1)
try:
    client.models.list()
except AuthenticationError:
    stop('badkey')
except Exception:
    pass

chunks, recording, cancelled, by_button = [], threading.Event(), threading.Event(), threading.Event()
held = [KEY]


def find_microphone():
    best, best_level = None, 0.0
    for i, device in enumerate(sd.query_devices()):
        if device['hostapi'] != sd.default.hostapi or device['max_input_channels'] < 1:
            continue
        if re.search(r'mapper|mapeador|virtual', device['name'], re.I):
            continue
        try:
            sample = sd.rec(int(RATE * 0.5), samplerate=RATE, channels=1, dtype='float32', device=i)
            sd.wait()
        except Exception:
            continue
        level = float(np.sqrt(np.mean(sample ** 2)))
        if level > best_level:
            best, best_level = i, level
    return best


def on_audio(data, *_):
    if recording.is_set():
        chunks.append(data.copy())


def is_phantom(text):
    if re.search(PHANTOM, text, re.I) and len(text) < 60:
        return True
    if WORDS:
        words = re.sub(r'\W+', ' ', WORDS.lower()).strip()
        heard = re.sub(r'\W+', ' ', text.lower()).strip()
        if len(heard) >= 15 and (heard in words or words[:40] in heard):
            return True
    return False


def transcribe(audio, with_words=True):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    buffer.seek(0)
    buffer.name = 'speech.wav'
    options = {}
    if LANGUAGE:
        options['language'] = LANGUAGE
    if WORDS and with_words:
        options['prompt'] = WORDS
    return client.audio.transcriptions.create(model='gpt-4o-transcribe', file=buffer, **options).text.strip()


def split_on_pauses(audio):
    # One very long recording tends to come back summarized. Cut it every ~25-35 s at the quietest moment.
    parts, start, n, block = [], 0, len(audio), RATE // 10
    while n - start > RATE * (CHUNK + SLACK):
        a, b = start + RATE * CHUNK, min(n, start + RATE * (CHUNK + SLACK))
        energy = [float(np.mean(audio[i:i + block] ** 2)) for i in range(a, b - block, block)]
        cut = a + block * int(np.argmin(energy))
        parts.append(audio[start:cut])
        start = cut
    parts.append(audio[start:])
    return parts


def transcribe_all(audio):
    text = ' '.join(x for x in (transcribe(p) for p in split_on_pauses(audio)) if x)
    if is_phantom(text):
        text = ''
    seconds = len(audio) / RATE
    # The model sometimes echoes the word list or drops half the speech: try once more without the list.
    if seconds > 3 and (not text or len(text.split()) / seconds < 1.0):
        again = transcribe(audio, with_words=False)
        if not is_phantom(again) and len(again.split()) > len(text.split()):
            text = again
    return text if re.search(r'\w', text) else ''


def focus(window):
    if not window or user32.GetForegroundWindow() == window:
        return
    front = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(me, front, True)
    try:
        if user32.IsIconic(window):
            user32.ShowWindow(window, 9)
        user32.SetForegroundWindow(window)
        user32.BringWindowToTop(window)
    finally:
        user32.AttachThreadInput(me, front, False)
    time.sleep(0.1)


last_console = [None]


def window_class(window):
    name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(window, name, 256)
    return name.value


def paste(text, target, enter):
    # Pastes into the window that was in front when the key went DOWN (you can switch windows while it
    # transcribes), then gives your clipboard back. Typing key by key dropped spaces in some terminals.
    time.sleep(0.15)
    try:
        before = pyperclip.paste()
    except Exception:
        before = None
    window = target if target and user32.IsWindow(target) else user32.GetForegroundWindow()
    if window_class(window) in NO_TEXT and last_console[0] and user32.IsWindow(last_console[0]):
        window = last_console[0]  # a folder or the desktop cannot take text: use the last terminal
    console = window_class(window) == 'ConsoleWindowClass'
    if console:
        last_console[0] = window
    pyperclip.copy(text)
    time.sleep(0.05)
    if console:
        result = ctypes.c_size_t()
        user32.SendMessageTimeoutW(window, 0x0111, 0xFFF1, 0, 0x2, 3000, ctypes.byref(result))  # console Paste
        if enter:
            time.sleep(0.8 + min(len(text) / 1500, 3))
            user32.PostMessageW(window, 0x0100, 0x0D, 0x001C0001)
            user32.PostMessageW(window, 0x0101, 0x0D, 0xC01C0001)
    else:
        front = user32.GetForegroundWindow()
        focus(window)
        for key, flags in ((0x11, 0), (0x56, 0), (0x56, 2), (0x11, 2)):  # Ctrl+V
            user32.keybd_event(key, 0, flags, 0)
            time.sleep(0.02)
        time.sleep(0.3)
        if front != window:
            focus(front)
    time.sleep(0.4)
    if before:
        try:
            pyperclip.copy(before)
        except Exception:
            pass


# Speaking again before the last one finished must not mix the two: each one waits for its turn.
turn = threading.Condition()
next_ticket, current = [0], [0]


def finish(ticket, recorded, target, enter):
    text = ''
    try:
        if recorded:
            audio = np.concatenate(recorded)[:, 0]
            if len(audio) >= RATE * 0.4:
                if np.sqrt(np.mean(audio ** 2)) < SILENCE:
                    show(t('silence'))
                    winsound.Beep(300, 200)
                else:
                    winsound.Beep(600, 80)
                    text = transcribe_all(audio)
    except Exception as error:
        show(t('error'), error)
        winsound.Beep(300, 400)
        text = ''
    finally:
        with turn:
            if not turn.wait_for(lambda: current[0] >= ticket, timeout=90):
                show(t('stuck'))
                current[0] = ticket
            try:
                if text:
                    show('>', text)
                    paste(text + ' ', target, enter)
            except Exception as error:
                show(t('error'), error)
            current[0] += 1
            turn.notify_all()


target_window = [None]


def start_recording():
    cancelled.clear()
    chunks.clear()
    target_window[0] = user32.GetForegroundWindow()
    recording.set()


def stop_recording(enter):
    recording.clear()
    recorded = list(chunks)
    chunks.clear()
    if cancelled.is_set():
        return
    ticket = next_ticket[0]
    next_ticket[0] += 1
    threading.Thread(target=finish, args=(ticket, recorded, target_window[0], enter)).start()


def beep_if_still_held():
    # Waits a moment so a shortcut like Ctrl+C does not beep.
    time.sleep(0.3)
    if recording.is_set() and not cancelled.is_set():
        winsound.Beep(1000, 80)


def key_name(event):
    # Left and right Ctrl share a scan code, so a hook on one also fires for the other.
    # The event name says which one it really was.
    name = (event.name or '').lower()
    return 'left ctrl' if name == 'ctrl' else name


def key_down(event):
    name = key_name(event)
    if recording.is_set() or name not in (KEY, SEND_KEY):
        return
    held[0] = name
    start_recording()
    threading.Thread(target=beep_if_still_held, daemon=True).start()


def key_up(event):
    name = key_name(event)
    if recording.is_set() and not by_button.is_set() and held[0] == name:
        stop_recording(enter=(name == SEND_KEY))


def any_key(event):
    # Holding the key as part of a shortcut (Ctrl+C, Ctrl+V...) is not dictation: cancel it.
    if by_button.is_set() or event.event_type != 'down' or not recording.is_set():
        return
    name = key_name(event)
    if name not in (KEY, SEND_KEY, 'ctrl', 'left ctrl', 'right ctrl', 'shift', 'alt'):
        cancelled.set()


def button_click():
    if recording.is_set():
        if by_button.is_set():
            by_button.clear()
            stop_recording(enter=False)
        return
    by_button.set()
    start_recording()
    threading.Thread(target=winsound.Beep, args=(1000, 80), daemon=True).start()


def button():
    # A small always-on-top dot that never takes the focus, so the text still goes where your cursor was.
    import tkinter as tk
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    try:
        x, y = (int(v) for v in open(BUTTON_POS).read().split())
    except Exception:
        x, y = root.winfo_screenwidth() - 90, root.winfo_screenheight() - 140
    root.geometry('64x64+%d+%d' % (x, y))
    canvas = tk.Canvas(root, width=64, height=64, highlightthickness=0, bg='#202020', cursor='hand2')
    canvas.pack()
    dot = canvas.create_oval(6, 6, 58, 58, fill='#2e7d32', outline='')
    label = canvas.create_text(32, 32, text='\U0001F3A4', font=('Segoe UI Emoji', 20), fill='white')
    root.update_idletasks()
    handle = user32.GetParent(root.winfo_id()) or root.winfo_id()
    user32.SetWindowLongW(handle, -20, user32.GetWindowLongW(handle, -20) | 0x08000000 | 0x00000080 | 0x00000008)
    drag = {}

    def press(e):
        drag.update(x=e.x_root, y=e.y_root, wx=root.winfo_x(), wy=root.winfo_y(), moved=False)

    def motion(e):
        dx, dy = e.x_root - drag['x'], e.y_root - drag['y']
        if abs(dx) + abs(dy) > 6:
            drag['moved'] = True
        if drag['moved']:
            root.geometry('+%d+%d' % (drag['wx'] + dx, drag['wy'] + dy))

    def release(_):
        if drag.get('moved'):
            try:
                open(BUTTON_POS, 'w').write('%d %d' % (root.winfo_x(), root.winfo_y()))
            except Exception:
                pass
        else:
            button_click()

    canvas.bind('<ButtonPress-1>', press)
    canvas.bind('<B1-Motion>', motion)
    canvas.bind('<ButtonRelease-1>', release)
    canvas.bind('<ButtonRelease-3>', lambda _: button_click())

    def paint():
        live = recording.is_set() and not cancelled.is_set()
        canvas.itemconfigure(dot, fill='#c62828' if live else '#2e7d32')
        canvas.itemconfigure(label, text='■' if live and by_button.is_set() else '\U0001F3A4')
        root.after(100, paint)

    paint()
    root.mainloop()


keyboard.hook(any_key)
for name in filter(None, (KEY, SEND_KEY)):
    keyboard.on_press_key(name, key_down)
    keyboard.on_release_key(name, key_up)

microphone = find_microphone()
with sd.InputStream(samplerate=RATE, channels=1, dtype='float32', callback=on_audio, device=microphone):
    print(t('mic'), sd.query_devices(microphone if microphone is not None else sd.default.device[0])['name'], flush=True)
    print(t('ready'), flush=True)
    if SEND_KEY:
        print(t('send'), flush=True)
    if BUTTON:
        print(t('button'), flush=True)
        try:
            button()
        except Exception as error:
            show(t('nobutton'), str(error) + ')')
            keyboard.wait()
    else:
        keyboard.wait()

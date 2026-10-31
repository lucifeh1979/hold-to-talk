import io
import locale
import os
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
LANGUAGE = os.environ.get('HOLD_TO_TALK_LANG') or None
WORDS = os.environ.get('HOLD_TO_TALK_WORDS') or None
RATE = 16000
SILENCE = 0.004
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
    'ready': (f'Ready. Hold {KEY}, speak and release. Close this window to quit.', f'Pronto. Segure {KEY}, fale e solte. Feche esta janela pra desligar.'),
    'silence': ('(silence: nothing heard on this microphone)', '(silencio: nao ouvi nada nesse microfone)'),
    'error': ('error:', 'erro:'),
}
PHANTOM = r'amara\.org|legendas pela comunidade|obrigad[oa] por assistir|inscreva-se|thanks? for watching|subscribe'


def t(name):
    return TEXT[name][1 if PT else 0]


def stop(name):
    winsound.Beep(300, 400)
    sys.exit(t(name))


if not os.environ.get('OPENAI_API_KEY'):
    stop('nokey')

client = OpenAI()
try:
    client.models.list()
except AuthenticationError:
    stop('badkey')
except Exception:
    pass

chunks, recording = [], threading.Event()


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


def transcribe(audio):
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
    if WORDS:
        options['prompt'] = WORDS
    return client.audio.transcriptions.create(model='gpt-4o-transcribe', file=buffer, **options).text.strip()


def type_text(text):
    time.sleep(0.15)
    keyboard.write(text, delay=0.005)
    pyperclip.copy(text)


def released():
    recording.clear()
    if not chunks:
        return
    audio = np.concatenate(chunks)[:, 0]
    chunks.clear()
    if len(audio) < RATE * 0.4:
        return
    if np.sqrt(np.mean(audio ** 2)) < SILENCE:
        print(t('silence'), flush=True)
        winsound.Beep(300, 200)
        return
    winsound.Beep(600, 80)
    try:
        text = transcribe(audio)
        if text and not re.search(PHANTOM, text, re.I):
            print('>', text, flush=True)
            type_text(text + ' ')
    except Exception as error:
        print(t('error'), error, flush=True)
        winsound.Beep(300, 400)


def pressed(_):
    if recording.is_set():
        return
    chunks.clear()
    recording.set()
    winsound.Beep(1000, 80)


keyboard.on_press_key(KEY, pressed)
keyboard.on_release_key(KEY, lambda _: threading.Thread(target=released).start())

microphone = find_microphone()
with sd.InputStream(samplerate=RATE, channels=1, dtype='float32', callback=on_audio, device=microphone):
    print(t('mic'), sd.query_devices(microphone if microphone is not None else sd.default.device[0])['name'], flush=True)
    print(t('ready'), flush=True)
    keyboard.wait()

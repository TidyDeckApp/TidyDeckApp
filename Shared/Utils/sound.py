"""Petit carillon doux de fin d'action (généré en mémoire, aucun fichier, aucun réseau)."""
import io
import math
import os
import struct
import sys
import wave


def chime_wav(volume: float = 1.0) -> bytes:
    rate, buf = 22050, io.BytesIO()
    notes = [(659.25, 0.28), (880.0, 0.28), (1318.5, 0.7)]     # mi - la - mi aigu, très doux
    amp = 0.22 * max(0.0, min(1.0, volume))
    frames = bytearray()
    for freq, dur in notes:
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            env = math.exp(-4.5 * t / dur) * min(1.0, i / 300)      # attaque douce, longue extinction
            v = amp * env * (math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t))
            frames += struct.pack("<h", int(v * 32767))
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _scaled_file(src: str, volume: float) -> str:
    """Ecrit une copie du wav amplifiee au volume demande (16 bits) ; retourne le chemin."""
    import array
    import tempfile
    with wave.open(src, "rb") as r:
        nch, sw, fr = r.getnchannels(), r.getsampwidth(), r.getframerate()
        raw = r.readframes(r.getnframes())
    if sw != 2:
        return src
    a = array.array("h")
    a.frombytes(raw)
    for i in range(len(a)):
        a[i] = max(-32768, min(32767, int(a[i] * volume)))
    out = os.path.join(tempfile.gettempdir(), "tidydeck_custom_%d.wav" % max(1, int(volume * 100)))
    with wave.open(out, "wb") as w:
        w.setnchannels(nch)
        w.setsampwidth(2)
        w.setframerate(fr)
        w.writeframes(a.tobytes())
    return out


_DATA = {}
_PATH = {}


def _volume() -> float:
    try:
        from Shared.Utils import config
        v = float(config.load().get("sound_volume", 70))
    except Exception:
        v = 70.0
    return max(0.0, min(1.0, v / 100.0))


def chime(volume=None):
    if sys.platform != "win32":
        return
    vol = _volume() if volume is None else max(0.0, min(1.0, float(volume)))
    if vol <= 0:
        return
    try:
        import winsound
        k = int(vol * 100)
        p = _PATH.get(k)
        if p is None or not os.path.isfile(p):
            p = os.path.join(os.environ.get("TEMP", "."), f"tidydeck_chime_{k}.wav")
            with open(p, "wb") as fh:
                fh.write(chime_wav(vol))
            _PATH[k] = p
        winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        from Shared.Utils import depannage
        depannage.noter("Shared/Utils/sound.py:81")


def play(path=None, volume=None):
    """Joue un son perso (wav) si fourni et existant, sinon le carillon doux par defaut.
    Le volume (0-100 dans la config) s'applique aux deux."""
    vol = _volume() if volume is None else max(0.0, min(1.0, float(volume)))
    if vol <= 0:
        return
    if path and os.path.isfile(path):
        try:
            import winsound
            src = _scaled_file(path, vol) if vol < 0.999 else path
            winsound.PlaySound(src, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("Shared/Utils/sound.py:97")
    chime(vol)

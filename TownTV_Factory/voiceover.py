"""Offline spoken narration. Piper (natural) when present, eSpeak fallback.

Voice models: en_US-john-medium and en_US-kristin-medium. Their source dataset
is public-domain LibriVox recordings; verify model cards before redistribution.
The models are downloaded by CI, not committed to the repository.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

ROOT = Path(__file__).resolve().parent
VOICE_DIR = ROOT / 'voices'
VOICE_IDS = {'host': 'en_US-john-medium', 'caller': 'en_US-kristin-medium'}
_VOICES = {}


def _run(cmd):
    p = subprocess.run([str(v) for v in cmd], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError('Audio command failed: ' + ' '.join(map(str, cmd[:4])) + '\n' + p.stderr[-700:])


def active_voice_engine(choice='auto'):
    if choice == 'espeak':
        if not shutil.which('espeak'): raise RuntimeError('eSpeak not installed')
        return 'espeak'
    try:
        from piper import PiperVoice  # noqa: F401
        if all((VOICE_DIR/(v+'.onnx')).exists() for v in VOICE_IDS.values()):
            return 'piper'
    except ImportError:
        pass
    if choice == 'piper':
        raise RuntimeError('Piper voices missing. Run voice download from README or install with GitHub Actions.')
    if not shutil.which('espeak'):
        raise RuntimeError('Install Piper voices or eSpeak before generating audio')
    return 'espeak'


def _write_speech(text, who, outfile, engine):
    if engine == 'piper':
        from piper import PiperVoice
        ident = VOICE_IDS['caller' if who == 'caller' else 'host']
        if ident not in _VOICES:
            _VOICES[ident] = PiperVoice.load(str(VOICE_DIR/(ident+'.onnx')))
        with wave.open(str(outfile), 'wb') as out:
            _VOICES[ident].synthesize_wav(text, out)
    else:
        pitch = 47 if who == 'caller' else 32
        _run(['espeak','-v', 'en-us+f3' if who == 'caller' else 'en-us',
              '-s','150','-p',str(pitch),'-a','165','-w',str(outfile),text])


def synthesize(segments, dest, voice_choice='auto'):
    """Return speech runtime in seconds. All segment WAVs normalized to 44.1 kHz mono."""
    engine = active_voice_engine(voice_choice)
    with tempfile.TemporaryDirectory() as td:
        pieces=[]
        for i, (who, text) in enumerate(segments):
            raw=Path(td)/f'{i:02d}_raw.wav'
            normal=Path(td)/f'{i:02d}_normal.wav'
            _write_speech(text, who, raw, engine)
            # Restrained analog broadcast processing; callers have telephone bandwidth.
            filt = ('highpass=f=220,lowpass=f=3300,acompressor=threshold=-21dB:ratio=2.2:attack=15:release=180'
                    if who == 'caller' else
                    'highpass=f=90,lowpass=f=11000,acompressor=threshold=-20dB:ratio=2:attack=18:release=160')
            _run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(raw),
                  '-af',filt,'-ar','44100','-ac','1','-c:a','pcm_s16le',str(normal)])
            with wave.open(str(normal),'rb') as w:
                assert (w.getnchannels(),w.getsampwidth(),w.getframerate()) == (1,2,44100)
                pieces.append(w.readframes(w.getnframes()))
        rate=44100
        with wave.open(str(dest),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
            for i, raw in enumerate(pieces):
                if i: out.writeframes(b'\x00'*int(rate*.40)*2)
                out.writeframes(raw)
        return sum(len(p) for p in pieces)/(rate*2)+max(0,len(pieces)-1)*.4, engine

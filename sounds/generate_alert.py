"""
Generate a simple WAV beep alert file for BidScouter notifications.
Run once: python sounds/generate_alert.py
"""
import struct
import math
import wave
import os

def generate_beep(filename, frequency=880, duration=0.5, sample_rate=44100, amplitude=0.5):
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        # Two-tone alert
        if i < n_samples // 2:
            s = amplitude * math.sin(2 * math.pi * 880 * t)
        else:
            s = amplitude * math.sin(2 * math.pi * 1100 * t)
        # Fade in/out
        fade = min(i, n_samples - i, 2000) / 2000.0
        samples.append(int(s * fade * 32767))

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "alert.wav")
    generate_beep(out)
    print(f"Generated: {out}")

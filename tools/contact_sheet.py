"""Contact sheet + stream report for a generated video, so an agent can eyeball a result without a player.

Run with the ComfyUI venv python (needs av, numpy, PIL), e.g. inside WSL:
  ~/h3-video-gen-runtime/ComfyUI/.venv/bin/python tools/contact_sheet.py outputs/x.mp4 [--frames 8] [--out x.png]
Prints JSON (video/audio stream info, audio RMS) and writes a PNG grid of evenly spaced frames.
"""

import argparse
import json
import os

import av
import numpy as np
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser()
    p.add_argument('video')
    p.add_argument('--frames', type=int, default=8)
    p.add_argument('--cols', type=int, default=4)
    p.add_argument('--width', type=int, default=480, help='thumbnail width')
    p.add_argument('--out')
    a = p.parse_args()
    out = a.out or os.path.splitext(a.video)[0] + '_sheet.png'

    with av.open(a.video) as c:
        vs = c.streams.video[0]
        fps, codec = float(vs.average_rate or 0), vs.codec_context.name
        frames = [f.to_image() for f in c.decode(video=0)]
    info = {'video': {'frames': len(frames), 'size': frames[0].size if frames else None, 'fps': fps, 'codec': codec}}
    with av.open(a.video) as c:
        if c.streams.audio:
            st = c.streams.audio[0]
            acodec, rate, channels = st.codec_context.name, st.rate, st.channels
            pcm = np.concatenate([f.to_ndarray().reshape(-1) for f in c.decode(audio=0)]).astype(np.float32)
            if pcm.size and np.abs(pcm).max() > 1.5:  # integer PCM
                pcm /= 32768.0
            info['audio'] = {'codec': acodec, 'rate': rate, 'channels': channels,
                             'seconds': round(pcm.size / max(channels, 1) / rate, 2),
                             'rms': round(float(np.sqrt(np.mean(pcm ** 2))), 4) if pcm.size else 0.0}
        else:
            info['audio'] = None

    idx = np.linspace(0, len(frames) - 1, a.frames).round().astype(int)
    tw = a.width
    th = round(frames[0].size[1] * tw / frames[0].size[0])
    rows = -(-len(idx) // a.cols)
    sheet = Image.new('RGB', (a.cols * tw, rows * th), 'black')
    for k, i in enumerate(idx):
        im = frames[i].resize((tw, th), Image.Resampling.LANCZOS)
        ImageDraw.Draw(im).text((6, 4), f'#{i}  {i / (info["video"]["fps"] or 24):.2f}s', fill='yellow')
        sheet.paste(im, ((k % a.cols) * tw, (k // a.cols) * th))
    sheet.save(out)
    info['sheet'] = out
    print(json.dumps(info))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولّد فيديوهات المقدمة السينمائية لكل موقع أثري
   (صورة حقيقية بزوم + بانوراما بتتحرك + الشرح الصوتي العربي)"""
import subprocess, os, re, sys

FF = subprocess.run(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],
                    capture_output=True, text=True).stdout.strip()
ROOT = '/home/user/ancient-egypt'
IMG, PANO, AUD, VID = f'{ROOT}/assets/img', f'{ROOT}/assets/pano', f'{ROOT}/assets/audio', f'{ROOT}/assets/video'
TMP = '/tmp/vidsrc'
os.makedirs(VID, exist_ok=True); os.makedirs(TMP, exist_ok=True)

SITES = {
 'giza':     ('giza.webp',      'giza.jpg',      'giza.mp3'),
 'saqqara':  ('saqqara.jpg',    'saqqara.jpg',   'saqqara.mp3'),
 'karnak':   ('karnak.jpg',     'karnak.jpg',    'karnak.mp3'),
 'luxor':    ('luxor.jpg',      'luxor.jpg',     'luxor.mp3'),
 'deir':     ('hatshepsut.jpg', 'hatshepsut.jpg','hatshepsut.mp3'),
 'edfu':     ('edfu.webp',      'edfu.jpg',      'edfu.mp3'),
 'komombo':  ('komombo.jpg',    'komombo.jpg',   'komombo.mp3'),
 'philae':   ('philae.jpg',     'philae.jpg',    'philae.mp3'),
 'obelisk':  ('obelisk.jpg',    'obelisk.jpg',   'obelisk.mp3'),
 'abusimbel':('abusimbel.webp', 'abusimbel.jpg', 'abusimbel.mp3'),
 'ramses6':  ('ramses6.jpg',    None,            'ramses6.mp3'),
}

def dur_of(path):
    r = subprocess.run([FF,'-i',path], capture_output=True, text=True)
    m = re.search(r'Duration: (\d+):(\d+):(\d+\.?\d*)', r.stderr)
    return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))

def prep(src, dst, w, h):
    """توحيد المقاسات وتحويل كل الصيغ إلى JPG آمن"""
    vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
    subprocess.run([FF,'-y','-i',src,'-vf',vf,'-q:v','2',dst],
                   capture_output=True)
    assert os.path.exists(dst), f'prep failed {src}'

def build(site, photo, pano, audio):
    out = f'{VID}/{site}.mp4'
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f'[skip] {site}'); return
    adur = dur_of(f'{AUD}/{audio}')
    tail = 0.9
    total = adur + tail
    seg = total/3.0
    frames = lambda d: str(int(round(d*20)))
    # تجهيز المصادر
    ph = f'{TMP}/{site}_ph.jpg'
    prep(f'{IMG}/{photo}', ph, 2400, 1350)
    if pano:
        pa = f'{TMP}/{site}_pa.jpg'
        prep(f'{PANO}/{pano}', pa, 2600, 1500)
        mid = (f"[1:v]scale=1800:-2,crop=1280:720:y='(in_h-720)/2':"
               f"x='(in_w-1280)*min(t/{seg:.3f},1)',fps=20,trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[m];")
        inputs_mid = ['-loop','1','-t',f'{seg:.3f}','-i',pa]
        final_inputs = ['-loop','1','-t',f'{seg:.3f}','-i',pa]
    else:
        mid = (f"[1:v]scale=2400:-2,crop=1280:720:y='(in_h-720)*min(t/{seg:.3f},1)*0.5',"
               f"fps=20,trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[m];")
        inputs_mid = ['-loop','1','-t',f'{seg:.3f}','-i',ph]
        final_inputs = []
    fc = (
      f"[0:v]scale=2400:-2,zoompan=z='min(zoom+0.00055,1.22)':"
      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames(seg)}:s=1280x720:fps=20,"
      f"trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[a];"
      + mid +
      f"[2:v]scale=2400:-2,zoompan=z='if(eq(on,1),1.22,max(zoom-0.00055,1.0))':"
      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames(seg)}:s=1280x720:fps=20,"
      f"trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[b];"
      f"[a][m][b]concat=n=3:v=1:a=0,format=yuv420p,fade=t=in:st=0:d=1,fade=t=out:st={total-1.0:.3f}:d=1.0[v]"
    )
    cmd = [FF,'-y',
           '-loop','1','-t',f'{seg:.3f}','-i',ph,
           ] + inputs_mid + [
           '-loop','1','-t',f'{seg:.3f}','-i',ph,
           '-i',f'{AUD}/{audio}',
           '-filter_complex',fc,
           '-map','[v]','-map','3:a',
           '-t',f'{total:.3f}',
           '-c:v','libx264','-preset','veryfast','-crf','26','-r','20',
           '-c:a','aac','-b:a','64k','-ac','1',
           '-movflags','+faststart','-shortest', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        print(f'[FAIL] {site}: {r.stderr[-500:]}'); sys.exit(1)
    print(f'[OK] {site} -> {os.path.getsize(out)//1024} KB, dur={total:.1f}s')

if __name__ == '__main__':
    only = sys.argv[1:] or list(SITES)
    for s in only:
        build(s, *SITES[s])
    print('ALL DONE')

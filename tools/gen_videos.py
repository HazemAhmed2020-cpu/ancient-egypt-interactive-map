#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولّد فيديوهات المقدمة السينمائية — نسخة الجولة 3D
   (زوم على مشهد الدخول + تحريك داخل البانوراما + مشهد العمق + التعليق الصوتي)"""
import subprocess, os, re, sys

FF = subprocess.run(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],
                    capture_output=True, text=True).stdout.strip()
ROOT = '/home/user/ancient-egypt'
IMG, PANO, AUD, VID = f'{ROOT}/assets/img', f'{ROOT}/assets/pano', f'{ROOT}/assets/audio', f'{ROOT}/assets/video'
TMP = '/tmp/vidsrc'
os.makedirs(VID, exist_ok=True); os.makedirs(TMP, exist_ok=True)

# (صورة الدخول، بانوراما التحريك، صورة العمق، الصوت) — القديمة: (صورة، بانوراما، صورة، صوت)
SITES = {
 'giza':     (f'{PANO}/giza_sphinx.jpg', f'{PANO}/giza.jpg',        f'{PANO}/giza_base.jpg',   'giza.mp3'),
 'saqqara':  (f'{PANO}/saqqara_col.jpg', f'{PANO}/saqqara.jpg',     f'{PANO}/saqqara_base.jpg','saqqara.mp3'),
 'karnak':   (f'{PANO}/karnak_court.jpg',f'{PANO}/karnak.jpg',      f'{PANO}/karnak_deep.jpg', 'karnak.mp3'),
 'luxor':    (f'{PANO}/luxor_court.jpg', f'{PANO}/luxor.jpg',       f'{PANO}/luxor_col.jpg',   'luxor.mp3'),
 'deir':     (f'{PANO}/deir_low.jpg',    f'{PANO}/hatshepsut.jpg',  f'{PANO}/deir_hathor.jpg', 'hatshepsut.mp3'),
 # الباقي مؤقتاً بالأسلوب السابق حتى توليد مشاهد الدخول/العمق الخاصة بها
 'dendera': (f'{PANO}/dendera_facade.jpg',f'{PANO}/dendera.jpg',   f'{PANO}/dendera_roof.jpg','dendera.mp3'),
 'edfu':     (f'{PANO}/edfu_court.jpg',  f'{PANO}/edfu.jpg',        f'{PANO}/edfu_hall.jpg',   'edfu.mp3'),
 'komombo':  (f'{PANO}/komombo_court.jpg',f'{PANO}/komombo.jpg',    f'{PANO}/komombo_hall.jpg','komombo.mp3'),
 'philae':   (f'{PANO}/philae_col.jpg',  f'{PANO}/philae.jpg',      f'{PANO}/philae_kiosk.jpg','philae.mp3'),
 'obelisk':  (f'{PANO}/obelisk_head.jpg',f'{PANO}/obelisk.jpg',     f'{PANO}/obelisk_quarry.jpg','obelisk.mp3'),
 'abusimbel':(f'{PANO}/abusimbel_facadesm.jpg',f'{PANO}/abusimbel.jpg',f'{PANO}/abusimbel_sanc.jpg','abusimbel.mp3'),
 'gem':(f'{PANO}/gem_exterior.jpg',f'{PANO}/gem_stairs.jpg',f'{PANO}/gem_tut.jpg','gem.mp3'),
 'ramses6':  (f'{PANO}/ramses6_desc.jpg',f'{PANO}/ramses6_pillar.jpg',f'{PANO}/ramses6_pillar.jpg','ramses6.mp3'),
 'menna':    (f'{PANO}/menna_court.jpg', f'{PANO}/menna_hall.jpg',  f'{PANO}/menna_deep.jpg',  'menna.mp3'),
 'meresankh':(f'{PANO}/meresankh_court.jpg',f'{PANO}/meresankh_hall.jpg',f'{PANO}/meresankh_hathor.jpg','meresankh.mp3'),
}

def dur_of(path):
    r = subprocess.run([FF,'-i',path], capture_output=True, text=True)
    m = re.search(r'Duration: (\d+):(\d+):(\d+\.?\d*)', r.stderr)
    return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))

def prep(src, dst, w, h):
    vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
    subprocess.run([FF,'-y','-i',src,'-vf',vf,'-q:v','2',dst], capture_output=True)
    assert os.path.exists(dst), f'prep failed {src}'

def build(site, ent, pano, deep, audio):
    out = f'{VID}/{site}.mp4'
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f'[skip] {site}'); return
    adur = dur_of(f'{AUD}/{audio}')
    tail = 0.9
    total = adur + tail
    seg = total/3.0
    fr = lambda d: str(int(round(d*20)))
    ph = f'{TMP}/{site}_ent.jpg'; prep(ent, ph, 2400, 1350)
    pd = f'{TMP}/{site}_deep.jpg'; prep(deep, pd, 2400, 1350)
    if pano:
        pa = f'{TMP}/{site}_pa.jpg'; prep(pano, pa, 2600, 1500)
        mid = (f"[1:v]scale=1800:-2,crop=1280:720:y='(in_h-720)/2':"
               f"x='(in_w-1280)*min(t/{seg:.3f},1)',fps=20,trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[m];")
        in_mid = ['-loop','1','-t',f'{seg:.3f}','-i',pa]
    else:
        mid = (f"[1:v]scale=2400:-2,crop=1280:720:y='(in_h-720)*min(t/{seg:.3f},1)*0.5',"
               f"fps=20,trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[m];")
        in_mid = ['-loop','1','-t',f'{seg:.3f}','-i',ph]
    fc = (
      f"[0:v]scale=2400:-2,zoompan=z='min(zoom+0.00055,1.22)':"
      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr(seg)}:s=1280x720:fps=20,"
      f"trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[a];"
      + mid +
      f"[2:v]scale=2400:-2,zoompan=z='if(eq(on,1),1.22,max(zoom-0.00055,1.0))':"
      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr(seg)}:s=1280x720:fps=20,"
      f"trim=duration={seg:.3f},setpts=PTS-STARTPTS,setsar=1[b];"
      f"[a][m][b]concat=n=3:v=1:a=0,format=yuv420p,fade=t=in:st=0:d=1,fade=t=out:st={total-1.0:.3f}:d=1.0[v]"
    )
    cmd = [FF,'-y','-loop','1','-t',f'{seg:.3f}','-i',ph,
           ] + in_mid + [
           '-loop','1','-t',f'{seg:.3f}','-i',pd,
           '-i',f'{AUD}/{audio}','-filter_complex',fc,
           '-map','[v]','-map','3:a','-t',f'{total:.3f}',
           '-c:v','libx264','-preset','veryfast','-crf','26','-r','20',
           '-c:a','aac','-b:a','64k','-ac','1',
           '-movflags','+faststart','-shortest', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        print(f'[FAIL] {site}: {r.stderr[-400:]}'); sys.exit(1)
    print(f'[OK] {site} -> {os.path.getsize(out)//1024} KB, dur={total:.1f}s')

if __name__ == '__main__':
    only = sys.argv[1:] or list(SITES)
    for s in only:
        build(s, *SITES[s])
    print('ALL DONE')

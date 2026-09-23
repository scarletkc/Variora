from pathlib import Path
import struct
import json
import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter

OUT = Path('/workspace/scratch/ab30d081b35e/seaside')
OUT.mkdir(exist_ok=True)
BPM = 104
BEAT = 60 / BPM
SR = 44100
PPQ = 480
rng = np.random.default_rng(92016)

# Original composition: two-bar introduction, A, B, A variation, cadence.
# All melody pitches and rhythms are composed here explicitly.
chords = {
    'D9':  (38, [54, 57, 61, 64, 66]),
    'G7':  (43, [54, 57, 59, 62, 66]),
    'A6':  (45, [52, 57, 61, 64, 66]),
    'Fs7': (42, [52, 57, 61, 64]),
    'Bm7': (35, [54, 57, 59, 62, 66]),
    'Em7': (40, [55, 59, 62, 66]),
    'A7':  (45, [55, 57, 61, 64]),
    'D7':  (38, [54, 57, 60, 64]),
    'Fsd': (42, [54, 58, 61, 64]),
}
progression = ['D9', 'G7'] + [
    'G7', 'A6', 'Fs7', 'Bm7', 'Em7', 'A7', 'D9', 'D7',
] + [
    'G7', 'A6', 'Fs7', 'Bm7', 'Em7', 'Fsd', 'Bm7', 'A7',
] + [
    'G7', 'A6', 'Fs7', 'Bm7', 'Em7', 'A7', 'D9', 'A7',
] + ['G7', 'D9']

# MIDI note numbers; None is a rest. Each bar has four quarter-note beats.
A = [
    [(None,.5),(74,.5),(78,.5),(81,.5),(78,1),(76,.5),(74,.5)],
    [(73,.5),(76,.5),(78,1),(76,.5),(73,.5),(71,.5),(69,.5)],
    [(73,.5),(76,.5),(78,1.5),(76,.5),(73,1)],
    [(74,1),(73,.5),(71,.5),(69,1),(66,.5),(69,.5)],
    [(71,.5),(74,.5),(78,1),(76,.5),(74,.5),(71,1)],
    [(73,.5),(76,.5),(79,.5),(78,.5),(76,1),(73,.5),(69,.5)],
    [(74,1.5),(73,.5),(69,1),(66,.5),(69,.5)],
    [(72,.5),(74,.5),(78,1),(76,.5),(74,.5),(72,.5),(69,.5)],
]
B = [
    [(71,.5),(74,.5),(78,.5),(81,.5),(83,1),(81,.5),(78,.5)],
    [(81,1),(78,.5),(76,.5),(73,1),(76,.5),(78,.5)],
    [(81,1.5),(80,.5),(78,.5),(76,.5),(73,1)],
    [(78,.5),(81,.5),(83,1),(81,.5),(78,.5),(74,1)],
    [(79,1),(78,.5),(76,.5),(74,.5),(71,.5),(74,1)],
    [(73,.5),(70,.5),(66,1),(70,.5),(73,.5),(76,1)],
    [(78,1.5),(76,.5),(74,1),(73,.5),(71,.5)],
    [(73,.5),(76,.5),(79,1),(78,.5),(76,.5),(73,.5),(69,.5)],
]
AV = [
    A[0], A[1],
    [(73,.5),(76,.5),(81,1),(78,.5),(76,.5),(73,1)],
    [(74,1),(78,.5),(76,.5),(74,.5),(73,.5),(71,1)],
    A[4], A[5],
    [(78,1),(76,.5),(74,.5),(73,.5),(69,.5),(74,1)],
    [(76,1),(73,.5),(71,.5),(69,1),(None,1)],
]
melody = [
    [(None,4)], [(None,3),(69,.5),(73,.5)],
] + A + B + AV + [
    [(71,1),(74,1),(73,.5),(76,.5),(73,1)],
    [(74,4)],
]
assert len(melody) == len(progression) == 28
assert all(abs(sum(d for _, d in bar) - 4) < .00001 for bar in melody)

events = []
def add(inst, note, start, dur, vel):
    if note is None:
        return
    # Small timing and velocity variations preserve the written rhythms.
    shift = rng.uniform(-.009,.009) if inst not in ['pad'] else 0
    velocity = int(np.clip(vel + rng.integers(-3,4), 1, 120))
    events.append(dict(inst=inst, note=int(note), start=max(0,start+shift),
                       dur=float(dur), vel=velocity))

for bar, notes in enumerate(melody):
    t = bar * 4
    for n, d in notes:
        add('piano', n, t, max(.10,d*.91), 82 if 10 <= bar < 18 else 77)
        t += d

for bar, name in enumerate(progression):
    segments = [(0,4,name)]
    if bar == 26:
        segments = [(0,2,'G7'), (2,2,'A7')]
    for off, length, cname in segments:
        root, voicing = chords[cname]
        t = bar*4 + off
        for i, n in enumerate(voicing[:4]):
            add('pad', n, t+.025*i, length-.06, 42 if bar >= 10 else 35)
        # Sparse, warm chord punctuation under the melodic piano.
        if bar not in [0,27]:
            for pos in ([0,2.5] if length == 4 else [0]):
                for i,n in enumerate(voicing[:3]):
                    add('comp', n, t+pos+.018*i, .68, 49)
        arp = sorted(set(voicing))
        pattern = [0,2,3,1,2,3,1,2]
        for i in range(int(length*2)):
            if bar == 27 and i > 3:
                continue
            n = arp[pattern[i % 8] % len(arp)] + 12
            add('marimba', n, t+i*.5, .34, 48 if i % 2 == 0 else 39)
        add('bass', root, t, min(1.65,length-.1), 65)
        if length == 4 and bar != 27:
            add('bass', root+7, t+2, .7, 54)
            add('bass', root+12, t+3, .6, 48)
    # Light shaker and sidestick: walking pace without an aggressive beat.
    if 2 <= bar <= 25:
        for step in range(8):
            add('drums',42,bar*4+step*.5,.11,35 if step % 2 else 27)
        for pos in [0,2]:
            add('drums',36,bar*4+pos,.16,49 if pos == 0 else 40)
        for pos in [1,3]:
            add('drums',37,bar*4+pos,.12,42)

configs = {
    'piano':   (0, 0,  64, 100, 'Melody - Summer Walk'),
    'comp':    (1, 4,  46,  77, 'Warm Electric Piano'),
    'marimba': (2, 12, 84,  82, 'Marimba - Sunlight'),
    'pad':     (3, 89, 60,  60, 'Warm Pad - Sea Breeze'),
    'bass':    (4, 33, 64,  95, 'Soft Finger Bass'),
    'drums':   (9, 0,  68,  73, 'Light Walking Percussion'),
}

def vlq(n):
    b = [int(n) & 127]
    n = int(n) >> 7
    while n:
        b.insert(0,(n & 127) | 128)
        n >>= 7
    return bytes(b)

def meta(kind, value):
    return bytes([255,kind]) + vlq(len(value)) + value

def chunk(items):
    data = bytearray()
    last = 0
    for tick, priority, raw in sorted(items, key=lambda x:(x[0],x[1])):
        data.extend(vlq(tick-last))
        data.extend(raw)
        last = tick
    data.extend(b'\x00\xff\x2f\x00')
    return b'MTrk' + struct.pack('>I',len(data)) + data

conductor = [
    (0,0,meta(3,b'Seaside Stroll - Original Composition')),
    (0,1,meta(0x51,int(round(60000000/BPM)).to_bytes(3,'big'))),
    (0,2,meta(0x58,bytes([4,2,24,8]))),
    (0,3,meta(0x59,bytes([2,0]))),
]
for bar, section in [(0,'Intro'),(2,'A - Promenade'),(10,'B - Horizon'),
                     (18,'A variation'),(26,'Cadence')]:
    conductor.append((bar*4*PPQ,5,meta(6,section.encode())))
tracks = [chunk(conductor)]
for inst,(channel,program,pan,volume,name) in configs.items():
    items = [(0,-5,meta(3,name.encode())),(0,-4,bytes([0xC0+channel,program]))]
    for cc,value in [(7,volume),(10,pan),(91,35 if inst != 'bass' else 9),(93,8)]:
        items.append((0,-3,bytes([0xB0+channel,cc,value])))
    for e in events:
        if e['inst'] != inst:
            continue
        start=round(e['start']*PPQ)
        end=round((e['start']+e['dur'])*PPQ)
        items.append((start,1,bytes([0x90+channel,e['note'],e['vel']])))
        items.append((end,0,bytes([0x80+channel,e['note'],0])))
    items.append((112*PPQ+PPQ,2,bytes([0xB0+channel,123,0])))
    tracks.append(chunk(items))
mid = b'MThd'+struct.pack('>IHHH',6,1,len(tracks),PPQ)+b''.join(tracks)
(OUT/'seaside_stroll.mid').write_bytes(mid)

# Render the exact same notes with deterministic, locally synthesized timbres.
# No audio-generating model, recording, or borrowed melody is used.
seconds = 112*BEAT + 3.5
mix = np.zeros((int(seconds*SR),2),np.float64)

def release_gate(t, duration, release):
    return np.exp(-np.maximum(t-duration,0)/release)

def tone(inst, note, duration, velocity):
    tail = .85 if inst in ['piano','comp','marimba'] else .65
    if inst == 'drums':
        tail=.09
    t = np.arange(int((duration+tail)*SR),dtype=np.float64)/SR
    f = 440*2**((note-69)/12)
    v = velocity/100
    if inst == 'piano':
        y=np.zeros_like(t)
        for h,a,decay in [(1,1.0,1.55),(2,.34,.83),(3,.17,.53),
                          (4,.075,.36),(5,.034,.24),(7,.014,.16)]:
            y += a*np.sin(2*np.pi*f*h*(1+.00013*h*h)*t)*np.exp(-t/decay)
        y += .13*np.sin(2*np.pi*f*1.0012*t)*np.exp(-t/.95)
        y *= (1-np.exp(-t/.005))*release_gate(t,duration,.20)
        return y*.16*v
    if inst == 'comp':
        phase=2*np.pi*f*t
        y=np.sin(phase+.55*np.exp(-t/.21)*np.sin(2*phase))
        y += .14*np.sin(phase*2)*np.exp(-t/.28)
        y *= (1-np.exp(-t/.007))*np.exp(-t/.82)*release_gate(t,duration,.18)
        return y*.095*v
    if inst == 'marimba':
        y=np.sin(2*np.pi*f*t)*np.exp(-t/.28)
        y+=.25*np.sin(2*np.pi*f*4.01*t)*np.exp(-t/.055)
        y+=.055*np.sin(2*np.pi*f*9.13*t)*np.exp(-t/.025)
        y *= (1-np.exp(-t/.0017))*release_gate(t,duration,.10)
        return y*.10*v
    if inst == 'pad':
        y=np.zeros_like(t)
        for detune in [.998,1.002]:
            for h,a in [(1,.5),(2,.13),(3,.045)]:
                y+=a*np.sin(2*np.pi*f*h*detune*t)
        env=(1-np.exp(-t/.24))*release_gate(t,duration,.22)
        return y*env*.041*v
    if inst == 'bass':
        phase=2*np.pi*f*t
        y=np.sin(phase)+.27*np.sin(phase*2)*np.exp(-t/.30)
        y+=.08*np.sin(phase*3)*np.exp(-t/.11)
        y *= (1-np.exp(-t/.008))*np.exp(-t/1.8)*release_gate(t,duration,.085)
        return y*.19*v
    noise=rng.normal(0,1,len(t))
    if note == 36:
        phase=2*np.pi*(48*t + 44*.019*(1-np.exp(-t/.019)))
        y=np.sin(phase)*np.exp(-t/.075)
        return y*.15*v
    if note == 37:
        y=(np.sin(2*np.pi*1750*t)+.4*np.sin(2*np.pi*2510*t))*np.exp(-t/.014)
        y+=.15*noise*np.exp(-t/.009)
        return y*.066*v
    y=np.concatenate(([0],np.diff(noise)))*np.exp(-t/.026)
    return y*.024*v

gains={'piano':(0.72,0.70),'comp':(.81,.57),'marimba':(.53,.85),
       'pad':(.72,.72),'bass':(.71,.71),'drums':(.67,.73)}
for e in events:
    wave=tone(e['inst'],e['note'],e['dur']*BEAT,e['vel'])
    start=int(e['start']*BEAT*SR)
    stop=min(start+len(wave),len(mix))
    g=gains[e['inst']]
    mix[start:stop,0]+=wave[:stop-start]*g[0]
    mix[start:stop,1]+=wave[:stop-start]*g[1]

# Stereo early reflections and a quiet, diffuse room tail.
dry=mix.copy()
for channel in range(2):
    for delay,amp in [(0.043,.045),(.071,.040),(.113,.029),(.179,.022),
                      (.263,.016),(.347,.012),(.461,.008)]:
        shift=int((delay+channel*.004)*SR)
        source=dry[:-shift,1-channel]
        source=lfilter([.16],[1,-.84],source)
        mix[shift:,channel]+=source*amp
mix -= mix.mean(axis=0)
mix /= max(1,np.max(np.abs(mix))/.88)
peak=float(np.max(np.abs(mix)))
fade=int(1.2*SR)
mix[-fade:] *= np.linspace(1,0,fade)[:,None]
wavfile.write(OUT/'seaside_stroll.wav',SR,(mix*32767).astype(np.int16))
summary={'title':'海风慢慢 / Seaside Stroll','bpm':BPM,'key':'D major',
         'bars':28,'duration_seconds':round(seconds,2),'notes':len(events),
         'midi_tracks':len(tracks),'sample_peak':round(peak,4),
         'rms':round(float(np.sqrt(np.mean(mix**2))),4)}
print(json.dumps(summary,ensure_ascii=False,indent=2))

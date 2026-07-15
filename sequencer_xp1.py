import mido
import threading
import time

BPM       = 120
STEPS     = 16
NOTE_SEQ  = 36
VELOCITY  = 100

CANAL_STEPS = 7
NOTE_STEPS_START = 48

CTRL_PLAY     = 0
CTRL_RESET    = 1
CTRL_BPM_UP   = 2
CTRL_BPM_DOWN = 3

steps        = [False] * STEPS
current_step = 0
playing      = False
bpm          = BPM

def find(ports, kw):
    return next((p for p in ports if kw.lower() in p.lower()), None)

xp1_in  = find(mido.get_input_names(),  "XP1")
xp1_out = find(mido.get_output_names(), "XP1")
iac_out = find(mido.get_output_names(), "IAC")

print(f"XP1 in  : {xp1_in}")
print(f"XP1 out : {xp1_out}")
print(f"IAC out : {iac_out}")

if not iac_out:
    print("⚠️  IAC Driver non trouvé")
    exit()

def led(out, step, on):
    t = 'note_on' if on else 'note_off'
    out.send(mido.Message(t, channel=CANAL_STEPS,
                          note=NOTE_STEPS_START + step,
                          velocity=127 if on else 0))

def clock(xp1, iac):
    global current_step, playing, bpm
    while True:
        if playing:
            dt = 60 / bpm / 4
            led(xp1, current_step, True)
            if steps[current_step]:
                iac.send(mido.Message('note_on',  channel=0, note=NOTE_SEQ, velocity=VELOCITY))
            time.sleep(dt * 0.5)
            if steps[current_step]:
                iac.send(mido.Message('note_off', channel=0, note=NOTE_SEQ, velocity=0))
            led(xp1, current_step, steps[current_step])
            time.sleep(dt * 0.5)
            current_step = (current_step + 1) % STEPS
        else:
            time.sleep(0.01)

def handle(msg, xp1):
    global playing, current_step, bpm
    if msg.type != 'note_on' or msg.velocity == 0:
        return
    ch, note = msg.channel, msg.note

    if ch == CANAL_STEPS and NOTE_STEPS_START <= note < NOTE_STEPS_START + STEPS:
        i = note - NOTE_STEPS_START
        steps[i] = not steps[i]
        led(xp1, i, steps[i])
        print(f"Step {i+1:2d} {'■' if steps[i] else '□'}")

    elif ch == CANAL_STEPS:
        if note == CTRL_PLAY:
            playing = not playing
            if not playing: current_step = 0
            print("▶ PLAY" if playing else "■ STOP")
        elif note == CTRL_RESET:
            current_step = 0
            print("↩ RESET")
        elif note == CTRL_BPM_UP:
            bpm = min(bpm + 5, 200)
            print(f"BPM ↑ {bpm}")
        elif note == CTRL_BPM_DOWN:
            bpm = max(bpm - 5, 60)
            print(f"BPM ↓ {bpm}")

with mido.open_input(xp1_in)   as inp, \
     mido.open_output(xp1_out) as xp1, \
     mido.open_output(iac_out) as iac:

    print("\n🎹 Séquenceur XP1 prêt")
    print("SAMPLER=steps | HOT CUE: pad1=Play pad2=Reset pad3=BPM+ pad4=BPM-\n")
    threading.Thread(target=clock, args=(xp1, iac), daemon=True).start()
    for msg in inp:
        handle(msg, xp1)

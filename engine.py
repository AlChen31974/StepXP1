import mido
import threading
import time
import random
import queue

# ── Constantes ────────────────────────────────────────────────────────
NUM_STEPS       = 32
NUM_PATTERNS    = 6
DEFAULT_BPM     = 120
DEFAULT_NOTE    = 60    # C3
VELOCITY        = 100
CLOCK_TIMEOUT   = 0.3   # secondes sans clock IAC → mode standalone

# Ambitus utilisé par la randomisation (basse/mélodie) : 2 octaves autour de C3
RANDOM_NOTE_MIN = 36    # C2
RANDOM_NOTE_MAX = 60    # C4

# Vélocités de couleur des pads XP1 (déterminées empiriquement avec
# test_pad_colors.py — la XP1 encode teinte + intensité dans la vélocité)
LED_OFF            = 0
LED_PLAYHEAD       = 106   # rouge — pad en cours de lecture, quel que soit le mode
LED_BASS_ANCHOR    = 35    # orange vif — note d'ancrage (root/fifth) en mode Basse
LED_BASS_PASSING   = 100   # orange sourd — note de passage en mode Basse
LED_MELODY_ANCHOR  = 120   # violet vif — note sur la tonique/quinte en mode Mélodie
LED_MELODY_PASSING = 55    # violet doux — autres notes en mode Mélodie

# ── Mapping pad physique ↔ step (0-indexed) ───────────────────────────
# Layout 4 rangées × 8 colonnes (gauche=col 0-3, droite=col 4-7)
# Gauche : Ch8 (ch=7), notes 48-63  |  Droite : Ch10 (ch=9), notes 48-63
# note i (0-15) : row = i//4, col_g = i%4, col_d = i%4 + 4
# step = row * 8 + col

PAD_TO_STEP: dict[tuple[int, int], int] = {}
STEP_TO_PAD: dict[int, tuple[int, int]] = {}

for _i in range(16):
    _row        = _i // 4
    _col        = _i % 4
    _step_left  = _row * 8 + _col        # 0,1,2,3 / 8,9,10,11 / ...
    _step_right = _row * 8 + _col + 4    # 4,5,6,7 / 12,13,14,15 / ...
    PAD_TO_STEP[(7, 48 + _i)] = _step_left
    PAD_TO_STEP[(9, 48 + _i)] = _step_right
    STEP_TO_PAD[_step_left]   = (7, 48 + _i)
    STEP_TO_PAD[_step_right]  = (9, 48 + _i)

# ── Boutons XP1 (ch 0-indexed) ────────────────────────────────────────
BTN = {
    # Transport
    "play":       (0,  115),   # INT gauche
    "stop":       (1,  115),   # INT droite
    # BPM
    "bpm_m1":     (0,  39),    # Page ◄ gauche  → BPM −1
    "bpm_p1":     (0,  47),    # Page ► gauche  → BPM +1
    "bpm_m5":     (1,  39),    # Page ◄ droite  → BPM −5
    "bpm_p5":     (1,  47),    # Page ► droite  → BPM +5
    # Note editing (step sélectionné)
    "note_m_st":  (0,  10),    # Semitone − gauche → −1 demi-ton
    "note_p_st":  (0,  121),   # Semitone + gauche → +1 demi-ton
    "note_m_oct": (1,  10),    # Semitone − droite → −1 octave (step sélectionné)
    "note_p_oct": (1,  121),   # Semitone + droite → +1 octave (step sélectionné)
    "pattern_oct_m": (1, 101),  # SHIFT + Semitone − droite → −1 octave (tout le pattern)
    "pattern_oct_p": (1, 100),  # SHIFT + Semitone + droite → +1 octave (tout le pattern)
    # Longueur de pattern
    "len_8":      (1,  26),    # Master tempo droite
    "len_16":     (1,  88),    # Beat sync droite
    "len_32":     (1,  21),    # Slip reverse droite
    # Fonctions
    "reverse":          (0,  21),    # Slip reverse gauche
    "rnd_steps":        (0,  26),    # Master tempo gauche
    "rnd_notes":        (0,  88),    # Beat sync gauche
    "mute":             (0,  104),   # Silent cue gauche
    "clear_pattern":    (1,  104),   # Silent cue droite
    # Mode de génération (randomisation des notes)
    "gen_mode_bass":    (0,  53),    # Quantize gauche → mode Basse
    "gen_mode_melody":  (1,  53),    # Quantize droite → mode Mélodie
    # Modes perpétuels (SHIFT + bouton)
    "perp_rnd_notes":   (0,  96),    # SHIFT + Master tempo gauche
    "perp_rnd_steps":   (0,  92),    # SHIFT + Beat sync gauche
    # Sélection sortie MIDI
    "out_iac":  (1, 16),   # LOOP IN droite          → IAC seulement
    "out_hw":   (1, 17),   # LOOP OUT droite          → HW seulement
    "out_both": (1, 77),   # SHIFT + LOOP OUT droite  → les deux
    # Changements de mode (boutons de mode XP1)
    "mode_sampler_l":   (0, 34),   # SAMPLER gauche
    "mode_sampler_r":   (1, 34),   # SAMPLER droite
    "mode_beatjump_l":  (0, 32),   # BEAT JUMP gauche
    "mode_beatjump_r":  (1, 32),   # BEAT JUMP droite
    # Sélection de pattern (SLIDE FX — note_on = activer)
    "pattern_0":  (4,  112),   # SLIDE FX 1 gauche
    "pattern_1":  (4,  113),   # SLIDE FX 2 gauche
    "pattern_2":  (4,  114),   # SLIDE FX 3 gauche
    "pattern_3":  (5,  112),   # SLIDE FX 1 droite
    "pattern_4":  (5,  113),   # SLIDE FX 2 droite
    "pattern_5":  (5,  114),   # SLIDE FX 3 droite
    # SHIFT + pattern → copie le pattern actif dans la cible + bascule dessus
    "pattern_copy_0": (4, 115),   # SHIFT + SLIDE FX 1 gauche
    "pattern_copy_1": (4, 116),   # SHIFT + SLIDE FX 2 gauche
    "pattern_copy_2": (4, 117),   # SHIFT + SLIDE FX 3 gauche
    "pattern_copy_3": (5, 115),   # SHIFT + SLIDE FX 1 droite
    "pattern_copy_4": (5, 116),   # SHIFT + SLIDE FX 2 droite
    "pattern_copy_5": (5, 117),   # SHIFT + SLIDE FX 3 droite
}

BTN_LOOKUP: dict[tuple[int, int], str] = {v: k for k, v in BTN.items()}

# ── Encodeur central ───────────────────────────────────────────────────
# Control Change relatif : value=1 → +1 cran, value=127 → −1 cran
# (déterminé empiriquement avec test_encoder.py)
ENCODER_CH      = 6
ENCODER_CONTROL = 64

# ── Mapping BEAT JUMP pads → index dans la gamme (0-31) ──────────────
# Même layout physique que SAMPLER, mais notes 32-47
BEATJUMP_TO_IDX: dict[tuple[int, int], int] = {}
for _i in range(16):
    _row = _i // 4
    _col = _i % 4
    BEATJUMP_TO_IDX[(7, 32 + _i)] = _row * 8 + _col        # gauche
    BEATJUMP_TO_IDX[(9, 32 + _i)] = _row * 8 + _col + 4    # droite

# ── Gammes (intervalles depuis la tonique) ────────────────────────────
SCALES: dict[str, list[int]] = {
    "Majeur":           [0, 2, 4, 5, 7, 9, 11],
    "Mineur":           [0, 2, 3, 5, 7, 8, 10],
    "Pentatonique maj": [0, 2, 4, 7, 9],
    "Pentatonique min": [0, 3, 5, 7, 10],
    "Dorien":           [0, 2, 3, 5, 7, 9, 10],
    "Mixolydien":       [0, 2, 4, 5, 7, 9, 10],
    "Blues":            [0, 3, 5, 6, 7, 10],
    "Chromatique":      list(range(12)),
}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class SequencerEngine:
    """
    Séquenceur 32 steps, 6 patterns, esclave du clock Ableton.
    Joue librement si Ableton est arrêté (clock interne).
    """

    def __init__(self):
        self.bpm            = DEFAULT_BPM
        self.playing        = False
        self.current_step   = 0
        self.selected_step  = None     # step sélectionné pour l'édition (None = aucun)
        self.pattern_length = 16       # 8, 16 ou 32
        self.reverse        = False
        self.perp_rnd_notes = False
        self.perp_rnd_steps = False
        self.muted          = False
        self.gen_mode       = "bass"        # "bass" ou "melody" (randomisation des notes)
        self.ui_mode        = "sequencer"   # "sequencer" ou "scale"
        self._pending_start    = False   # en attente du prochain début de barre
        self._pending_pattern: int | None = None  # pattern à appliquer en fin de boucle
        self._ableton_playing  = False   # True seulement si transport Ableton tourne
        self._shift_held       = False   # SHIFT du XP1 maintenu
        self.midi_out_mode     = "BOTH"  # "IAC", "HW" ou "BOTH"
        self._pad_press_time: dict[int, float] = {}  # step → heure du note_on
        self._held_step: int | None = None   # step SAMPLER actuellement tenu enfoncé (édition via encodeur)
        self.scale_root     = 0        # 0=C, 1=C#, ... 11=B
        self.scale_mode     = "Majeur"

        # 6 patterns indépendants (steps on/off)
        self.patterns = [[False] * NUM_STEPS for _ in range(NUM_PATTERNS)]
        self.active_pattern = 0

        # Notes par pattern (chaque pattern a ses propres notes)
        self.pattern_notes = [[DEFAULT_NOTE] * NUM_STEPS for _ in range(NUM_PATTERNS)]

        # Suivi interne
        self._active_note     = None
        self._last_clock_time = 0.0
        self._last_lit_step: int | None = None   # dernier pad allumé en couleur playhead
        self._led_queue: queue.Queue = queue.Queue()   # (step, velocity) → _led_writer_loop
        # RLock (verrou réentrant) : autorise un même thread à reprendre son
        # propre verrou sans se bloquer (nécessaire car _handle_button, appelé
        # sous verrou depuis _xp1_loop, appelle des méthodes qui prennent
        # aussi le verrou quand elles sont appelées directement par la GUI).
        self._lock            = threading.RLock()

        # ── Ports MIDI ────────────────────────────────────────────────
        xp1_in  = self._find("in",  "XP1")
        xp1_out = self._find("out", "XP1")
        iac_in  = self._find("in",  "IAC")
        iac_out = self._find("out", "IAC")
        hw_out  = self._find("out", "PreSonus")

        print(f"XP1 in  : {xp1_in}")
        print(f"XP1 out : {xp1_out}")
        print(f"IAC in  : {iac_in}")
        print(f"IAC out : {iac_out}")
        print(f"HW out  : {hw_out or 'non connecté'}")

        if not iac_out:
            raise RuntimeError("IAC Driver introuvable en sortie")

        self._xp1_in  = mido.open_input(xp1_in)   if xp1_in  else None
        self._xp1_out = mido.open_output(xp1_out)  if xp1_out else None
        self._iac_in  = mido.open_input(iac_in)    if iac_in  else None
        self._iac_out = mido.open_output(iac_out)
        self._hw_out  = mido.open_output(hw_out)   if hw_out  else None

    def _midi_send(self, msg: mido.Message):
        """Envoie selon midi_out_mode : IAC, HW ou BOTH."""
        if self.midi_out_mode in ("IAC", "BOTH"):
            self._iac_out.send(msg)
        if self.midi_out_mode in ("HW", "BOTH") and self._hw_out:
            try:
                self._hw_out.send(msg)
            except Exception as e:
                print(f"[HW out] erreur : {e}")

    # ── Propriétés : pattern et notes courants ────────────────────────

    @property
    def steps(self) -> list[bool]:
        return self.patterns[self.active_pattern]

    @property
    def step_notes(self) -> list[int]:
        return self.pattern_notes[self.active_pattern]

    # ── Démarrage ─────────────────────────────────────────────────────

    def start(self):
        threading.Thread(target=self._clock_loop, daemon=True).start()
        threading.Thread(target=self._led_writer_loop, daemon=True).start()
        if self._xp1_in:
            threading.Thread(target=self._xp1_loop, daemon=True).start()
        if self._iac_in:
            threading.Thread(target=self._iac_loop, daemon=True).start()
        print("Séquenceur prêt")

    def _led_writer_loop(self):
        """Envoie les messages de couleur des pads XP1 depuis un thread dédié,
        pour que l'I/O MIDI (parfois lente) ne retarde jamais la lecture du
        clock Ableton dans _iac_loop."""
        while True:
            step, velocity = self._led_queue.get()
            if not self._xp1_out or step not in STEP_TO_PAD:
                continue
            ch, note = STEP_TO_PAD[step]
            self._xp1_out.send(mido.Message('note_on', channel=ch, note=note, velocity=velocity))

    # ── Avance d'un step (utilisé par les deux modes clock) ──────────────

    def _reset_playhead(self, step: int = 0):
        """Déplace le curseur de lecture sans passer par _tick (démarrage,
        reset, changement de longueur...). Restaure d'abord la couleur
        statique de l'ancien pad playhead pour ne pas le laisser bloqué en rouge."""
        if self._last_lit_step is not None and self._last_lit_step != step:
            self._led(self._last_lit_step, self._step_led_velocity(self._last_lit_step))
            self._last_lit_step = None
        self.current_step = step

    def _tick(self):
        """Joue le step courant et avance au suivant. Appelé sous _lock."""
        # Note-off de la note précédente avant tout
        self._send_note_off()

        step = self.current_step
        # Restaure la couleur statique de l'ancien pad playhead avant d'éclairer le nouveau
        if self._last_lit_step is not None and self._last_lit_step != step:
            self._led(self._last_lit_step, self._step_led_velocity(self._last_lit_step))
        self._led(step, LED_PLAYHEAD)
        self._last_lit_step = step

        if self.steps[step] and not self.muted:
            note = self.step_notes[step]
            self._midi_send(mido.Message('note_on', channel=0,
                                         note=note, velocity=VELOCITY))
            self._active_note = note

        if self.reverse:
            next_step = (step - 1) % self.pattern_length
        else:
            next_step = (step + 1) % self.pattern_length

        if next_step == 0:
            if self.perp_rnd_notes: self.randomize_notes()
            if self.perp_rnd_steps: self.randomize_steps()
            # Changement de pattern quantisé : appliqué en fin de boucle
            if self._pending_pattern is not None:
                self.active_pattern = self._pending_pattern
                self._pending_pattern = None
                self._refresh_all_leds()

        self.current_step = next_step

    # ── Thread clock interne (mode standalone) ───────────────────────────

    def _clock_loop(self):
        while True:
            if not self.playing or self._ableton_playing:
                # Pendant qu'Ableton pilote le clock, ce thread n'a rien à faire :
                # on ralentit son réveil pour ne pas concurrencer le GIL avec
                # _iac_loop (thread temps-réel qui lit le clock MIDI d'Ableton).
                time.sleep(0.02 if self._ableton_playing else 0.005)
                continue
            dt = 60 / self.bpm / 4
            with self._lock:
                self._tick()
            time.sleep(dt)

    # ── Thread clock IAC — pilote les steps depuis Ableton ───────────────

    def _iac_loop(self):
        step_pulse = 0   # avance d'un step tous les 6 pulses
        bar_pulse  = 0   # position dans la barre (0–95, soit 4 temps)
        quarter_pulse_count = 0    # compte les pulses jusqu'à une noire (24 = 1 noire)
        quarter_start_time  = None

        for msg in self._iac_in:
            if msg.type == 'clock':
                now = time.time()
                # BPM mesuré sur une noire entière (24 pulses) plutôt que sur
                # une seule pulsion : une pulsion isolée est trop bruitée
                # (jitter OS/USB) et faisait trembler l'affichage du tempo.
                if quarter_start_time is None:
                    quarter_start_time = now
                quarter_pulse_count += 1
                if quarter_pulse_count >= 24:
                    elapsed = now - quarter_start_time
                    if 0 < elapsed < 2.0:
                        raw = 60 / elapsed
                        self.set_bpm(round(self.bpm * 0.7 + raw * 0.3))
                    quarter_start_time = now
                    quarter_pulse_count = 0
                self._last_clock_time = now

                bar_pulse = (bar_pulse + 1) % 96

                # Déclenchement quantisé au prochain début de barre
                if self._pending_start and bar_pulse == 0:
                    with self._lock:
                        self._pending_start = False
                        self._reset_playhead(0)
                        self.playing = True
                        step_pulse = 0
                        # Joue le step 0 tout de suite : sinon il fallait attendre
                        # 6 pulses de plus (1/16ème de temps) avant la 1ère note,
                        # d'où le décalage constant entendu par rapport à Ableton.
                        self._tick()
                        print("▶ Départ quantisé !")

                if self.playing and self._ableton_playing:
                    step_pulse += 1
                    if step_pulse >= 6:
                        step_pulse = 0
                        with self._lock:
                            self._tick()

            elif msg.type == 'start':
                bar_pulse  = 0
                step_pulse = 0
                self._ableton_playing = True
                with self._lock:
                    self._reset_playhead(0)
                    self._pending_start = False
                    self.playing = True
                    self._tick()   # joue le step 0 dès le 'start', même raison que ci-dessus
                    print("↩ Start Ableton")

            elif msg.type == 'continue':
                self._ableton_playing = True
                with self._lock:
                    if not self.playing:
                        self.playing = True
                        print("↩ Continue Ableton")

            elif msg.type == 'stop':
                step_pulse = 0
                bar_pulse  = 0
                self._ableton_playing = False

    # ── Thread XP1 ────────────────────────────────────────────────────

    def _xp1_loop(self):
        for msg in self._xp1_in:
            # Verrou partagé avec _tick() : évite qu'une modif manuelle (toggle,
            # édition de note...) parte en concurrence avec l'avance du curseur
            # et se fasse écraser/déplacer sans ordre garanti.
            with self._lock:
                self._handle_xp1(msg)

    def _handle_xp1(self, msg):
        # Encodeur central : n'agit que si un pad SAMPLER est tenu enfoncé
        if msg.type == 'control_change':
            if msg.channel == ENCODER_CH and msg.control == ENCODER_CONTROL \
                    and self._held_step is not None:
                delta = 1 if msg.value == 1 else -1 if msg.value == 127 else 0
                if delta:
                    self.set_step_note(self._held_step,
                                       self.step_notes[self._held_step] + delta)
            return

        if msg.type not in ('note_on', 'note_off'):
            return

        ch_note = (msg.channel, msg.note)
        pressed = (msg.type == 'note_on' and msg.velocity > 0)

        # SHIFT tracking (Ch7 Note 64)
        if ch_note == (6, 64):
            self._shift_held = pressed
            return

        # Pads BEAT JUMP → assigne une note de la gamme au step sélectionné
        if pressed and ch_note in BEATJUMP_TO_IDX:
            self._assign_scale_note(BEATJUMP_TO_IDX[ch_note])
            return

        # Pads SAMPLER — note_on : sélectionne immédiatement + enregistre l'heure
        if ch_note in PAD_TO_STEP:
            step = PAD_TO_STEP[ch_note]
            if pressed:
                self.selected_step = step
                self._held_step = step   # tant que tenu : l'encodeur édite sa note
                self._pad_press_time[step] = time.time()
            else:
                if self._held_step == step:
                    self._held_step = None
                # note_off : court appui = toggle, long appui = sélection seule
                held = time.time() - self._pad_press_time.pop(step, time.time())
                if held < 0.35:
                    self.toggle_step(step)
            return

        # Boutons nommés → seulement à l'appui
        if pressed:
            btn = BTN_LOOKUP.get(ch_note)
            if btn:
                self._handle_button(btn)

    def _handle_button(self, btn: str):
        if btn == "play":
            if not self.playing and not self._pending_start:
                if self._ableton_playing:
                    self._pending_start = True   # attend le prochain début de barre
                    print("⏱ En attente du prochain début de barre...")
                else:
                    self.playing = True          # départ immédiat (standalone)
                    self._reset_playhead(0)

        elif btn == "stop":
            self.playing = False
            self._pending_start = False
            self._send_note_off()
            # All-notes-off sur toutes les sorties pour éviter notes bloquées
            for out in [self._iac_out, self._hw_out]:
                if out:
                    try:
                        out.send(mido.Message('control_change',
                                              channel=0, control=123, value=0))
                    except Exception:
                        pass
            self._refresh_all_leds()
            if self._last_lit_step is not None:
                self._led(self._last_lit_step, self._step_led_velocity(self._last_lit_step))
                self._last_lit_step = None

        elif btn == "bpm_m1":   self.set_bpm(self.bpm - 1)
        elif btn == "bpm_p1":   self.set_bpm(self.bpm + 1)
        elif btn == "bpm_m5":   self.set_bpm(self.bpm - 5)
        elif btn == "bpm_p5":   self.set_bpm(self.bpm + 5)

        elif btn in ("note_m_st", "note_p_st", "note_m_oct", "note_p_oct"):
            if self.selected_step is not None:
                delta = {"note_m_st": -1, "note_p_st": +1,
                         "note_m_oct": -12, "note_p_oct": +12}[btn]
                self.set_step_note(self.selected_step,
                                   self.step_notes[self.selected_step] + delta)

        elif btn == "pattern_oct_m": self.shift_pattern_octave(-12)
        elif btn == "pattern_oct_p": self.shift_pattern_octave(+12)

        elif btn == "len_8":    self.set_length(8)
        elif btn == "len_16":   self.set_length(16)
        elif btn == "len_32":   self.set_length(32)

        elif btn == "reverse":  self.reverse = not self.reverse

        elif btn == "rnd_steps":       self.randomize_steps()
        elif btn == "rnd_notes":       self.randomize_notes()
        elif btn == "perp_rnd_notes":  self.perp_rnd_notes = not self.perp_rnd_notes
        elif btn == "perp_rnd_steps":  self.perp_rnd_steps = not self.perp_rnd_steps
        elif btn == "mute":             self.muted = not self.muted
        elif btn == "clear_pattern":   self.clear_pattern()

        elif btn == "gen_mode_bass":
            self.gen_mode = "bass"
            print("→ Génération : BASSE")
            self._refresh_all_leds()
        elif btn == "gen_mode_melody":
            self.gen_mode = "melody"
            print("→ Génération : MÉLODIE")
            self._refresh_all_leds()
        elif btn in ("mode_sampler_l", "mode_sampler_r"):    self.ui_mode = "sequencer"
        elif btn in ("mode_beatjump_l", "mode_beatjump_r"):  self.ui_mode = "scale"
        elif btn == "out_iac":  self.midi_out_mode = "IAC";  print("→ Sortie : IAC")
        elif btn == "out_hw":   self.midi_out_mode = "HW";   print("→ Sortie : HW")
        elif btn == "out_both": self.midi_out_mode = "BOTH"; print("→ Sortie : BOTH")

        elif btn.startswith("pattern_copy_"):
            self.copy_to_pattern(int(btn.split("_")[2]))

        elif btn.startswith("pattern_"):
            self.set_pattern(int(btn.split("_")[1]))

    # ── API publique ──────────────────────────────────────────────────

    def toggle_step(self, index: int):
        with self._lock:
            self.steps[index] = not self.steps[index]
            # On protège l'affichage du curseur seulement pendant la lecture ;
            # à l'arrêt, il n'y a pas de curseur actif donc on rafraîchit toujours.
            if not self.playing or index != self.current_step:
                self._led(index, self._step_led_velocity(index))

    def toggle_play(self):
        with self._lock:
            if self.playing:
                self._handle_button("stop")
            else:
                self._handle_button("play")

    def panic(self):
        """Coupe toutes les notes sur toutes les sorties."""
        with self._lock:
            self.playing = False
            self._send_note_off()
        for out in [self._iac_out, self._hw_out]:
            if out:
                try:
                    for ch in range(16):
                        out.send(mido.Message('control_change',
                                              channel=ch, control=123, value=0))
                except Exception:
                    pass

    def reset(self):
        with self._lock:
            self._reset_playhead(0)

    def set_bpm(self, value: int):
        self.bpm = max(40, min(240, value))

    def set_pattern(self, index: int):
        with self._lock:
            if 0 <= index < NUM_PATTERNS:
                if self.playing:
                    # Quantisé : le nouveau pattern démarre à la fin de la boucle courante
                    self._pending_pattern = index
                else:
                    # Pas en lecture : changement immédiat
                    self.active_pattern = index
                    self._pending_pattern = None
                    self._refresh_all_leds()

    def copy_to_pattern(self, target: int):
        """Copie le pattern actif (steps + notes) dans le pattern `target`,
        puis bascule dessus (comme set_pattern : immédiat, ou quantisé si
        lecture en cours)."""
        if not (0 <= target < NUM_PATTERNS) or target == self.active_pattern:
            return
        with self._lock:
            self.patterns[target]      = list(self.steps)
            self.pattern_notes[target] = list(self.step_notes)
            self.set_pattern(target)

    def set_step_note(self, index: int, note: int):
        with self._lock:
            self.step_notes[index] = max(0, min(127, note))
            if not self.playing or index != self.current_step:
                self._led(index, self._step_led_velocity(index))

    def set_length(self, length: int):
        with self._lock:
            if length in (8, 16, 32):
                self.pattern_length = length
                if self.current_step >= length:
                    self._reset_playhead(0)

    def get_scale_notes(self, midi_min: int = 36, midi_max: int = 84) -> list[int]:
        """Retourne toutes les notes MIDI de la gamme entre midi_min et midi_max."""
        intervals = SCALES.get(self.scale_mode, SCALES["Majeur"])
        notes = []
        for midi in range(midi_min, midi_max + 1):
            if (midi - self.scale_root) % 12 in intervals:
                notes.append(midi)
        return notes

    def _assign_scale_note(self, scale_index: int):
        """Joue la note scale_index et l'assigne à selected_step si un step est sélectionné."""
        with self._lock:
            scale = self.get_scale_notes()
            if not scale or scale_index >= len(scale):
                return
            note = scale[scale_index]
            # Assigner au step seulement si un step est sélectionné
            if self.selected_step is not None:
                self.set_step_note(self.selected_step, note)
        # Feedback auditif : envoyé hors verrou (I/O MIDI, pas d'état partagé touché)
        self._midi_send(mido.Message('note_on',  channel=0, note=note, velocity=VELOCITY))
        threading.Timer(0.2, lambda n=note: self._midi_send(
            mido.Message('note_off', channel=0, note=n, velocity=0)
        )).start()

    def clear_pattern(self):
        with self._lock:
            for i in range(NUM_STEPS):
                self.steps[i] = False
                self._led(i, LED_OFF)

    def shift_pattern_octave(self, delta: int):
        """Décale la note de TOUS les steps du pattern actif d'une octave
        (±12 demi-tons), actifs ou non, pour que les steps encore éteints
        gardent la bonne octave si on les rallume ensuite."""
        with self._lock:
            for i in range(NUM_STEPS):
                self.step_notes[i] = max(0, min(127, self.step_notes[i] + delta))
            self._refresh_all_leds()

    def _step_weight(self, i: int) -> float:
        """Probabilité qu'un step soit actif selon sa position rythmique.
        Temps forts plus denses que les subdivisions → ça groove au lieu d'être plat."""
        if i % 4 == 0:
            return 0.75    # temps fort (1, 5, 9, 13...)
        elif i % 2 == 0:
            return 0.45    # contretemps
        else:
            return 0.20    # subdivision faible

    def _scale_degree_role(self, note: int) -> str:
        """Rôle harmonique d'une note par rapport à la fondamentale : 'root',
        'fifth' ou 'other'. Root+fifth = le couple de basse le plus universel."""
        interval = (note - self.scale_root) % 12
        if interval == 0:
            return "root"
        elif interval == 7:
            return "fifth"
        return "other"

    def _pick_anchor_note(self, scale: list[int], near_midi: int | None) -> int:
        """Choisit une fondamentale ou une quinte de la gamme (root favorisée),
        en privilégiant celle la plus proche de near_midi pour éviter les sauts."""
        candidates = [n for n in scale if self._scale_degree_role(n) != "other"]
        if not candidates:
            return random.choice(scale)
        weights = [3.0 if self._scale_degree_role(n) == "root" else 1.0 for n in candidates]
        if near_midi is not None:
            weights = [w / (1 + abs(n - near_midi)) for w, n in zip(weights, candidates)]
        return random.choices(candidates, weights=weights, k=1)[0]

    def _passing_note(self, scale: list[int], start: int, end: int) -> int:
        """Note de passage entre deux ancrages (technique du walking bass) :
        un degré de la gamme situé entre les deux, pour relier la ligne pas à pas."""
        lo, hi = sorted((start, end))
        between = [n for n in scale if lo < n < hi]
        return random.choice(between) if between else start

    def _walking_bass_notes(self, scale: list[int]) -> dict[int, int]:
        """Notes des steps actifs façon walking bass : une fondamentale/quinte
        (ancrage) sur chaque temps fort (groupe de 4 steps), et des notes de
        passage entre deux ancrages voisines sur les temps faibles."""
        anchors: dict[int, int] = {}
        last_anchor = None
        for i in range(0, self.pattern_length, 4):
            last_anchor = self._pick_anchor_note(scale, last_anchor)
            anchors[i] = last_anchor

        notes: dict[int, int] = {}
        for i in range(self.pattern_length):
            if not self.steps[i]:
                continue
            group_start = (i // 4) * 4
            if i == group_start:
                notes[i] = anchors[group_start]
            else:
                target = anchors.get(group_start + 4, anchors[group_start])
                notes[i] = self._passing_note(scale, anchors[group_start], target)
        return notes

    def _melody_notes(self, scale: list[int]) -> dict[int, int]:
        """Notes des steps actifs façon mélodie : tous les degrés de la gamme
        sont utilisables (pas juste root/fifth comme la basse). Règle de
        contrepoint classique : après un grand saut, la note suivante revient
        par un pas conjoint en sens inverse. Léger arc de phrase (tendance vers
        l'aigu en 1ère moitié de pattern, vers le grave ensuite). Cadence finale :
        le dernier step actif résout vers la tonique la plus proche."""
        active = [i for i in range(self.pattern_length) if self.steps[i]]
        if not active:
            return {}

        notes: dict[int, int] = {}
        prev_idx = len(scale) // 2   # on démarre au milieu de l'ambitus
        last_leap = 0                # amplitude/direction du dernier mouvement

        for pos, i in enumerate(active):
            if pos == 0:
                notes[i] = scale[prev_idx]
                continue

            if i == active[-1]:
                roots = [n for n in scale if self._scale_degree_role(n) == "root"]
                notes[i] = min(roots, key=lambda n: abs(n - scale[prev_idx])) if roots else scale[prev_idx]
                continue

            if abs(last_leap) >= 3:
                pas = -1 if last_leap > 0 else 1   # retour par pas conjoint après un saut
            else:
                arc = 1 if pos < len(active) / 2 else -1
                choix = [-4, -3, -2, -1, -1, 0, 1, 1, 2, 3, 4]
                poids = [1 + (0.5 if (c > 0) == (arc > 0) and c != 0 else 0) for c in choix]
                pas = random.choices(choix, weights=poids, k=1)[0]

            new_idx = max(0, min(len(scale) - 1, prev_idx + pas))
            last_leap = new_idx - prev_idx
            prev_idx = new_idx
            notes[i] = scale[prev_idx]

        return notes

    def _generate_notes(self, scale: list[int]) -> dict[int, int]:
        """Choisit la logique de génération de notes selon le mode actif."""
        if self.gen_mode == "melody":
            return self._melody_notes(scale)
        return self._walking_bass_notes(scale)

    def randomize_steps(self):
        """Randomise les steps on/off à partir d'un motif de 4 steps répété sur
        tout le pattern (avec variation) plutôt qu'un tirage indépendant partout :
        ça donne un groove reconnaissable au lieu d'un bruit rythmique sans forme.
        Notes générées selon le mode actif (basse ou mélodie)."""
        with self._lock:
            scale = self.get_scale_notes(RANDOM_NOTE_MIN, RANDOM_NOTE_MAX)
            motif_len = 4
            motif = [random.random() < self._step_weight(i) for i in range(motif_len)]
            for i in range(self.pattern_length):
                base_on = motif[i % motif_len]
                # 20% de chance d'inverser le step du motif à chaque répétition
                self.steps[i] = (not base_on) if random.random() < 0.2 else base_on
            if scale:
                for i, note in self._generate_notes(scale).items():
                    self.step_notes[i] = note
            self._refresh_all_leds()

    def randomize_notes(self):
        """Randomise les notes des steps actifs en place, selon le mode actif
        (basse : ancrages root/fifth + passage ; mélodie : contour + cadence)."""
        with self._lock:
            scale = self.get_scale_notes(RANDOM_NOTE_MIN, RANDOM_NOTE_MAX)
            if not scale:
                return
            for i, note in self._generate_notes(scale).items():
                self.step_notes[i] = note
            self._refresh_all_leds()

    @property
    def synced_to_ableton(self) -> bool:
        return time.time() - self._last_clock_time < CLOCK_TIMEOUT

    # ── Helpers ───────────────────────────────────────────────────────

    def _send_note_off(self):
        if self._active_note is not None:
            self._midi_send(mido.Message('note_off', channel=0,
                                            note=self._active_note, velocity=0))
            self._active_note = None

    def _led(self, step: int, velocity: int):
        """Met en file la couleur d'un pad (cf. LED_* plus haut), envoyée par
        _led_writer_loop dans un thread séparé pour ne jamais bloquer le
        thread qui lit le clock MIDI d'Ableton."""
        self._led_queue.put((step, velocity))

    def _step_led_velocity(self, step: int) -> int:
        """Couleur d'affichage statique d'un step : orange en mode Basse,
        violet en mode Mélodie, plus vif si la note est un ancrage (root/fifth)."""
        if not self.steps[step]:
            return LED_OFF
        is_anchor = self._scale_degree_role(self.step_notes[step]) in ("root", "fifth")
        if self.gen_mode == "melody":
            return LED_MELODY_ANCHOR if is_anchor else LED_MELODY_PASSING
        return LED_BASS_ANCHOR if is_anchor else LED_BASS_PASSING

    def _refresh_all_leds(self):
        """Réaffiche tous les pads selon l'état courant (mode + notes),
        sauf le step en cours de lecture (géré séparément par _tick)."""
        for i in range(NUM_STEPS):
            if i != self.current_step:
                self._led(i, self._step_led_velocity(i))

    @staticmethod
    def _find(direction: str, keyword: str) -> str | None:
        ports = mido.get_input_names() if direction == "in" else mido.get_output_names()
        return next((p for p in ports if keyword.lower() in p.lower()), None)

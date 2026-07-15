# ── Mapping complet DDJ-XP1 ───────────────────────────────────────────
# Convention : ch = canal MIDI (0-indexed), note = numéro de note MIDI

# ── Boutons de mode (sélectionnent le mode des pads) ─────────────────
MODE_BUTTONS = {
    "hotcue_gauche":    dict(ch=0,  note=27),
    "hotcue_droite":    dict(ch=1,  note=27),
    "padfx1_gauche":    dict(ch=0,  note=30),
    "padfx1_droite":    dict(ch=1,  note=30),
    "beatjump_gauche":  dict(ch=0,  note=32),
    "beatjump_droite":  dict(ch=1,  note=32),
    "sampler_gauche":   dict(ch=0,  note=34),
    "sampler_droite":   dict(ch=1,  note=34),
}

# ── Pads (16 par côté, par mode) ─────────────────────────────────────
PADS = {
    # Sampler : séquenceur 32 steps
    "sampler_gauche":   dict(ch=7,  notes=list(range(48, 64))),  # steps 1-16
    "sampler_droite":   dict(ch=9,  notes=list(range(48, 64))),  # steps 17-32

    # Hot Cue : contrôles directs
    "hotcue_gauche":    dict(ch=7,  notes=list(range(0,  16))),
    "hotcue_droite":    dict(ch=9,  notes=list(range(0,  16))),

    # Beat Jump : clavier chromatique (assignation de notes)
    "beatjump_gauche":  dict(ch=7,  notes=list(range(32, 48))),
    "beatjump_droite":  dict(ch=9,  notes=list(range(32, 48))),

    # Pad FX1 : fonctions avancées
    "padfx1_gauche":    dict(ch=7,  notes=list(range(16, 32))),
    "padfx1_droite":    dict(ch=9,  notes=list(range(16, 32))),
}

# ── Boutons du haut — côté gauche (Ch1 = ch=0) ───────────────────────
TOP_LEFT = {
    "4beats_loop_gauche":   dict(ch=0, note=20),
    "loop_in_gauche":       dict(ch=0, note=16),
    "loop_out_gauche":      dict(ch=0, note=17),
    "slip_reverse_gauche":  dict(ch=0, note=21),
    "master_tempo_gauche":  dict(ch=0, note=26),
    "beat_sync_gauche":     dict(ch=0, note=88),
    "quantize_gauche":      dict(ch=0, note=53),
    "page_left_gauche":     dict(ch=0, note=38),
    "page_right_gauche":    dict(ch=0, note=46),
    "silent_cue_gauche":    dict(ch=0, note=104),
    "semitone_moins_gauche":dict(ch=0, note=10),
    "semitone_plus_gauche": dict(ch=0, note=121),
    "INT_gauche":           dict(ch=0, note=115),
    "load_gauche":          dict(ch=6, note=70),   # Ch7 en 0-indexed = ch=6
}

# ── Boutons du haut — côté droit (Ch2 = ch=1) ────────────────────────
# Miroir du côté gauche, ch=1 au lieu de ch=0
TOP_RIGHT = {
    "4beats_loop_droite":   dict(ch=1, note=20),
    "loop_in_droite":       dict(ch=1, note=16),
    "loop_out_droite":      dict(ch=1, note=17),
    "slip_reverse_droite":  dict(ch=1, note=21),
    "master_tempo_droite":  dict(ch=1, note=26),
    "beat_sync_droite":     dict(ch=1, note=88),
    "quantize_droite":      dict(ch=1, note=53),
    "page_left_droite":     dict(ch=1, note=38),
    "page_right_droite":    dict(ch=1, note=46),
    "silent_cue_droite":    dict(ch=1, note=104),
    "semitone_moins_droite":dict(ch=1, note=10),
    "semitone_plus_droite": dict(ch=1, note=121),
    "INT_droite":           dict(ch=1, note=115),
    "load_droite":          dict(ch=6, note=71),   # à confirmer
}

# ── Boutons latéraux ─────────────────────────────────────────────────
# Comportement : note_on v>0 = enfoncé / note_off = relâché (même note)
SIDE_BUTTONS = {
    "slidefx1_gauche":  dict(ch=4, note=112),
    "slidefx2_gauche":  dict(ch=4, note=113),
    "slidefx3_gauche":  dict(ch=4, note=114),
    "hold_gauche":      dict(ch=4, note=118),

    "slidefx1_droite":  dict(ch=5, note=112),
    "slidefx2_droite":  dict(ch=5, note=113),
    "slidefx3_droite":  dict(ch=5, note=114),
    "hold_droite":      dict(ch=5, note=118),
}

# ── Centre ────────────────────────────────────────────────────────────
CENTER = {
    "shift":        dict(ch=6, note=64),   # Ch7 = ch=6
    # encodeur rotatif → envoie probablement des CC, pas des notes
    # à vérifier avec un script CC
}

# ── À CONFIRMER / INCONNU ─────────────────────────────────────────────
# Ch7 Note 65 = INT centre ? (à tester)
# Ch5/Ch6 Note 73 = origine inconnue (FX LEVEL fader ? à vérifier)
# Encodeur rotatif central = probablement CC (pas capté par note_on)
# Faders FX LEVEL = probablement CC

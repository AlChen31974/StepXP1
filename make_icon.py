"""
Génère icon.png pour le Step Sequencer — grille de steps style séquenceur.
"""
from PIL import Image, ImageDraw, ImageFilter
import math

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── Fond arrondi ────────────────────────────────────────────────────
RADIUS = 220
BG = (20, 20, 28, 255)
draw.rounded_rectangle([0, 0, SIZE, SIZE], radius=RADIUS, fill=BG)

# ── Grille de steps (4 rangées × 8 colonnes) ───────────────────────
ROWS, COLS = 4, 8
MARGIN = 90
STEP_GAP = 18
STEP_W = (SIZE - 2 * MARGIN - (COLS - 1) * STEP_GAP) // COLS
STEP_H = (SIZE - 2 * MARGIN - (ROWS - 1) * STEP_GAP) // ROWS
STEP_R = 24

# Couleurs du projet
COLOR_OFF       = (43, 43, 43, 255)
COLOR_ON_ORANGE = (230, 126, 34, 255)
COLOR_ON_BLUE   = (52, 152, 219, 255)
COLOR_ON_TEAL   = (26, 188, 156, 255)
COLOR_ON_PURPLE = (142, 68, 173, 255)

# Pattern : quels steps sont allumés (par rangée)
PATTERN = [
    [1, 0, 0, 1, 0, 1, 0, 1],  # rangée 0 — orange (kick)
    [0, 0, 1, 0, 0, 0, 1, 0],  # rangée 1 — bleu (snare)
    [1, 1, 0, 1, 1, 0, 1, 1],  # rangée 2 — teal (hihat)
    [0, 1, 0, 0, 1, 0, 0, 1],  # rangée 3 — purple (bass)
]

ROW_COLORS = [COLOR_ON_ORANGE, COLOR_ON_BLUE, COLOR_ON_TEAL, COLOR_ON_PURPLE]

# Playhead sur la colonne 4
PLAYHEAD_COL = 4

for r in range(ROWS):
    for c in range(COLS):
        x0 = MARGIN + c * (STEP_W + STEP_GAP)
        y0 = MARGIN + r * (STEP_H + STEP_GAP)
        x1 = x0 + STEP_W
        y1 = y0 + STEP_H

        on = PATTERN[r][c]
        is_playhead = (c == PLAYHEAD_COL)

        if on and is_playhead:
            # Step allumé + playhead → version plus lumineuse
            base = ROW_COLORS[r]
            color = tuple(min(255, v + 60) for v in base[:3]) + (255,)
        elif on:
            color = ROW_COLORS[r]
        elif is_playhead:
            color = (60, 80, 100, 255)
        else:
            color = COLOR_OFF

        draw.rounded_rectangle([x0, y0, x1, y1], radius=STEP_R, fill=color)

# ── Légère lueur sur les steps orange ──────────────────────────────
glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for r in range(ROWS):
    for c in range(COLS):
        if PATTERN[r][c]:
            x0 = MARGIN + c * (STEP_W + STEP_GAP) - 6
            y0 = MARGIN + r * (STEP_H + STEP_GAP) - 6
            x1 = x0 + STEP_W + 12
            y1 = y0 + STEP_H + 12
            rc = ROW_COLORS[r]
            gd.rounded_rectangle([x0, y0, x1, y1], radius=STEP_R + 4, fill=rc[:3] + (60,))

glow = glow.filter(ImageFilter.GaussianBlur(12))
img = Image.alpha_composite(img, glow)

# Recoller la grille par-dessus la lueur
draw2 = ImageDraw.Draw(img)
for r in range(ROWS):
    for c in range(COLS):
        x0 = MARGIN + c * (STEP_W + STEP_GAP)
        y0 = MARGIN + r * (STEP_H + STEP_GAP)
        x1 = x0 + STEP_W
        y1 = y0 + STEP_H
        on = PATTERN[r][c]
        is_playhead = (c == PLAYHEAD_COL)
        if on and is_playhead:
            base = ROW_COLORS[r]
            color = tuple(min(255, v + 60) for v in base[:3]) + (255,)
        elif on:
            color = ROW_COLORS[r]
        elif is_playhead:
            color = (60, 80, 100, 255)
        else:
            color = COLOR_OFF
        draw2.rounded_rectangle([x0, y0, x1, y1], radius=STEP_R, fill=color)

out = "/Users/alexandrecheny/VIBE_CODING/Step Sequenceur/icon.png"
img.save(out)
print(f"Icône sauvegardée : {out}")

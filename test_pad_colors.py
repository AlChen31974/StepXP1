"""
Script de test TEMPORAIRE : allume plusieurs pads de la XP1 en même temps,
chacun avec une vélocité différente, pour découvrir la vraie correspondance
vélocité → couleur sur ce matériel. À supprimer une fois le mapping trouvé.
"""
import time
import mido
from engine import STEP_TO_PAD

# Vélocités candidates (piste trouvée sur un forum, à vérifier sur le vrai hardware)
CANDIDATES = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65,
              70, 75, 80, 85, 90, 95, 100, 106, 110, 116, 120, 125, 127]

xp1_out_name = next((p for p in mido.get_output_names() if "xp1" in p.lower()), None)
if not xp1_out_name:
    print("XP1 non trouvée en sortie MIDI. Branche/allume la XP1 et relance.")
    exit()

print(f"XP1 out : {xp1_out_name}\n")

with mido.open_output(xp1_out_name) as out:
    print("Pad → vélocité testée :")
    for step, velocity in enumerate(CANDIDATES):
        ch, note = STEP_TO_PAD[step]
        out.send(mido.Message('note_on', channel=ch, note=note, velocity=velocity))
        print(f"  pad {step + 1:2d} → vélocité {velocity}")

    input("\nRegarde la grille de pads, note la couleur de chacun, "
          "puis appuie sur Entrée pour tout éteindre...\n")

    for step in range(len(CANDIDATES)):
        ch, note = STEP_TO_PAD[step]
        out.send(mido.Message('note_off', channel=ch, note=note, velocity=0))

print("Pads éteints.")

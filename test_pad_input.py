"""
Script de test TEMPORAIRE : affiche tous les messages MIDI reçus de la XP1
en entrée, pour comparer ce qu'envoie le pad 5 (qui bug) vs un pad qui marche.
À supprimer une fois le diagnostic fait.
"""
import mido

xp1_in_name = next((p for p in mido.get_input_names() if "xp1" in p.lower()), None)
if not xp1_in_name:
    print("XP1 non trouvée en entrée MIDI. Branche/allume la XP1 et relance.")
    exit()

print(f"XP1 in : {xp1_in_name}")
print("Appuie sur des pads (essaie le pad 5, puis un pad qui marche à côté "
      "pour comparer). Ctrl+C pour arrêter.\n")

with mido.open_input(xp1_in_name) as inp:
    for msg in inp:
        if msg.type in ('note_on', 'note_off'):
            print(f"{msg.type:9s}  channel={msg.channel}  note={msg.note}  velocity={msg.velocity}")

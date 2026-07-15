import mido

port_name = [p for p in mido.get_input_names() if "XP1" in p][0]
print(f"Écoute sur : {port_name}")
print("Tourne l'encodeur dans un sens, puis dans l'autre (Ctrl+C pour arrêter)...\n")

with mido.open_input(port_name) as port:
    for msg in port:
        print(msg)

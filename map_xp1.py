import mido

port_name = [p for p in mido.get_input_names() if "XP1" in p][0]
print(f"Écoute sur : {port_name}")
print("Appuie sur les pads...\n")

seen = set()

with mido.open_input(port_name) as port:
    for msg in port:
        if msg.type == 'note_on' and msg.velocity > 0:
            key = (msg.channel, msg.note)
            if key not in seen:
                seen.add(key)
                print(f"Ch{msg.channel+1:2d}  Note {msg.note:3d}")

# StepXP1

Séquenceur MIDI 32 steps piloté par un contrôleur Pioneer DDJ-XP1, en Python.

Pensé pour jouer en standalone ou en esclave du clock Ableton Live (via IAC), avec sortie vers un synthé hardware en plus/à la place d'Ableton.

## Fonctionnalités

- 32 pads SAMPLER = grille de steps (4×8, répartis sur les 2 decks du contrôleur)
- 6 patterns indépendants, sélectionnables via les boutons SLIDE FX
- Longueur de pattern variable (8 / 16 / 32 steps)
- Édition des notes par step (±½ ton, ±octave) directement depuis le contrôleur ou la GUI
- Mode gamme (BEAT JUMP) : assignation de notes à partir d'une gamme (majeur, mineur, pentatonique, dorien, mixolydien, blues, chromatique)
- Randomisation des steps/notes, avec deux modes de génération musicale :
  - **Basse** (walking bass) : ancrages fondamentale/quinte sur les temps forts, notes de passage entre les deux
  - **Mélodie** : parcours de gamme avec règles de contrepoint (retour par pas conjoint après un saut, arc de phrase, cadence finale)
- Modes perpétuels (re-randomisation automatique à chaque boucle)
- Reverse, Mute, Clear pattern
- Synchro Ableton Live via IAC Bus (clock + transport), avec démarrage quantisé sur début de barre
- Sélection de la sortie MIDI : IAC (Ableton), sortie hardware, ou les deux
- Feedback visuel sur les pads du contrôleur (couleur selon le rôle harmonique de la note) + GUI desktop (CustomTkinter, dark mode)

## Prérequis

- macOS (utilise le driver IAC pour la synchro Ableton)
- Python 3.11
- Un contrôleur Pioneer DDJ-XP1 connecté en USB
- [mido](https://mido.readthedocs.io/) (I/O MIDI)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) (interface graphique)

Installation des dépendances :

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python3 gui.py
```

Sur macOS, un launcher `StepSequencer.app` est fourni pour lancer l'app d'un double-clic (sans icône Dock, voir `Info.plist`).

## Configuration MIDI

- **IAC Driver Bus 1** doit être activé (Configuration Audio MIDI > IAC Driver) pour la synchro avec Ableton Live.
- Dans les préférences MIDI d'Ableton, la ligne du DDJ-XP1 ne doit avoir **aucune case Sync/Remote cochée** — seul IAC Bus 1 doit piloter le clock envoyé à la XP1, sinon le firmware du contrôleur peut se comporter de façon erratique.
- Une sortie hardware additionnelle (ex. interface audio MIDI) peut être sélectionnée sur le contrôleur pour piloter un synthé externe en parallèle ou à la place d'Ableton.

## Structure du projet

- `engine.py` — logique du séquenceur (MIDI, clock, patterns, notes, génération musicale)
- `gui.py` — interface graphique (point d'entrée principal)
- `xp1_mapping.py` — mapping complet des boutons/pads du DDJ-XP1
- `test_pad_colors.py`, `test_pad_input.py` — scripts de diagnostic MIDI (utiles en cas de souci hardware)
- `make_icon.py` — génération de l'icône `.icns` de l'app

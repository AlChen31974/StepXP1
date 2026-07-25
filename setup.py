"""
Build du .app macOS avec py2app :
    python3 setup.py py2app
Le resultat est genere dans dist/StepSequencer.app
"""
from setuptools import setup

APP = ['gui.py']
OPTIONS = {
    'iconfile': 'StepSequencer.icns',
    # mido/rtmidi/customtkinter chargent des fichiers/plugins dynamiquement,
    # py2app ne les detecte pas tout seul -> on force l'inclusion du package entier.
    'packages': ['mido', 'rtmidi', 'customtkinter'],
    'plist': {
        'CFBundleName': 'StepSequencer',
        'CFBundleDisplayName': 'StepSequencer',
        'CFBundleIdentifier': 'com.alexandrecheny.stepsequencer',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

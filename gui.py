import time
import customtkinter as ctk
from engine import SequencerEngine, NUM_PATTERNS, NUM_STEPS, SCALES, NOTE_NAMES

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Couleurs ──────────────────────────────────────────────────────────
COLOR_STEP_OFF    = "#2b2b2b"
COLOR_STEP_ON     = "#e67e22"
COLOR_PLAYHEAD    = "#3498db"
COLOR_PLAYHEAD_ON = "#1abc9c"
COLOR_SELECTED    = "#8e44ad"
COLOR_INACTIVE    = "#1a1a1a"   # step hors de la longueur active
POLL_MS           = 50

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PATTERN_LABELS = ["P1", "P2", "P3", "P4", "P5", "P6"]


def midi_to_name(note: int) -> str:
    octave = (note // 12) - 2
    return f"{NOTE_NAMES[note % 12]}{octave}"


class SequencerGUI(ctk.CTk):

    def __init__(self, engine: SequencerEngine):
        super().__init__()
        self.engine = engine
        self._selected_step: int | None = None

        self.title("Step Sequencer XP1")
        self.resizable(False, False)
        self._build_ui()
        self._build_scale_overlay()
        self._poll()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 8}

        ctk.CTkLabel(self, text="STEP SEQUENCER XP1",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(padx=16, pady=(14, 4))

        # ── Patterns (6 boutons) ──────────────────────────────────────
        pat_frame = ctk.CTkFrame(self)
        pat_frame.pack(**pad)
        ctk.CTkLabel(pat_frame, text="PATTERN",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=8)
        self._pat_btns: list[ctk.CTkButton] = []
        for i, label in enumerate(PATTERN_LABELS):
            btn = ctk.CTkButton(
                pat_frame, text=label, width=52, height=30,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda idx=i: self.engine.set_pattern(idx)
            )
            btn.pack(side="left", padx=3)
            self._pat_btns.append(btn)

        # ── BPM + longueur + sync ─────────────────────────────────────
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(**pad)

        ctk.CTkButton(top_frame, text="−", width=32,
                      command=lambda: self.engine.set_bpm(self.engine.bpm - 1)
                      ).pack(side="left", padx=3)
        self._bpm_label = ctk.CTkLabel(
            top_frame, text=f"{self.engine.bpm} BPM",
            font=ctk.CTkFont(size=17, weight="bold"), width=100)
        self._bpm_label.pack(side="left", padx=3)
        ctk.CTkButton(top_frame, text="+", width=32,
                      command=lambda: self.engine.set_bpm(self.engine.bpm + 1)
                      ).pack(side="left", padx=3)

        # Longueur
        ctk.CTkLabel(top_frame, text="  STEPS",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(12, 4))
        for n in (8, 16, 32):
            ctk.CTkButton(top_frame, text=str(n), width=40, height=28,
                          command=lambda v=n: self.engine.set_length(v)
                          ).pack(side="left", padx=2)

        # Reverse + sync
        self._rev_btn = ctk.CTkButton(
            top_frame, text="REV", width=44, height=28,
            fg_color="#2b2b2b",
            command=lambda: setattr(self.engine, 'reverse', not self.engine.reverse)
        )
        self._rev_btn.pack(side="left", padx=(10, 3))

        self._mute_btn = ctk.CTkButton(
            top_frame, text="MUTE", width=52, height=28,
            fg_color="#2b2b2b",
            command=lambda: setattr(self.engine, 'muted', not self.engine.muted)
        )
        self._mute_btn.pack(side="left", padx=3)

        self._prn_btn = ctk.CTkLabel(
            top_frame, text="∞ NOTES",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#2b2b2b")
        self._prn_btn.pack(side="left", padx=4)

        self._prs_btn = ctk.CTkLabel(
            top_frame, text="∞ STEPS",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#2b2b2b")
        self._prs_btn.pack(side="left", padx=4)

        self._sync_badge = ctk.CTkLabel(
            top_frame, text="● STANDALONE",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#7f8c8d")
        self._sync_badge.pack(side="left", padx=10)

        self._out_badge = ctk.CTkLabel(
            top_frame, text="OUT: BOTH",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#7f8c8d")
        self._out_badge.pack(side="left", padx=4)

        self._gen_mode_badge = ctk.CTkLabel(
            top_frame, text="♪ BASSE",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#e67e22")
        self._gen_mode_badge.pack(side="left", padx=4)

        # ── Sélecteur de gamme ────────────────────────────────────────
        scale_frame = ctk.CTkFrame(self)
        scale_frame.pack(**pad)

        ctk.CTkLabel(scale_frame, text="GAMME",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=8)

        self._root_var = ctk.StringVar(value="C")
        root_menu = ctk.CTkOptionMenu(
            scale_frame,
            values=NOTE_NAMES,
            variable=self._root_var,
            width=70, height=28,
            command=self._on_scale_change
        )
        root_menu.pack(side="left", padx=4)

        self._mode_var = ctk.StringVar(value="Majeur")
        mode_menu = ctk.CTkOptionMenu(
            scale_frame,
            values=list(SCALES.keys()),
            variable=self._mode_var,
            width=160, height=28,
            command=self._on_scale_change
        )
        mode_menu.pack(side="left", padx=4)

        # ── 32 pads (4 rangées × 8 colonnes) ─────────────────────────
        pads_frame = ctk.CTkFrame(self)
        pads_frame.pack(**pad)
        self._pads: list[ctk.CTkButton] = []

        for row in range(4):
            row_frame = ctk.CTkFrame(pads_frame, fg_color="transparent")
            row_frame.pack(pady=3)
            for col in range(8):
                step = row * 8 + col   # 0-31
                btn = ctk.CTkButton(
                    row_frame,
                    text=str(step + 1),
                    width=58, height=58,
                    fg_color=COLOR_STEP_OFF,
                    hover_color="#444",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda s=step: self._on_pad_click(s)
                )
                btn.pack(side="left", padx=2)
                # Clic droit = sélectionner sans toggle
                btn.bind("<Button-2>", lambda e, s=step: self._on_pad_right_click(s))
                btn.bind("<Button-3>", lambda e, s=step: self._on_pad_right_click(s))
                self._pads.append(btn)

        # ── Éditeur de note ───────────────────────────────────────────
        note_frame = ctk.CTkFrame(self)
        note_frame.pack(**pad, fill="x")

        top_row = ctk.CTkFrame(note_frame, fg_color="transparent")
        top_row.pack(pady=(8, 2))
        ctk.CTkLabel(top_row, text="Step :",
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=6)
        self._step_label = ctk.CTkLabel(
            top_row, text="1",
            font=ctk.CTkFont(size=12, weight="bold"), width=30)
        self._step_label.pack(side="left")
        ctk.CTkLabel(top_row, text="Note :",
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(16, 6))
        self._note_label = ctk.CTkLabel(
            top_row,
            text=midi_to_name(self.engine.step_notes[0]),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#e67e22", width=60)
        self._note_label.pack(side="left")

        bot_row = ctk.CTkFrame(note_frame, fg_color="transparent")
        bot_row.pack(pady=(2, 8))
        for label, delta in [("− ½t", -1), ("+ ½t", +1), ("− oct", -12), ("+ oct", +12)]:
            ctk.CTkButton(bot_row, text=label, width=72, height=30,
                          command=lambda d=delta: self._shift_note(d)
                          ).pack(side="left", padx=3)

        # ── Play / Stop / Reset ───────────────────────────────────────
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.pack(**pad)
        self._play_btn = ctk.CTkButton(
            ctrl_frame, text="▶  PLAY",
            width=120, height=42,
            fg_color="#27ae60", hover_color="#1e8449",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.engine.toggle_play)
        self._play_btn.pack(side="left", padx=8)
        ctk.CTkButton(
            ctrl_frame, text="↩  RESET",
            width=100, height=42,
            fg_color="#7f8c8d", hover_color="#626b6c",
            command=self.engine.reset).pack(side="left", padx=8)

    # ── Overlay Scale Mode ────────────────────────────────────────────

    def _build_scale_overlay(self):
        """Page dédiée scale mode — posée par-dessus l'interface principale."""
        self._scale_overlay = ctk.CTkFrame(self, corner_radius=0)
        # Caché par défaut
        self._scale_overlay_visible = False

        # Titre
        ctk.CTkLabel(self._scale_overlay, text="SCALE MODE",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#3498db").pack(pady=(20, 4))

        ctk.CTkLabel(self._scale_overlay,
                     text="Presse SAMPLER pour revenir",
                     font=ctk.CTkFont(size=11), text_color="#7f8c8d").pack(pady=(0, 12))

        # Step sélectionné + note assignée
        info_frame = ctk.CTkFrame(self._scale_overlay)
        info_frame.pack(padx=20, pady=(0, 12), fill="x")

        ctk.CTkLabel(info_frame, text="Step :",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=10)
        self._sc_step_label = ctk.CTkLabel(
            info_frame, text="1",
            font=ctk.CTkFont(size=18, weight="bold"), width=40)
        self._sc_step_label.pack(side="left")

        ctk.CTkLabel(info_frame, text="Note assignée :",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(20, 6))
        self._sc_note_label = ctk.CTkLabel(
            info_frame, text="C3",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e67e22", width=60)
        self._sc_note_label.pack(side="left")

        # Grille 4×8 des notes de la gamme
        grid_frame = ctk.CTkFrame(self._scale_overlay)
        grid_frame.pack(padx=16, pady=8)

        self._scale_btns: list[ctk.CTkButton] = []
        for row in range(4):
            row_frame = ctk.CTkFrame(grid_frame, fg_color="transparent")
            row_frame.pack(pady=3)
            for col in range(8):
                idx = row * 8 + col
                btn = ctk.CTkButton(
                    row_frame, text="—",
                    width=60, height=50,
                    fg_color="#1a1a1a", hover_color="#333",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda i=idx: self._on_scale_pad(i)
                )
                btn.pack(side="left", padx=2)
                self._scale_btns.append(btn)

    def _show_scale_overlay(self, visible: bool):
        if visible and not self._scale_overlay_visible:
            self._scale_overlay.place(x=0, y=0, relwidth=1, relheight=1)
            self._scale_overlay_visible = True
        elif not visible and self._scale_overlay_visible:
            self._scale_overlay.place_forget()
            self._scale_overlay_visible = False

    def _on_close(self):
        self.engine.panic()
        self.destroy()

    # ── Callbacks ─────────────────────────────────────────────────────

    def _on_pad_click(self, step: int):
        self.engine.toggle_step(step)
        self._selected_step = step
        self._update_note_display()

    def _on_pad_right_click(self, step: int):
        """Sélectionne le step pour édition sans le toggle."""
        self._selected_step = step
        self.engine.selected_step = step
        self._update_note_display()

    def _shift_note(self, semitones: int):
        if self._selected_step is None:
            return
        current = self.engine.step_notes[self._selected_step]
        self.engine.set_step_note(self._selected_step, current + semitones)
        self._update_note_display()

    def _on_scale_change(self, _value=None):
        self.engine.scale_root = NOTE_NAMES.index(self._root_var.get())
        self.engine.scale_mode = self._mode_var.get()

    def _on_scale_pad(self, index: int):
        self.engine._assign_scale_note(index)

    def _update_note_display(self):
        if self._selected_step is None:
            self._step_label.configure(text="—")
            self._note_label.configure(text="—")
            return
        self._step_label.configure(text=str(self._selected_step + 1))
        self._note_label.configure(
            text=midi_to_name(self.engine.step_notes[self._selected_step]))

    # ── Boucle de sync ────────────────────────────────────────────────

    def _poll(self):
        self._show_scale_overlay(self.engine.ui_mode == "scale")
        self._refresh_pads()
        self._refresh_bpm()
        self._refresh_patterns()
        self._refresh_play_btn()
        self._refresh_length_and_reverse()
        self._refresh_sync_badge()
        if self.engine.ui_mode == "scale":
            self._refresh_scale_overlay()
        # Sync selected_step depuis hardware
        if self.engine.selected_step is not None and self.engine.selected_step != self._selected_step:
            self._selected_step = self.engine.selected_step
            self._update_note_display()
        self.after(POLL_MS, self._poll)

    def _refresh_pads(self):
        playhead = self.engine.current_step
        steps    = self.engine.steps
        length   = self.engine.pattern_length

        for i, btn in enumerate(self._pads):
            is_active   = steps[i]
            is_playhead = (i == playhead) and self.engine.playing
            is_selected = (self._selected_step is not None and i == self._selected_step)
            in_range    = (i < length)

            if not in_range:
                color = COLOR_INACTIVE
            elif is_playhead and is_active:
                color = COLOR_PLAYHEAD_ON
            elif is_playhead:
                color = COLOR_PLAYHEAD
            elif is_selected:
                color = COLOR_SELECTED
            elif is_active:
                color = COLOR_STEP_ON
            else:
                color = COLOR_STEP_OFF

            text = f"{i+1}\n{midi_to_name(self.engine.step_notes[i])}" if is_active else str(i + 1)
            btn.configure(fg_color=color, text=text)

    def _refresh_bpm(self):
        self._bpm_label.configure(text=f"{self.engine.bpm} BPM")

    def _refresh_patterns(self):
        for i, btn in enumerate(self._pat_btns):
            if i == self.engine.active_pattern:
                btn.configure(fg_color="#e67e22", hover_color="#d35400")
            else:
                btn.configure(fg_color="#1f538d", hover_color="#2d6db5")

    def _refresh_play_btn(self):
        if self.engine.playing:
            self._play_btn.configure(text="■  STOP", fg_color="#c0392b",
                                     hover_color="#922b21")
        elif self.engine._pending_start:
            # Alterne pour simuler un clignotement
            tick = int(time.time() * 2) % 2
            color = "#e67e22" if tick else "#7f5200"
            self._play_btn.configure(text="⏱  QUANTIZE...", fg_color=color,
                                     hover_color="#c0392b")
        else:
            self._play_btn.configure(text="▶  PLAY", fg_color="#27ae60",
                                     hover_color="#1e8449")

    def _refresh_length_and_reverse(self):
        color = "#e67e22" if self.engine.reverse else "#2b2b2b"
        self._rev_btn.configure(fg_color=color)
        self._prn_btn.configure(
            text_color="#1abc9c" if self.engine.perp_rnd_notes else "#2b2b2b")
        self._prs_btn.configure(
            text_color="#1abc9c" if self.engine.perp_rnd_steps else "#2b2b2b")
        self._mute_btn.configure(
            fg_color="#c0392b" if self.engine.muted else "#2b2b2b")

    def _refresh_scale_overlay(self):
        step = self.engine.selected_step if self.engine.selected_step is not None else 0
        active_note = self.engine.step_notes[step]
        scale = self.engine.get_scale_notes()

        self._sc_step_label.configure(text=str(step + 1))
        self._sc_note_label.configure(text=midi_to_name(active_note))

        for i, btn in enumerate(self._scale_btns):
            if i < len(scale):
                note = scale[i]
                is_active = (note == active_note)
                is_root   = (note % 12 == self.engine.scale_root % 12)
                if is_active:
                    color = "#e67e22"
                elif is_root:
                    color = "#2980b9"
                else:
                    color = "#2b2b2b"
                btn.configure(text=midi_to_name(note), fg_color=color, hover_color="#555")
            else:
                btn.configure(text="—", fg_color="#111", hover_color="#111")

    def _refresh_sync_badge(self):
        if self.engine.synced_to_ableton:
            self._sync_badge.configure(text="● SYNC ABLETON", text_color="#3498db")
        else:
            self._sync_badge.configure(text="● STANDALONE",   text_color="#7f8c8d")
        colors = {"IAC": "#3498db", "HW": "#e67e22", "BOTH": "#1abc9c"}
        mode = self.engine.midi_out_mode
        self._out_badge.configure(text=f"OUT: {mode}", text_color=colors[mode])

        gen_colors = {"bass": "#e67e22", "melody": "#9b59b6"}
        gen_labels = {"bass": "♪ BASSE", "melody": "♪ MÉLODIE"}
        gen = self.engine.gen_mode
        self._gen_mode_badge.configure(text=gen_labels[gen], text_color=gen_colors[gen])


# ── Point d'entrée ────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = SequencerEngine()
    engine.start()

    app = SequencerGUI(engine)
    app.mainloop()

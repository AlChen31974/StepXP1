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
COLOR_IDLE        = "#2b2b2b"  # couleur neutre des CmdButton au repos
POLL_MS           = 50

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PATTERN_LABELS = ["P1", "P2", "P3", "P4", "P5", "P6"]

GEN_COLORS = {"bass": "#e67e22", "melody": "#9b59b6"}
OUT_COLORS = {"IAC": "#3498db", "HW": "#e67e22", "BOTH": "#9b59b6"}


def midi_to_name(note: int) -> str:
    octave = (note // 12) - 2
    return f"{NOTE_NAMES[note % 12]}{octave}"


class Pad(ctk.CTkCanvas):
    """Un step dessiné à la main (coins arrondis) au lieu d'un CTkButton classique."""

    SIZE = 58

    def __init__(self, master, step: int, on_click, on_right_click):
        super().__init__(master, width=self.SIZE, height=self.SIZE,
                          bg="#242424", highlightthickness=0)
        self.step = step
        self.color = COLOR_STEP_OFF
        self.text = str(step + 1)
        self.bind("<Button-1>", lambda e: on_click(step))
        self.bind("<Button-2>", lambda e: on_right_click(step))
        self.bind("<Button-3>", lambda e: on_right_click(step))
        self._draw()

    def set_state(self, color: str, text: str):
        if color == self.color and text == self.text:
            return  # évite de redessiner si rien n'a changé (perf)
        self.color = color
        self.text = text
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.SIZE
        self._round_rect(2, 2, s - 2, s - 2, radius=8, fill=self.color, outline="#000", width=1)
        lines = self.text.split("\n")
        if len(lines) == 1:
            self.create_text(s / 2, s / 2, text=lines[0], fill="white",
                              font=("Helvetica", 11, "bold"))
        else:
            self.create_text(s / 2, s / 2 - 8, text=lines[0], fill="white",
                              font=("Helvetica", 11, "bold"))
            self.create_text(s / 2, s / 2 + 9, text=lines[1], fill="white",
                              font=("Helvetica", 10))

    def _round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, **kwargs)


class CmdButton(ctk.CTkFrame):
    """Bouton de commande façon hardware XP1 : libellé de la fonction en gros,
    nom du bouton physique d'origine en petit dessous (optionnel)."""

    def __init__(self, master, label: str, sub: str | None, command=None,
                 width: int = 74, height: int = 52):
        super().__init__(master, width=width, height=height,
                          corner_radius=8, fg_color=COLOR_IDLE)
        self.pack_propagate(False)
        self._base_color = COLOR_IDLE
        lbl = ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=10, weight="bold"))
        lbl.pack(pady=(8, 1) if sub else 0, expand=not sub)
        widgets = [self, lbl]
        if sub:
            sub_lbl = ctk.CTkLabel(self, text=sub, font=ctk.CTkFont(size=8), text_color="#888")
            sub_lbl.pack(pady=(0, 6))
            widgets.append(sub_lbl)
        if command:
            for w in widgets:
                w.bind("<Button-1>", lambda e: command())

    def set_active(self, active: bool, active_color: str = "#e67e22"):
        self.configure(fg_color=active_color if active else self._base_color)


def blank_slot(master, width: int = 74, height: int = 40) -> ctk.CTkFrame:
    """Emplacement vide (fonction hardware non utilisée pour le moment)."""
    return ctk.CTkFrame(master, width=width, height=height, corner_radius=8,
                         fg_color="transparent", border_width=1, border_color="#3a3a3a")


class SequencerGUI(ctk.CTk):

    def __init__(self, engine: SequencerEngine):
        super().__init__()
        self.engine = engine
        self._selected_step: int | None = None
        self._toggle_buttons: list[tuple[CmdButton, object, str]] = []  # (widget, check_fn, color)

        self.title("Step Sequencer XP1")
        self.resizable(False, False)
        self._build_ui()
        self._build_scale_overlay()
        self._poll()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        ctk.CTkLabel(self, text="STEP SEQUENCER XP1",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(padx=16, pady=(12, 6))

        self._build_banner()
        self._build_info_row()

        top_controls = ctk.CTkFrame(self, fg_color="transparent")
        top_controls.pack(padx=16, pady=(0, 18))
        self._build_side_controls(top_controls, side="left").pack(side="left", padx=(0, 8))
        self._build_side_controls(top_controls, side="right").pack(side="left", padx=(8, 0))

        self._build_pad_section()

    def _build_banner(self):
        """Bandeau de statut : sync, mode Basse/Mélodie, sortie MIDI."""
        banner = ctk.CTkFrame(self, corner_radius=8)
        banner.pack(padx=16, pady=(0, 6), fill="x")

        self._sync_badge = ctk.CTkLabel(
            banner, text="● STANDALONE", corner_radius=999, fg_color="#333",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#ccc", padx=12, pady=4)
        self._sync_badge.pack(side="left", padx=12, pady=8)

        gen_frame = ctk.CTkFrame(banner, corner_radius=999, fg_color="#1a1a1a")
        gen_frame.pack(side="left", expand=True, pady=8)
        self._gen_bass_lbl = ctk.CTkLabel(
            gen_frame, text="BASSE", corner_radius=999,
            font=ctk.CTkFont(size=11, weight="bold"), padx=14, pady=4)
        self._gen_bass_lbl.pack(side="left", padx=2, pady=2)
        self._gen_mel_lbl = ctk.CTkLabel(
            gen_frame, text="MÉLODIE", corner_radius=999,
            font=ctk.CTkFont(size=11, weight="bold"), padx=14, pady=4)
        self._gen_mel_lbl.pack(side="left", padx=2, pady=2)

        self._out_badge = ctk.CTkLabel(
            banner, text="OUT: BOTH", corner_radius=999, fg_color="#333",
            font=ctk.CTkFont(size=11, weight="bold"), padx=12, pady=4)
        self._out_badge.pack(side="left", padx=12, pady=8)

        self._in_badge = ctk.CTkLabel(
            banner, text="IN: IAC", corner_radius=999, fg_color="#333",
            font=ctk.CTkFont(size=11, weight="bold"), padx=12, pady=4)
        self._in_badge.pack(side="left", padx=(0, 12), pady=8)

    def _build_info_row(self):
        """BPM (lecture seule, réglé via les boutons PAGE) + sélecteur de gamme."""
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(padx=16, pady=(0, 6))

        self._bpm_label = ctk.CTkLabel(
            info, text=f"{self.engine.bpm} BPM",
            font=ctk.CTkFont(size=15, weight="bold"), width=90)
        self._bpm_label.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(info, text="GAMME", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 4))
        self._root_var = ctk.StringVar(value="C")
        ctk.CTkOptionMenu(info, values=NOTE_NAMES, variable=self._root_var,
                          width=64, height=26, command=self._on_scale_change
                          ).pack(side="left", padx=4)
        self._mode_var = ctk.StringVar(value="Majeur")
        ctk.CTkOptionMenu(info, values=list(SCALES.keys()), variable=self._mode_var,
                          width=140, height=26, command=self._on_scale_change
                          ).pack(side="left", padx=4)

    # ── Rangées de commandes façon hardware (3x4 par côté) ─────────────

    def _build_side_controls(self, master, side: str) -> ctk.CTkFrame:
        specs = self._LEFT_SPECS if side == "left" else self._RIGHT_SPECS
        frame = ctk.CTkFrame(master, fg_color="transparent")
        for row in specs:
            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(pady=5)
            for cell in row:
                if cell.get("blank"):
                    w = blank_slot(row_frame)
                else:
                    w = CmdButton(row_frame, cell["label"], cell.get("sub"),
                                  command=cell["action"])
                    if "check" in cell:
                        self._toggle_buttons.append((w, cell["check"], cell.get("color", "#e67e22")))
                w.pack(side="left", padx=2)
        return frame

    # Chaque ligne regroupe des fonctions apparentées (BPM ensemble, note ensemble,
    # longueur ensemble) au lieu de suivre l'ordre brut des boutons hardware.
    @property
    def _LEFT_SPECS(self):
        e = self.engine
        return [
            [{"blank": True},
             {"label": "BASSE", "sub": "Quantize",
              "action": lambda: self._fire("gen_mode_bass"),
              "check": lambda: e.gen_mode == "bass", "color": GEN_COLORS["bass"]},
             {"blank": True}],
            [{"label": "REVERSE", "sub": "Slip Reverse",
              "action": lambda: self._fire("reverse"),
              "check": lambda: e.reverse, "color": "#e67e22"},
             {"label": "RND STEPS", "sub": "Master Tempo", "action": lambda: self._fire("rnd_steps")},
             {"label": "RND NOTES", "sub": "Beat Sync", "action": lambda: self._fire("rnd_notes")}],
            [{"label": "◄ BPM−1", "sub": "Page", "action": lambda: e.set_bpm(e.bpm - 1)},
             {"label": "BPM+1 ►", "sub": "Page", "action": lambda: e.set_bpm(e.bpm + 1)},
             {"label": "− ½t", "sub": "Semitone", "action": lambda: self._shift_note(-1)},
             {"label": "+ ½t", "sub": "Semitone", "action": lambda: self._shift_note(+1)}],
            [{"label": "MUTE", "sub": "Silent Cue",
              "action": lambda: self._fire("mute"),
              "check": lambda: e.muted, "color": "#c0392b"}],
        ]

    @property
    def _RIGHT_SPECS(self):
        e = self.engine
        return [
            [{"label": "OUT MIDI", "sub": "Loop In/Out", "action": self._cycle_output},
             {"label": "MÉLODIE", "sub": "Quantize",
              "action": lambda: self._fire("gen_mode_melody"),
              "check": lambda: e.gen_mode == "melody", "color": GEN_COLORS["melody"]},
             {"label": "IN CLOCK", "sub": None, "action": self._cycle_clock_source}],
            [{"label": "LEN 8", "sub": "Master Tempo",
              "action": lambda: e.set_length(8),
              "check": lambda: e.pattern_length == 8, "color": "#e67e22"},
             {"label": "LEN 16", "sub": "Beat Sync",
              "action": lambda: e.set_length(16),
              "check": lambda: e.pattern_length == 16, "color": "#e67e22"},
             {"label": "LEN 32", "sub": "Slip Reverse",
              "action": lambda: e.set_length(32),
              "check": lambda: e.pattern_length == 32, "color": "#e67e22"}],
            [{"label": "◄ BPM−5", "sub": "Page", "action": lambda: e.set_bpm(e.bpm - 5)},
             {"label": "BPM+5 ►", "sub": "Page", "action": lambda: e.set_bpm(e.bpm + 5)},
             {"label": "− oct", "sub": "Semitone", "action": lambda: self._shift_note(-12)},
             {"label": "+ oct", "sub": "Semitone", "action": lambda: self._shift_note(+12)}],
            [{"label": "CLEAR", "sub": "Silent Cue", "action": e.clear_pattern}],
        ]

    def _fire(self, btn_name: str):
        self.engine._handle_button(btn_name)

    def _cycle_clock_source(self):
        order = ["IAC", "HW"]
        current = self.engine.clock_source
        self.engine.set_clock_source(order[(order.index(current) + 1) % len(order)])

    def _cycle_output(self):
        order = ["out_iac", "out_hw", "out_both"]
        current = {"IAC": "out_iac", "HW": "out_hw", "BOTH": "out_both"}[self.engine.midi_out_mode]
        self._fire(order[(order.index(current) + 1) % 3])

    # ── Section pads : patterns + grilles + centre ─────────────────────

    def _build_pad_section(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=16, pady=(0, 6))

        self._build_pattern_column(row, [0, 1, 2]).pack(side="left", padx=(0, 8))
        self._build_deck(row, side="left").pack(side="left")
        self._build_deck(row, side="right").pack(side="left", padx=(6, 0))
        self._build_pattern_column(row, [3, 4, 5]).pack(side="left", padx=(8, 0))

        self._build_center_column(self).pack(pady=(4, 12))

    def _build_pattern_column(self, master, indices: list[int]) -> ctk.CTkFrame:
        col = ctk.CTkFrame(master, fg_color="transparent")
        if not hasattr(self, "_pat_btns"):
            self._pat_btns: list[CmdButton] = [None] * NUM_PATTERNS
        for i in indices:
            btn = CmdButton(col, PATTERN_LABELS[i], None,
                            command=lambda idx=i: self.engine.set_pattern(idx),
                            width=56, height=48)
            btn.pack(pady=4)
            self._pat_btns[i] = btn
            self._toggle_buttons.append(
                (btn, lambda idx=i: self.engine.active_pattern == idx, "#e67e22"))
        return col

    def _build_deck(self, master, side: str) -> ctk.CTkFrame:
        """Bloc mode (SAMPLER/BEAT JUMP) + grille 4x4 de pads, un côté du sampler."""
        deck = ctk.CTkFrame(master, fg_color="transparent")
        mode_row = ctk.CTkFrame(deck, fg_color="transparent")
        mode_row.pack(pady=(0, 4))

        sampler_btn = CmdButton(mode_row, "SAMPLER", None,
                                command=lambda: self._fire(f"mode_sampler_{side[0]}"),
                                width=90, height=28)
        beatjump_btn = CmdButton(mode_row, "BEAT JUMP", None,
                                 command=lambda: self._fire(f"mode_beatjump_{side[0]}"),
                                 width=90, height=28)
        beatjump_btn.pack(side="left", padx=2)
        sampler_btn.pack(side="left", padx=2)
        self._toggle_buttons.append((sampler_btn, lambda: self.engine.ui_mode == "sequencer", "#1abc9c"))
        self._toggle_buttons.append((beatjump_btn, lambda: self.engine.ui_mode == "scale", "#9b59b6"))

        if not hasattr(self, "_pads"):
            self._pads: list[Pad] = [None] * NUM_STEPS
        grid = ctk.CTkFrame(deck, fg_color="transparent")
        grid.pack()
        col_offset = 0 if side == "left" else 4
        for r in range(4):
            row_frame = ctk.CTkFrame(grid, fg_color="transparent")
            row_frame.pack(pady=2)
            for c in range(4):
                step = r * 8 + c + col_offset
                p = Pad(row_frame, step,
                        on_click=self._on_pad_click,
                        on_right_click=self._on_pad_right_click)
                p.pack(side="left", padx=2)
                self._pads[step] = p
        return deck

    def _make_circle(self, master, text: str, color: str, command, diameter: int,
                      font_size: int = 13) -> ctk.CTkLabel:
        """Bouton rond façon INT/SHIFT du hardware. command=None → juste décoratif."""
        lbl = ctk.CTkLabel(master, text=text, width=diameter, height=diameter,
                           corner_radius=diameter // 2, fg_color=color,
                           font=ctk.CTkFont(size=font_size, weight="bold"))
        if command:
            lbl.bind("<Button-1>", lambda e: command())
        return lbl

    def _build_center_column(self, master) -> ctk.CTkFrame:
        """Bandeau horizontal (sous les pads) : INT/SHIFT, encodeur, statut, note, reset."""
        bar = ctk.CTkFrame(master, fg_color="transparent")

        int_row = ctk.CTkFrame(bar, fg_color="transparent")
        int_row.pack(side="left", padx=(0, 20))
        self._make_circle(int_row, "▶", "#1e5c33", lambda: self._fire("play"), 36
                          ).pack(side="left", padx=3)
        self._make_circle(int_row, "SHIFT", "#3a2a10", None, 40, font_size=9
                          ).pack(side="left", padx=3)
        self._make_circle(int_row, "■", "#5c1e1e", lambda: self._fire("stop"), 36
                          ).pack(side="left", padx=3)

        self._status_label = ctk.CTkLabel(bar, text="■ STOP", width=90,
                                          font=ctk.CTkFont(size=13, weight="bold"))
        self._status_label.pack(side="left", padx=(0, 20))

        note_row = ctk.CTkFrame(bar, fg_color="transparent")
        note_row.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(note_row, text="Step", font=ctk.CTkFont(size=10),
                     text_color="#888").grid(row=0, column=0)
        self._step_label = ctk.CTkLabel(note_row, text="—", font=ctk.CTkFont(size=13, weight="bold"))
        self._step_label.grid(row=1, column=0)
        ctk.CTkLabel(note_row, text="Note", font=ctk.CTkFont(size=10),
                     text_color="#888").grid(row=0, column=1, padx=(14, 0))
        self._note_label = ctk.CTkLabel(note_row, text="—",
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        text_color="#e67e22")
        self._note_label.grid(row=1, column=1, padx=(14, 0))

        ctk.CTkButton(bar, text="↩ RESET", width=90, height=30,
                      fg_color="#7f8c8d", hover_color="#626b6c",
                      command=self.engine.reset).pack(side="left")
        return bar

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
        self._refresh_status()
        self._refresh_banner()
        self._refresh_toggle_buttons()
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
            btn.set_state(color, text)

    def _refresh_bpm(self):
        self._bpm_label.configure(text=f"{self.engine.bpm} BPM")

    def _refresh_toggle_buttons(self):
        for widget, check, color in self._toggle_buttons:
            widget.set_active(bool(check()), color)

    def _refresh_status(self):
        if self.engine.playing:
            self._status_label.configure(text="▶ LECTURE", text_color="#27ae60")
        elif self.engine._pending_start:
            tick = int(time.time() * 2) % 2
            self._status_label.configure(
                text="⏱ QUANTIZE...", text_color="#e67e22" if tick else "#7f5200")
        else:
            self._status_label.configure(text="■ STOP", text_color="#c0392b")

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

    def _refresh_banner(self):
        if self.engine.synced_to_ableton:
            self._sync_badge.configure(text=f"● SYNC {self.engine.clock_source}",
                                        fg_color="#1f3a52", text_color="#3498db")
        else:
            self._sync_badge.configure(text="● STANDALONE", fg_color="#333", text_color="#ccc")

        self._in_badge.configure(text=f"IN: {self.engine.clock_source}")

        bass_on = self.engine.gen_mode == "bass"
        self._gen_bass_lbl.configure(
            fg_color=GEN_COLORS["bass"] if bass_on else "transparent",
            text_color="white" if bass_on else "#888")
        self._gen_mel_lbl.configure(
            fg_color=GEN_COLORS["melody"] if not bass_on else "transparent",
            text_color="white" if not bass_on else "#888")

        mode = self.engine.midi_out_mode
        self._out_badge.configure(text=f"OUT: {mode}", fg_color="#333", text_color=OUT_COLORS[mode])


# ── Point d'entrée ────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = SequencerEngine()
    engine.start()

    app = SequencerGUI(engine)
    app.mainloop()

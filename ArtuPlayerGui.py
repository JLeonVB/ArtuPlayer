import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mido
from mido import MidiFile, MidiTrack, MetaMessage
import fluidsynth
import threading
import time
import os

class ArtuPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("ArtuPlayer v8 - Relative Encoder")
        self.root.geometry("600x650")
        self.root.configure(bg="#1e1e1e")
        
        # --- VARIABLES ---
        self.running = True
        self.fs = None
        self.inport = None
        self.outport = None
        
        self.master_gain = 1.0
        self.velocity_scale = 1.0
        
        # Grabación
        self.grabando = False
        self.reproduciendo = False
        self.eventos_grabados = []
        self.tiempo_inicio_rec = 0
        self.ultimo_midi_path = None

        # LISTA DE INSTRUMENTOS
        self.instrumentos_lista = [
            ("Grand Piano", 0), ("Bright Piano", 1), ("Electric Piano", 4),
            ("Honky-tonk", 3), ("Organ (Rock)", 18), ("Church Organ", 19),
            ("Guitar (Nylon)", 24), ("Guitar (Distortion)", 30), ("Bass (Finger)", 33),
            ("Violin", 40), ("Strings", 48), ("Trumpet", 56), ("Saxophone", 65),
            ("Flute", 73), ("Synth Lead", 81), ("Synth Pad", 89), ("Drums", 115)
        ]
        self.current_inst_index = 0

        # --- INTERFAZ ---
        main_frame = ttk.Frame(root, padding=15)
        main_frame.pack(fill="both", expand=True)

        # 1. Header
        lbl_title = ttk.Label(main_frame, text="ARTUPLAYER V8", font=("Arial", 20, "bold"), foreground="#00ff99")
        lbl_title.pack(pady=(0, 5))
        self.status_var = tk.StringVar(value="Buscando MIDI...")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="#aaaaaa").pack()

        # 2. INSTRUMENTO (Encoder)
        inst_frame = ttk.LabelFrame(main_frame, text=" Instrumento Seleccionado ", padding=10)
        inst_frame.pack(fill="x", pady=10)
        
        self.inst_var = tk.StringVar(value=f"1. {self.instrumentos_lista[0][0]}")
        self.lbl_inst = tk.Label(inst_frame, textvariable=self.inst_var, font=("Impact", 28), bg="#222", fg="#00ccff", width=20)
        self.lbl_inst.pack()
        ttk.Label(inst_frame, text="Gira el Encoder Negro para cambiar", font=("Segoe UI", 8)).pack()

        # 3. SLIDER 2 - GAIN
        gain_frame = ttk.LabelFrame(main_frame, text=" Master Gain (Slider 2) ", padding=10)
        gain_frame.pack(fill="x", pady=5)
        
        self.progress_gain = ttk.Progressbar(gain_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_gain.pack(fill="x", pady=5)
        self.progress_gain['value'] = 50
        self.lbl_gain_val = tk.Label(gain_frame, text="50%", bg="#1e1e1e", fg="orange")
        self.lbl_gain_val.pack()

        # 4. Nota y Transporte
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=10)
        self.lbl_nota = tk.Label(info_frame, text="--", font=("Impact", 30), bg="black", fg="#ffffff", width=4)
        self.lbl_nota.pack(side="left", padx=10)
        
        self.btn_rec = ttk.Button(info_frame, text="⏺ GRABAR", command=self.toggle_grabacion)
        self.btn_rec.pack(side="left", fill="x", expand=True, padx=5)

        # Iniciar
        self.iniciar_audio()
        threading.Thread(target=self.conectar_midi, daemon=True).start()

    def iniciar_audio(self):
        sf2_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
        if not os.path.exists(sf2_path): return
        drivers = ['pulseaudio', 'alsa', 'oss']
        for driver in drivers:
            try:
                self.fs = fluidsynth.Synth()
                self.fs.start(driver=driver)
                sfid = self.fs.sfload(sf2_path)
                self.fs.program_select(0, sfid, 0, 0)
                break
            except: pass

    def conectar_midi(self):
        # Espera y busca flexiblemente
        time.sleep(1)
        entradas = mido.get_input_names()
        nombre = None
        for p in entradas:
            if "minilab" in p.lower() or "arturia" in p.lower():
                nombre = p
                break
        
        if nombre:
            try:
                self.inport = mido.open_input(nombre)
                self.outport = mido.open_output(nombre)
                self.status_var.set(f"Conectado: {nombre}")
                self.despertar_lcd()
                self.escribir_lcd("ARTUPLAYER V8", "RELATIVE MODE")
                self.loop_midi()
            except: self.status_var.set("Error: Puerto ocupado")
        else:
            self.status_var.set("MiniLab no encontrado")

    def despertar_lcd(self):
        if self.outport:
            self.outport.send(mido.Message('sysex', data=[0x00, 0x20, 0x6B, 0x7F, 0x42, 0x02, 0x00, 0x40, 0x52, 0x00]))

    def escribir_lcd(self, l1, l2=""):
        if not self.outport: return
        try:
            base = [0x00, 0x20, 0x6B, 0x7F, 0x42, 0x04, 0x00, 0x60]
            p1 = base + [0x01] + [ord(c) for c in str(l1).ljust(16)[:16]] + [0x00]
            self.outport.send(mido.Message('sysex', data=p1))
            p2 = base + [0x02] + [ord(c) for c in str(l2).ljust(16)[:16]] + [0x00]
            self.outport.send(mido.Message('sysex', data=p2))
        except: pass

    def cambiar_instrumento_relativo(self, direction):
        """
        Direction: +1 para siguiente, -1 para anterior
        """
        nuevo_idx = self.current_inst_index + direction
        
        # Clampear (que no baje de 0 ni suba del maximo)
        if 0 <= nuevo_idx < len(self.instrumentos_lista):
            self.current_inst_index = nuevo_idx
            nombre, prog = self.instrumentos_lista[self.current_inst_index]
            
            # Cambiar sonido
            if self.fs: self.fs.program_select(0, self.fs.sfid, 0, prog)
            
            # Actualizar GUI
            texto = f"{nuevo_idx + 1}. {nombre}"
            self.root.after(0, lambda: self.inst_var.set(texto))
            self.escribir_lcd("Inst:", nombre)

    def loop_midi(self):
        while self.running:
            if self.inport:
                for msg in self.inport.iter_pending():
                    if self.grabando: self.eventos_grabados.append((time.time() - self.tiempo_inicio_rec, msg))

                    # --- LÓGICA ENCODER RELATIVO (CC 28) ---
                    if msg.type == 'control_change' and msg.control == 28:
                        val = msg.value
                        # Lógica Arturia Relativa:
                        # > 64 (ej: 65, 66) = Derecha
                        # < 64 (ej: 63, 61) = Izquierda
                        if val >= 65:
                            self.cambiar_instrumento_relativo(1) # Siguiente
                        elif val <= 63:
                            self.cambiar_instrumento_relativo(-1) # Anterior

                    # --- SLIDER 2: GAIN (CC 15) ---
                    elif msg.type == 'control_change' and msg.control == 15:
                        self.master_gain = (msg.value / 64) # 0 a 2.0x
                        porcentaje = int(msg.value / 1.27)
                        
                        self.root.after(0, lambda v=porcentaje: self.progress_gain.configure(value=v))
                        self.root.after(0, lambda v=porcentaje: self.lbl_gain_val.config(text=f"{v}%"))
                        self.escribir_lcd("MASTER GAIN", f"{porcentaje}%")

                    # --- NOTAS ---
                    elif msg.type == 'note_on' and msg.velocity > 0 and msg.channel == 0:
                        vel = int(msg.velocity * self.master_gain)
                        if vel > 127: vel = 127
                        if self.fs: self.fs.noteon(0, msg.note, vel)
                        self.root.after(0, lambda n=msg.note: self.lbl_nota.config(text=str(n), fg="#00ff00"))
                        
                    elif (msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)) and msg.channel == 0:
                        if self.fs: self.fs.noteoff(0, msg.note)
                        self.root.after(0, lambda: self.lbl_nota.config(fg="white"))

            time.sleep(0.001)

    # (Funciones de grabacion omitidas para brevedad, son las mismas de la v6)
    def toggle_grabacion(self):
        if not self.grabando:
            self.grabando = True
            self.eventos_grabados = []
            self.tiempo_inicio_rec = time.time()
            self.btn_rec.config(text="⏹ DETENER")
        else:
            self.grabando = False
            self.btn_rec.config(text="⏺ GRABAR")
            self.guardar_midi_archivo()

    def guardar_midi_archivo(self):
        if not self.eventos_grabados: return
        filename = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI", "*.mid")])
        if not filename: return
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('set_tempo', tempo=500000))
        last_time = 0
        for t, msg in self.eventos_grabados:
            delta = int((t - last_time) * 1000)
            last_time = t
            new_msg = msg.copy()
            new_msg.time = delta
            track.append(new_msg)
        mid.save(filename)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArtuPlayer(root)
    root.mainloop()

import tkinter as tk
from tkinter import ttk
import mido
import fluidsynth
import threading
import time
import os
import sys

class ArtuPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("ArtuPlayer v1 - Stable")
        self.root.geometry("400x300")
        self.root.configure(bg="#222222")

        # Limpieza obligatoria al cerrar (Para evitar error de puertos)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_programa)

        self.running = True
        self.fs = None
        self.sfid = None
        self.inport = None

        # --- INTERFAZ SIMPLE ---
        main_frame = tk.Frame(root, bg="#222222")
        main_frame.pack(expand=True, fill="both")

        tk.Label(main_frame, text="🎹 PIANO BÁSICO", font=("Arial", 20, "bold"), bg="#222", fg="white").pack(pady=20)
        
        self.lbl_status = tk.Label(main_frame, text="Cargando...", font=("Arial", 10), bg="#222", fg="yellow")
        self.lbl_status.pack()

        self.lbl_nota = tk.Label(main_frame, text="--", font=("Impact", 60), bg="#222", fg="#00ff00")
        self.lbl_nota.pack(pady=30)

        # Iniciar todo
        self.iniciar_audio()
        threading.Thread(target=self.conectar_midi, daemon=True).start()

    def iniciar_audio(self):
        # Ruta estándar en Linux
        sf2_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
        
        if not os.path.exists(sf2_path):
            self.lbl_status.config(text="ERROR: No se encontró FluidR3_GM.sf2")
            return

        # Intentar drivers de audio de Linux
        drivers = ['pulseaudio', 'alsa', 'oss']
        for driver in drivers:
            try:
                self.fs = fluidsynth.Synth()
                self.fs.start(driver=driver)
                
                # Cargar Piano (SoundFont)
                self.sfid = self.fs.sfload(sf2_path)
                self.fs.program_select(0, self.sfid, 0, 0) # 0 = Grand Piano
                
                print(f"Audio iniciado con: {driver}")
                break
            except:
                pass

    def conectar_midi(self):
        time.sleep(1) # Esperar a que el sistema respire
        entradas = mido.get_input_names()
        
        # Buscar algo que se parezca a Arturia o MiniLab
        nombre_puerto = None
        for p in entradas:
            if "minilab" in p.lower() or "arturia" in p.lower():
                nombre_puerto = p
                break
        
        if nombre_puerto:
            try:
                self.inport = mido.open_input(nombre_puerto)
                self.lbl_status.config(text=f"Conectado a: {nombre_puerto}", fg="cyan")
                self.loop_midi()
            except:
                self.lbl_status.config(text="ERROR: Puerto MIDI Ocupado", fg="red")
        else:
            self.lbl_status.config(text="No se encontró MiniLab", fg="red")

    def loop_midi(self):
        while self.running:
            if self.inport:
                for msg in self.inport.iter_pending():
                    # Solo nos importan las notas (Note On / Note Off)
                    
                    # Tocar nota
                    if msg.type == 'note_on' and msg.velocity > 0:
                        if self.fs: self.fs.noteon(0, msg.note, msg.velocity)
                        self.root.after(0, lambda n=msg.note: self.lbl_nota.config(text=str(n)))

                    # Soltar nota
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        if self.fs: self.fs.noteoff(0, msg.note)
                        self.root.after(0, lambda: self.lbl_nota.config(text="--"))
            
            time.sleep(0.001) # Pequeña pausa para no quemar el procesador

    def cerrar_programa(self):
        """Limpieza para que no falle la próxima vez"""
        self.running = False
        try:
            if self.inport: self.inport.close()
            if self.fs: self.fs.delete()
        except: pass
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArtuPlayer(root)
    root.mainloop()

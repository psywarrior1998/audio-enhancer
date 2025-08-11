import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
import librosa # Added to get audio duration

class VocalEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Intelligent Vocal Enhancer (ETA v2.1)")
        self.root.geometry("500x600")
        self.style = ttk.Style(root)
        self.style.theme_use('clam')

        # --- Processing state ---
        self.is_processing = False
        self.start_time = 0
        self.estimated_total_time = 0

        self.create_widgets(ttk.Frame(root, padding="20"))

    def create_widgets(self, parent):
        parent.pack(expand=True, fill=tk.BOTH)

        # --- File Selection ---
        ttk.Label(parent, text="Select Input Audio File:").grid(row=0, column=0, columnspan=3, sticky="w", pady=5)
        self.file_entry = ttk.Entry(parent, width=60)
        self.file_entry.grid(row=1, column=0, columnspan=2, sticky="we")
        ttk.Button(parent, text="Browse", command=self.browse_file).grid(row=1, column=2, sticky="e")

        # --- Processing Options ---
        options_frame = ttk.LabelFrame(parent, text="Vocal Processing Chain", padding=15)
        options_frame.grid(row=2, column=0, columnspan=3, sticky="we", pady=15)

        ttk.Label(options_frame, text="1. Separation Model:").pack(anchor="w")
        self.separation_var = tk.StringVar(value='Demucs (Fastest)')
        ttk.Radiobutton(options_frame, text="Demucs (Fastest CPU Model)", variable=self.separation_var, value='Demucs (Fastest)').pack(anchor="w", padx=20)
        ttk.Radiobutton(options_frame, text="Spleeter", variable=self.separation_var, value='Spleeter').pack(anchor="w", padx=20)

        ttk.Label(options_frame, text="\n2. Noise Gate Threshold (dBFS):").pack(anchor="w")
        self.gate_threshold_var = tk.StringVar(value="-40")
        self.gate_slider = ttk.Scale(options_frame, from_=-60, to=-20, orient=tk.HORIZONTAL, command=lambda s: self.gate_threshold_var.set(f"{float(s):.0f}"))
        self.gate_slider.set(-40)
        self.gate_slider.pack(fill='x', padx=20)
        ttk.Label(options_frame, textvariable=self.gate_threshold_var).pack(anchor="w", padx=20)
        ttk.Label(options_frame, text="(Lower dB = more aggressive gating)", font=("TkDefaultFont", 8)).pack(anchor="w", padx=20)

        self.compress_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="\n3. Apply Dynamic Compression (Makes Vocals Louder)", variable=self.compress_var).pack(anchor="w")

        # --- Execution ---
        self.process_button = ttk.Button(parent, text="Enhance Vocals", command=self.start_processing_thread)
        self.process_button.grid(row=3, column=0, columnspan=3, pady=10)
        self.status_label = ttk.Label(parent, text="Status: Idle")
        self.status_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=5)
        
        # Timer and ETA labels
        self.timer_label = ttk.Label(parent, text="Elapsed Time: 0s")
        self.timer_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=5)
        self.eta_label = ttk.Label(parent, text="Time Remaining: N/A")
        self.eta_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=5)

        self.progress = ttk.Progressbar(parent, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=3, sticky="we")

    def set_status(self, message, value):
        self.status_label['text'] = f"Status: {message}"
        self.progress['value'] = value

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)

    def start_processing_thread(self):
        input_path = self.file_entry.get()
        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid audio file first.")
            return
        
        self.process_button.config(state=tk.DISABLED)
        self.is_processing = True
        
        # --- ETA Calculation ---
        try:
            audio_duration = librosa.get_duration(filename=input_path)
            # Estimate: ~45 seconds of processing per 60 seconds of audio (ratio=0.75)
            # This is a heuristic and can be adjusted.
            self.estimated_total_time = audio_duration * 0.75 
        except Exception:
            self.estimated_total_time = 0 # Cannot estimate if duration fails

        self.start_time = time.time()
        self.update_timer()

        thread = threading.Thread(target=self.process_audio)
        thread.daemon = True
        thread.start()

    def update_timer(self):
        if self.is_processing:
            elapsed_time = time.time() - self.start_time
            self.timer_label['text'] = f"Elapsed Time: {int(elapsed_time)}s"

            if self.estimated_total_time > 0:
                remaining_time = self.estimated_total_time - elapsed_time
                if remaining_time > 0:
                    self.eta_label['text'] = f"Time Remaining: ~{int(remaining_time)}s"
                else:
                    self.eta_label['text'] = "Time Remaining: Finishing up..."
            else:
                self.eta_label['text'] = "Time Remaining: Calculating..."

            self.root.after(1000, self.update_timer)

    def apply_noise_gate(self, segment, threshold_dbfs, keep_silence_ms=100):
        chunks = split_on_silence(segment, min_silence_len=500, silence_thresh=threshold_dbfs, keep_silence=keep_silence_ms)
        return sum(chunks) if chunks else AudioSegment.silent(duration=len(segment))

    def process_audio(self):
        input_path = self.file_entry.get()
        output_dir = os.path.join(os.path.dirname(input_path), "output_audio")
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            self.progress.config(mode='indeterminate')
            self.progress.start()
            self.set_status("Separating vocals (this may take time)...", 0)
            
            model = self.separation_var.get()
            if model == 'Demucs (Fastest)':
                cmd = ["demucs", "-n", "htdemucs_ft", "--two-stems=vocals", "-o", temp_dir, input_path]
            else:
                cmd = ["spleeter", "separate", "-p", "spleeter:2stems", "-o", temp_dir, input_path]
            subprocess.run(cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.progress.stop()
            self.progress.config(mode='determinate')
            
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            vocals_path = os.path.join(temp_dir, "htdemucs_ft" if model == 'Demucs (Fastest)' else "", base_name, "vocals.wav")
            if model != 'Demucs (Fastest)':
                vocals_path = os.path.join(temp_dir, base_name, "vocals.wav")


            if not os.path.exists(vocals_path): raise FileNotFoundError("Separated vocals file not found.")

            self.set_status("Applying noise gate...", 65)
            vocal_segment = AudioSegment.from_file(vocals_path)
            gate_threshold = float(self.gate_threshold_var.get())
            gated_vocals = self.apply_noise_gate(vocal_segment, gate_threshold)
            
            processed_vocals = gated_vocals
            if self.compress_var.get():
                self.set_status("Applying compression...", 80)
                processed_vocals = effects.compress_dynamic_range(gated_vocals)
            
            self.set_status("Normalizing and saving...", 95)
            final_vocals = effects.normalize(processed_vocals)
            final_output_path = os.path.join(output_dir, f"{base_name}_vocals_enhanced.wav")
            final_vocals.export(final_output_path, format="wav")

            self.set_status("Enhancement Complete!", 100)
            messagebox.showinfo("Success", f"Processing complete!\nEnhanced file saved to:\n{final_output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}\n\nCheck console for details.")
            print(f"ERROR: {e}")
        finally:
            self.is_processing = False
            self.progress.stop()
            self.progress.config(mode='determinate')
            self.set_status("Idle", 0)
            self.eta_label['text'] = "Time Remaining: N/A"
            self.process_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = VocalEnhancerApp(root)
    root.mainloop()
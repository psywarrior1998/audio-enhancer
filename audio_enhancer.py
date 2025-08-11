import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
import re
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
import librosa

class ModularAudioProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("Modular Audio Processor (v4.0)")
        self.root.geometry("550x650")
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.is_processing = False
        self.start_time = 0
        self.create_widgets(ttk.Frame(root, padding="20"))

    def create_widgets(self, parent):
        parent.pack(expand=True, fill=tk.BOTH)
        # --- File Selection ---
        ttk.Label(parent, text="Select Input Audio File:").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))
        self.file_entry = ttk.Entry(parent, width=60)
        self.file_entry.grid(row=1, column=0, columnspan=2, sticky="we")
        ttk.Button(parent, text="Browse", command=self.browse_file).grid(row=1, column=2, sticky="e")

        # --- Processing Modules ---
        modules_frame = ttk.LabelFrame(parent, text="Processing Modules", padding=15)
        modules_frame.grid(row=2, column=0, columnspan=3, sticky="we", pady=15)

        # Module 1: Vocal Separation
        self.sep_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(modules_frame, text="1. Isolate Vocals (AI Separation)", variable=self.sep_var, command=self.toggle_separation_options).pack(anchor="w")
        self.sep_options_frame = ttk.Frame(modules_frame, padding=(20, 5))
        self.sep_options_frame.pack(fill='x')
        self.separation_model_var = tk.StringVar(value='Demucs')
        ttk.Radiobutton(self.sep_options_frame, text="Demucs (Provides Exact ETA)", variable=self.separation_model_var, value='Demucs').pack(anchor="w")
        ttk.Radiobutton(self.sep_options_frame, text="Spleeter", variable=self.separation_model_var, value='Spleeter').pack(anchor="w")

        # Module 2: Noise Gate
        self.gate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(modules_frame, text="2. Apply Noise Gate", variable=self.gate_var, command=self.toggle_gate_options).pack(anchor="w", pady=(10, 0))
        self.gate_options_frame = ttk.Frame(modules_frame, padding=(20, 5))
        self.gate_options_frame.pack(fill='x')
        ttk.Label(self.gate_options_frame, text="Threshold (dBFS):").pack(anchor="w")
        self.gate_threshold_var = tk.StringVar(value="-40")
        self.gate_slider = ttk.Scale(self.gate_options_frame, from_=-60, to=-20, orient=tk.HORIZONTAL, command=lambda s: self.gate_threshold_var.set(f"{float(s):.0f}"))
        self.gate_slider.set(-40)
        self.gate_slider.pack(fill='x')
        ttk.Label(self.gate_options_frame, textvariable=self.gate_threshold_var).pack(anchor="w")

        # Module 3: Compression
        self.compress_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(modules_frame, text="3. Apply Dynamic Compression", variable=self.compress_var).pack(anchor="w", pady=(10, 0))

        # --- Execution ---
        self.process_button = ttk.Button(parent, text="Process Audio", command=self.start_processing_thread)
        self.process_button.grid(row=3, column=0, columnspan=3, pady=10)
        self.status_label = ttk.Label(parent, text="Status: Idle")
        self.status_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=5)
        self.eta_label = ttk.Label(parent, text="Time Remaining: N/A")
        self.eta_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=5)
        self.progress = ttk.Progressbar(parent, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky="we")

    def toggle_separation_options(self):
        state = "normal" if self.sep_var.get() else "disabled"
        for child in self.sep_options_frame.winfo_children():
            child.configure(state=state)

    def toggle_gate_options(self):
        state = "normal" if self.gate_var.get() else "disabled"
        for child in self.gate_options_frame.winfo_children():
            child.configure(state=state)

    def set_status(self, message, value=None):
        self.status_label['text'] = f"Status: {message}"
        if value is not None: self.progress['value'] = value

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)

    def start_processing_thread(self):
        if not self.file_entry.get():
            messagebox.showerror("Error", "Please select an audio file first.")
            return
        self.process_button.config(state=tk.DISABLED)
        self.is_processing = True
        self.start_time = time.time()
        thread = threading.Thread(target=self.process_audio)
        thread.daemon = True
        thread.start()

    def apply_noise_gate(self, segment, threshold_dbfs):
        return sum(split_on_silence(segment, min_silence_len=500, silence_thresh=threshold_dbfs, keep_silence=100)) or AudioSegment.silent(duration=len(segment))

    def process_audio(self):
        input_path = self.file_entry.get()
        output_dir = os.path.join(os.path.dirname(input_path), "output_audio")
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            current_audio = AudioSegment.from_file(input_path)
            output_suffix = ""

            # --- Module 1: Vocal Separation ---
            if self.sep_var.get():
                model = self.separation_model_var.get()
                self.set_status(f"Separating vocals with {model}...", 0)
                output_suffix += "_vocals"

                if model == 'Demucs':
                    cmd = ["demucs", "-n", "htdemucs_ft", "--two-stems=vocals", "-o", temp_dir, input_path]
                    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, universal_newlines=True)
                    for line in iter(process.stderr.readline, ''):
                        match = re.search(r'\|\s*(\d+)%', line)
                        if match:
                            percentage = int(match.group(1))
                            self.set_status(f"Separating vocals ({percentage}%)", percentage)
                            elapsed_time = time.time() - self.start_time
                            if percentage > 5:
                                total_time = (elapsed_time / percentage) * 100
                                self.eta_label['text'] = f"Time Remaining: ~{int(total_time - elapsed_time)}s"
                    process.wait()
                else: # Spleeter
                    self.progress.config(mode='indeterminate'); self.progress.start()
                    cmd = ["spleeter", "separate", "-p", "spleeter:2stems", "-o", temp_dir, input_path]
                    subprocess.run(cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.progress.stop(); self.progress.config(mode='determinate')

                base_name = os.path.splitext(os.path.basename(input_path))[0]
                vocals_path = os.path.join(temp_dir, "htdemucs_ft" if model == 'Demucs' else "", base_name, "vocals.wav")
                if model != 'Demucs': vocals_path = os.path.join(temp_dir, base_name, "vocals.wav")
                if not os.path.exists(vocals_path): raise FileNotFoundError("Separated vocals file not found.")
                current_audio = AudioSegment.from_file(vocals_path)
            
            # --- Module 2: Noise Gate ---
            if self.gate_var.get():
                self.set_status("Applying noise gate...", self.progress['value'])
                output_suffix += "_gated"
                current_audio = self.apply_noise_gate(current_audio, float(self.gate_threshold_var.get()))

            # --- Module 3: Compression ---
            if self.compress_var.get():
                self.set_status("Applying compression...", self.progress['value'])
                output_suffix += "_compressed"
                current_audio = effects.compress_dynamic_range(current_audio)

            # --- Finalization ---
            self.set_status("Normalizing and saving...", 98)
            final_audio = effects.normalize(current_audio)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            final_output_path = os.path.join(output_dir, f"{base_name}{output_suffix}.wav")
            final_audio.export(final_output_path, format="wav")

            self.set_status("Processing Complete!", 100)
            messagebox.showinfo("Success", f"Processing complete!\nFile saved to:\n{final_output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.is_processing = False
            self.set_status("Idle", 0)
            self.eta_label['text'] = "Time Remaining: N/A"
            self.process_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModularAudioProcessor(root)
    root.mainloop()
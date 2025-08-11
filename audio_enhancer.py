import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import soundfile as sf
import librosa
import noisereduce as nr

class AudioEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Enhancer Tool")
        self.root.geometry("450x450")

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Frame
        frame = ttk.Frame(root, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)

        # UI Elements
        self.create_widgets(frame)

    def create_widgets(self, parent):
        """Creates and arranges all the UI widgets."""
        # File Selection
        ttk.Label(parent, text="Select Input Audio File:").grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        self.file_entry = ttk.Entry(parent, width=50)
        self.file_entry.grid(row=1, column=0, columnspan=2, sticky="we", padx=(0, 5))
        ttk.Button(parent, text="Browse", command=self.browse_file).grid(row=1, column=2, sticky="we")

        # Denoise Passes
        ttk.Label(parent, text="Denoise Passes:").grid(row=2, column=0, sticky="w", pady=10)
        self.passes_entry = ttk.Spinbox(parent, from_=1, to=5, width=5)
        self.passes_entry.set("1")
        self.passes_entry.grid(row=2, column=1, sticky="w")

        # Normalization
        self.normalize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Normalize Audio to -3 dB", variable=self.normalize_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        # Separation Model
        ttk.Label(parent, text="Separation Model:").grid(row=4, column=0, sticky="w", pady=10)
        self.separation_var = tk.StringVar(value='Demucs')
        ttk.Radiobutton(parent, text="Demucs", variable=self.separation_var, value='Demucs').grid(row=5, column=0, sticky="w")
        ttk.Radiobutton(parent, text="Spleeter", variable=self.separation_var, value='Spleeter').grid(row=5, column=1, sticky="w")

        # Output Format
        ttk.Label(parent, text="Output Format:").grid(row=6, column=0, sticky="w", pady=10)
        self.output_format_var = tk.StringVar(value="wav")
        ttk.Combobox(parent, textvariable=self.output_format_var, values=["wav", "flac", "mp3"], state="readonly").grid(row=6, column=1, sticky="w")

        # Process Button
        self.process_button = ttk.Button(parent, text="Process Audio", command=self.process_audio)
        self.process_button.grid(row=7, column=0, columnspan=3, pady=20)
        
        # Progress Bar
        self.progress = ttk.Progressbar(parent, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=8, column=0, columnspan=3, sticky="we")

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)

    def process_audio(self):
        input_path = self.file_entry.get()
        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Invalid input file path.")
            return

        self.process_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.root.update_idletasks()

        try:
            # 1. Denoise
            self.progress['value'] = 10
            self.root.update_idletasks()
            audio, sr = librosa.load(input_path, sr=None, mono=False)
            passes = int(self.passes_entry.get())
            
            # If stereo, denoise each channel separately
            if audio.ndim > 1:
                denoised_channels = [nr.reduce_noise(y=channel, sr=sr) for channel in audio]
                denoised_audio = np.array(denoised_channels)
            else:
                denoised_audio = nr.reduce_noise(y=audio, sr=sr)

            # Transpose back to (samples, channels) for saving
            if denoised_audio.ndim > 1:
                 denoised_audio = denoised_audio.T
            
            self.progress['value'] = 40
            self.root.update_idletasks()

            # 2. Save denoised temporary file to pass to separator
            temp_denoised_path = os.path.join(os.path.dirname(input_path), "temp_denoised.wav")
            sf.write(temp_denoised_path, denoised_audio, sr)

            # 3. Separate Vocals
            output_dir = os.path.join(os.path.dirname(input_path), "output_audio")
            os.makedirs(output_dir, exist_ok=True)
            separator = self.separation_var.get()
            
            if separator == 'Demucs':
                # Using subprocess for robust execution
                command = ["demucs", "--two-stems=vocals", "-o", output_dir, temp_denoised_path]
            else: # Spleeter
                command = ["spleeter", "separate", "-p", "spleeter:2stems", "-o", output_dir, temp_denoised_path]
            
            subprocess.run(command, check=True, shell=True)
            self.progress['value'] = 80
            self.root.update_idletasks()

            # 4. Normalize and Save Final Vocal Track
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            if separator == 'Demucs':
                separated_vocals_path = os.path.join(output_dir, "htdemucs", os.path.basename(temp_denoised_path).replace('.wav',''), "vocals.wav")
            else: #Spleeter
                separated_vocals_path = os.path.join(output_dir, os.path.splitext(os.path.basename(temp_denoised_path))[0], "vocals.wav")

            if not os.path.exists(separated_vocals_path):
                raise FileNotFoundError("Separated vocals file not found. Check separator output.")

            vocals, sr_vocals = librosa.load(separated_vocals_path, sr=None)
            
            if self.normalize_var.get():
                peak = np.max(np.abs(vocals))
                if peak > 0:
                    scaling_factor = 10**((-3 - 20 * np.log10(peak)) / 20)
                    vocals = vocals * scaling_factor
            
            output_format = self.output_format_var.get()
            final_output_path = os.path.join(os.path.dirname(input_path), f"{base_name}_enhanced_vocals.{output_format}")
            sf.write(final_output_path, vocals, sr_vocals)
            
            # Cleanup temporary file
            os.remove(temp_denoised_path)

            self.progress['value'] = 100
            messagebox.showinfo("Success", f"Processing complete!\nEnhanced file saved to:\n{final_output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.process_button.config(state=tk.NORMAL)
            self.progress['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioEnhancerApp(root)
    root.mainloop()


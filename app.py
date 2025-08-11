import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import yaml
from pydub.playback import play
from engine import AudioEngine

class AudioProcessorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Aura Audio Suite v2.0 | by Sanyam Sanjay Sharma")
        self.geometry("700x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- Load Engine & Config ---
        self.engine = AudioEngine()
        self.config = self.engine.config
        self.is_processing = False
        self.sep_model_map = {v['display_name']: k for k, v in self.config['separation_models'].items()}

        # --- Main Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_widgets()

    def _create_widgets(self):
        # --- Top Frame for File Selection ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(top_frame, placeholder_text="Select an audio file to process...")
        self.file_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.browse_button = ctk.CTkButton(top_frame, text="Browse", width=100, command=self.browse_file)
        self.browse_button.grid(row=0, column=1)

        # --- Tabbed View for Main Controls ---
        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.grid(row=1, column=0, padx=20, pady=0, sticky="nsew")
        self.tab_view.add("Processing Chain")
        self.tab_view.add("Batch Processing")
        
        self._create_processing_tab(self.tab_view.tab("Processing Chain"))
        self._create_batch_tab(self.tab_view.tab("Batch Processing"))

        # --- Bottom Frame for Execution and Status ---
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        bottom_frame.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(bottom_frame, text="Status: Idle", anchor="w")
        self.status_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.progress = ctk.CTkProgressBar(bottom_frame, mode='determinate')
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="ew")

        self.preview_button = ctk.CTkButton(bottom_frame, text="Preview Snippet", command=lambda: self.start_processing_thread(preview=True))
        self.preview_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.process_button = ctk.CTkButton(bottom_frame, text="Process Full Audio", command=self.start_processing_thread)
        self.process_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    def _create_processing_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        # --- Separation Module ---
        sep_frame = ctk.CTkFrame(tab, fg_color="transparent")
        sep_frame.pack(fill='x', pady=10)
        self.sep_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sep_frame, text="Enable AI Vocal Separation", variable=self.sep_var).pack(anchor='w')
        self.sep_model_display_var = ctk.StringVar(value=list(self.sep_model_map.keys())[0])
        ctk.CTkOptionMenu(sep_frame, variable=self.sep_model_display_var, values=list(self.sep_model_map.keys())).pack(anchor='w', padx=20, pady=5, fill='x')

        # --- EQ Module ---
        self.eq_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Enable 3-Band Parametric EQ", variable=self.eq_var).pack(anchor='w', pady=(20, 5))
        eq_frame = ctk.CTkFrame(tab, fg_color="transparent")
        eq_frame.pack(fill='x', padx=20)
        eq_frame.grid_columnconfigure(1, weight=1)
        self.eq_low_var = tk.DoubleVar(value=0)
        self.eq_mid_var = tk.DoubleVar(value=0)
        self.eq_high_var = tk.DoubleVar(value=0)
        ctk.CTkLabel(eq_frame, text="Low (dB)").grid(row=0, column=0, padx=5)
        ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_low_var).grid(row=0, column=1, sticky='ew')
        ctk.CTkLabel(eq_frame, text="Mid (dB)").grid(row=1, column=0, padx=5)
        ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_mid_var).grid(row=1, column=1, sticky='ew')
        ctk.CTkLabel(eq_frame, text="High (dB)").grid(row=2, column=0, padx=5)
        ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_high_var).grid(row=2, column=1, sticky='ew')

        # --- Gate and Compression ---
        self.gate_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Enable Noise Gate", variable=self.gate_var).pack(anchor='w', pady=(20, 5))
        self.compress_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Enable Dynamic Compression", variable=self.compress_var).pack(anchor='w', pady=5)

    def _create_batch_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Select a folder to apply the current processing settings to all audio files within it.", wraplength=400).pack(fill='x', pady=10)
        
        batch_frame = ctk.CTkFrame(tab, fg_color="transparent")
        batch_frame.pack(fill='x', pady=10)
        batch_frame.grid_columnconfigure(0, weight=1)
        self.batch_entry = ctk.CTkEntry(batch_frame, placeholder_text="Select a folder for batch processing...")
        self.batch_entry.grid(row=0, column=0, sticky='ew', padx=(0,10))
        ctk.CTkButton(batch_frame, text="Browse Folder", width=120, command=self.browse_folder).grid(row=0, column=1)
        
        ctk.CTkButton(tab, text="Start Batch Process", command=self.start_batch_thread).pack(pady=20, fill='x')

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if path:
            self.file_entry.delete(0, tk.END); self.file_entry.insert(0, path)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.batch_entry.delete(0, tk.END); self.batch_entry.insert(0, path)

    def _get_processing_options(self):
        selected_display_name = self.sep_model_display_var.get()
        model_key = self.sep_model_map[selected_display_name]
        return {
            'use_separation': self.sep_var.get(),
            'separation_model': model_key,
            'use_eq': self.eq_var.get(),
            'eq_low': self.eq_low_var.get(),
            'eq_mid': self.eq_mid_var.get(),
            'eq_high': self.eq_high_var.get(),
            'use_gate': self.gate_var.get(),
            'gate_threshold': self.config['defaults']['gate_threshold_dbfs'],
            'use_compression': self.compress_var.get()
        }

    def start_processing_thread(self, preview=False, file_path=None):
        path = file_path or self.file_entry.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid audio file first."); return
        
        self.process_button.configure(state='disabled')
        self.preview_button.configure(state='disabled')
        
        thread = threading.Thread(target=self.process_audio, args=(path, self._get_processing_options(), preview))
        thread.daemon = True
        thread.start()

    def start_batch_thread(self):
        folder_path = self.batch_entry.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Please select a valid folder."); return
        thread = threading.Thread(target=self.process_batch, args=(folder_path, self._get_processing_options()))
        thread.daemon = True
        thread.start()

    def progress_callback(self, type, *args):
        if type == "status":
            self.status_label.configure(text=f"Status: {args[0]}")
            if len(args) > 1: self.progress.set(args[1]/100)
        elif type == "progress":
            self.progress.set(args[0]/100)

    def process_audio(self, path, options, preview):
        try:
            if preview:
                self.progress_callback("status", "Generating preview...")
                audio = AudioSegment.from_file(path)
                snippet = audio[:self.config['preview_duration_ms']]
                temp_path = os.path.join(os.path.dirname(path), "preview_temp.wav")
                snippet.export(temp_path, format="wav")
                processed_path = self.engine.run_pipeline(temp_path, options, self.progress_callback)
                processed_snippet = AudioSegment.from_file(processed_path)
                self.progress_callback("status", "Playing preview...")
                play(processed_snippet)
                os.remove(temp_path); os.remove(processed_path)
            else:
                final_path = self.engine.run_pipeline(path, options, self.progress_callback)
                messagebox.showinfo("Success", f"Processing complete!\nFile saved to:\n{final_path}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.progress_callback("status", "Idle", 0)
            self.process_button.configure(state='normal')
            self.preview_button.configure(state='normal')

    def process_batch(self, folder_path, options):
        audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp3', '.wav', '.flac'))]
        if not audio_files:
            messagebox.showinfo("Info", "No audio files found in the selected folder."); return

        for i, filename in enumerate(audio_files):
            self.progress_callback("status", f"Batch processing {i+1}/{len(audio_files)}: {filename}", int((i/len(audio_files))*100))
            file_path = os.path.join(folder_path, filename)
            try:
                self.engine.run_pipeline(file_path, options, self.progress_callback)
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
        
        self.progress_callback("status", "Batch process complete!", 100)

if __name__ == "__main__":
    app = AudioProcessorApp()
    app.mainloop()
import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import yaml
from pydub.playback import play
from engine import AudioEngine
import librosa
import numpy as np
import torch

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AudioProcessorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window & System Setup ---
        self.title("Aura Audio Suite v3.0 (Professional) | by Sanyam Sanjay Sharma")
        self.geometry("850x950")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.engine = AudioEngine()
        self.config = self.engine.config
        self.presets_path = 'presets.yaml'
        self.presets = self._load_presets()
        self.is_processing = False
        self.sep_model_map = {v['display_name']: k for k, v in self.config['separation_models'].items()}
        self.is_cuda_available = torch.cuda.is_available()

        # --- Main Layout ---
        # This configures the main window's grid to be resizable
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._create_widgets()

    def _load_presets(self):
        if not os.path.exists(self.presets_path):
            return {}
        with open(self.presets_path, 'r') as f:
            return yaml.safe_load(f) or {}

    def _save_presets(self):
        with open(self.presets_path, 'w') as f:
            yaml.dump(self.presets, f, default_flow_style=False)

    def _create_widgets(self):
        # --- Left Panel: Controls ---
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        left_panel.grid_rowconfigure(1, weight=1)

        # --- MODIFICATION: Make the left panel's content expandable ---
        left_panel.grid_columnconfigure(0, weight=1)


        # --- Right Panel: Waveform & Status ---
        right_panel = ctk.CTkFrame(self, fg_color="transparent")
        right_panel.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=3)
        right_panel.grid_rowconfigure(1, weight=1)

        # --- MODIFICATION: Make the right panel's content expandable ---
        right_panel.grid_columnconfigure(0, weight=1)


        # --- Populate Left Panel ---
        self._create_file_selection(left_panel)
        self._create_processing_tabs(left_panel)
        
        # --- Populate Right Panel ---
        self._create_waveform_display(right_panel)
        self._create_status_display(right_panel)

    def _create_file_selection(self, parent):
        file_frame = ctk.CTkFrame(parent, fg_color="transparent")
        file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        file_frame.grid_columnconfigure(0, weight=1)
        self.file_entry = ctk.CTkEntry(file_frame, placeholder_text="Select an audio file...")
        self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(file_frame, text="Browse", width=80, command=self.browse_file).grid(row=0, column=1)

    def _create_processing_tabs(self, parent):
        tab_view = ctk.CTkTabview(parent, anchor="w")
        tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tab_view.add("Processing")
        tab_view.add("Batch")
        tab_view.add("Settings")
        
        self._create_processing_chain_tab(tab_view.tab("Processing"))
        self._create_batch_tab(tab_view.tab("Batch"))
        self._create_settings_tab(tab_view.tab("Settings"))

    def _create_waveform_display(self, parent):
        waveform_frame = ctk.CTkFrame(parent)
        waveform_frame.grid(row=0, column=0, sticky="nsew")
        
        fig = Figure(figsize=(5, 4), dpi=100, facecolor="#2B2B2B")
        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor("#2B2B2B")
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['top'].set_color('none')
        self.ax.spines['right'].set_color('none')
        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=waveform_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _create_status_display(self, parent):
        status_frame = ctk.CTkFrame(parent)
        status_frame.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=1) # Allow buttons to space out

        self.status_label = ctk.CTkLabel(status_frame, text="Status: Idle", anchor="w")
        self.status_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.progress = ctk.CTkProgressBar(status_frame, mode='determinate')
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="ew")

        self.preview_button = ctk.CTkButton(status_frame, text="Preview Snippet", command=lambda: self.start_processing_thread(preview=True))
        self.preview_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.process_button = ctk.CTkButton(status_frame, text="Process Full Audio", command=self.start_processing_thread)
        self.process_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    def _create_processing_chain_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        
        # Presets
        preset_frame = ctk.CTkFrame(tab, fg_color="transparent")
        preset_frame.pack(fill='x', pady=5)
        preset_frame.grid_columnconfigure(0, weight=1)
        self.preset_var = ctk.StringVar(value="Select Preset...")
        self.preset_menu = ctk.CTkOptionMenu(preset_frame, variable=self.preset_var, values=list(self.presets.keys()), command=self.load_preset)
        self.preset_menu.grid(row=0, column=0, sticky='ew', padx=(0,10))
        ctk.CTkButton(preset_frame, text="Save", width=60, command=self.save_preset).grid(row=0, column=1)

        # Modules
        self.sep_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="AI Vocal Separation", variable=self.sep_var).pack(anchor='w', pady=(15, 5))
        self.sep_model_display_var = ctk.StringVar(value=list(self.sep_model_map.keys())[0])
        ctk.CTkOptionMenu(tab, variable=self.sep_model_display_var, values=list(self.sep_model_map.keys())).pack(anchor='w', padx=20, pady=5, fill='x')

        self.eq_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="3-Band Parametric EQ", variable=self.eq_var).pack(anchor='w', pady=(15, 5))
        eq_frame = ctk.CTkFrame(tab, fg_color="transparent")
        eq_frame.pack(fill='x', padx=20)
        eq_frame.grid_columnconfigure(1, weight=1)
        self.eq_low_var = tk.DoubleVar(value=0)
        self.eq_mid_var = tk.DoubleVar(value=0)
        self.eq_high_var = tk.DoubleVar(value=0)
        ctk.CTkLabel(eq_frame, text="Low").grid(row=0, column=0, padx=5)
        ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_low_var).grid(row=0, column=1, sticky='ew')
        ctk.CTkLabel(eq_frame, text="Mid").grid(row=1, column=0, padx=5)
        ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_mid_var).grid(row=1, column=1, sticky='ew')
        ctk.CTkLabel(eq_frame, text="High").grid(row=2, column=0, padx=5)
        ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_high_var).grid(row=2, column=1, sticky='ew')

        self.gate_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Noise Gate", variable=self.gate_var).pack(anchor='w', pady=(15, 5))
        self.compress_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Dynamic Compression", variable=self.compress_var).pack(anchor='w', pady=5)

    def _create_batch_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Apply current settings from the 'Processing' tab to all audio files in a folder.", wraplength=400).pack(fill='x', pady=10)
        
        batch_frame = ctk.CTkFrame(tab, fg_color="transparent")
        batch_frame.pack(fill='x', pady=10, expand=True)
        batch_frame.grid_columnconfigure(0, weight=1)
        self.batch_entry = ctk.CTkEntry(batch_frame, placeholder_text="Select a folder...")
        self.batch_entry.grid(row=0, column=0, sticky='ew', padx=(0,10))
        ctk.CTkButton(batch_frame, text="Browse", width=100, command=self.browse_folder).grid(row=0, column=1)
        
        ctk.CTkButton(tab, text="Start Batch Process", command=self.start_batch_thread).pack(pady=20, fill='x')

    def _create_settings_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        self.use_cuda_var = ctk.BooleanVar(value=self.is_cuda_available)
        gpu_checkbox = ctk.CTkCheckBox(tab, text="Use GPU (NVIDIA CUDA) for AI Models", variable=self.use_cuda_var)
        gpu_checkbox.pack(anchor='w', pady=10)
        if not self.is_cuda_available:
            gpu_checkbox.configure(state='disabled')

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if path:
            self.file_entry.delete(0, tk.END); self.file_entry.insert(0, path)
            self.draw_waveform(path)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.batch_entry.delete(0, tk.END); self.batch_entry.insert(0, path)

    def draw_waveform(self, path):
        try:
            self.status_label.configure(text="Status: Loading waveform...")
            y, sr = librosa.load(path, sr=None, mono=True)
            self.ax.clear()
            librosa.display.waveshow(y, sr=sr, ax=self.ax, color='#00AFFF')
            self.ax.set_xlabel('')
            self.ax.set_ylabel('')
            self.ax.set_yticks([])
            self.canvas.draw()
            self.status_label.configure(text="Status: Idle")
        except Exception as e:
            self.status_label.configure(text="Status: Error loading waveform")
            print(f"Waveform error: {e}")

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
            'use_compression': self.compress_var.get(),
            'use_cuda': self.use_cuda_var.get()
        }

    def save_preset(self):
        preset_name = ctk.CTkInputDialog(text="Enter preset name:", title="Save Preset").get_input()
        if preset_name:
            self.presets[preset_name] = self._get_processing_options()
            self._save_presets()
            self.preset_menu.configure(values=list(self.presets.keys()))
            self.preset_var.set(preset_name)

    def load_preset(self, preset_name):
        settings = self.presets.get(preset_name)
        if not settings: return
        
        self.sep_var.set(settings.get('use_separation', True))
        model_key = settings.get('separation_model', list(self.sep_model_map.values())[0])
        display_name = [k for k, v in self.sep_model_map.items() if v == model_key][0]
        self.sep_model_display_var.set(display_name)
        
        self.eq_var.set(settings.get('use_eq', True))
        self.eq_low_var.set(settings.get('eq_low', 0))
        self.eq_mid_var.set(settings.get('eq_mid', 0))
        self.eq_high_var.set(settings.get('eq_high', 0))
        
        self.gate_var.set(settings.get('use_gate', True))
        self.compress_var.set(settings.get('use_compression', True))
        self.use_cuda_var.set(settings.get('use_cuda', self.is_cuda_available))

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
            if len(args) > 1: self.progress.set(args[1]/100.0)
        elif type == "progress":
            self.progress.set(args[0]/100.0)

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
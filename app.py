import os
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import yaml
import logging
from typing import Dict, Any, Optional

import customtkinter as ctk
from pydub import AudioSegment
from pydub.playback import play
import librosa
import numpy as np
import torch

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from engine import AudioEngine, UserCancelledError

# --- Centralized Logging Setup ---
def setup_logging():
    logger = logging.getLogger("aura_audio_suite")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        logger.propagate = False
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'), mode='w')
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_formatter = logging.Formatter('%(levelname)s: %(message)s')
        stream_handler.setFormatter(stream_formatter)
    return logger

log = setup_logging()

class AudioProcessorApp(ctk.CTk):
    def __init__(self, engine: AudioEngine):
        super().__init__()
        self.engine = engine
        self.config = self.engine.config
        self.presets_path = 'presets.yaml'
        self.presets = self._load_presets()
        self.is_processing = False
        self.sep_model_map = {v['display_name']: k for k, v in self.config['separation_models'].items()}
        self.is_cuda_available = torch.cuda.is_available()
        self.playback_thread = None
        self.stop_event = threading.Event()

        self.title("Aura Audio Suite v3.4 (Professional) | by Sanyam Sanjay Sharma")
        self.geometry("850x950")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(0, weight=3); self.grid_columnconfigure(1, weight=2); self.grid_rowconfigure(0, weight=1)
        self._create_widgets()
        log.info("Application initialized successfully.")

    def _create_status_display(self, parent: ctk.CTkFrame):
        status_frame = ctk.CTkFrame(parent)
        status_frame.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        status_frame.grid_columnconfigure((0, 1), weight=1)
        self.status_label = ctk.CTkLabel(status_frame, text="Status: Idle", anchor="w", justify="left")
        self.status_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.progress = ctk.CTkProgressBar(status_frame, mode='determinate'); self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.preview_button = ctk.CTkButton(status_frame, text="Preview Snippet", command=lambda: self.start_processing_thread(preview=True))
        self.preview_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.process_button = ctk.CTkButton(status_frame, text="Process Full Audio", command=self.start_processing_thread)
        self.process_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.stop_button = ctk.CTkButton(status_frame, text="Stop Process", command=self.stop_processing, fg_color="#E53935", hover_color="#C62828")

    def stop_processing(self):
        if self.is_processing:
            log.warning("Stop button clicked by user.")
            self.stop_event.set()
            self.stop_button.configure(state="disabled", text="Stopping...")

    def start_processing_thread(self, preview: bool = False, file_path: Optional[str] = None):
        path = file_path or self.file_entry.get()
        if not path or not os.path.exists(path): messagebox.showerror("Error", "Please select a valid audio file first."); return
        if self.is_processing: messagebox.showwarning("Busy", "Another process is already running."); return
        self.stop_event.clear()
        self.is_processing = True
        self.toggle_ui_state(processing=True)
        thread = threading.Thread(target=self.process_audio, args=(path, self._get_processing_options(), preview, self.stop_event), daemon=True)
        thread.start()
        
    def process_audio(self, path: str, options: Dict[str, Any], preview: bool, stop_event: threading.Event):
        temp_path, processed_path = None, None
        try:
            if preview:
                self.progress_callback("status", "Generating preview...", 0); audio = AudioSegment.from_file(path); snippet = audio[:self.config['preview_duration_ms']]
                temp_dir = os.path.join(os.path.dirname(path), self.config.get('temp_directory_name', 'temp_processing')); os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, "preview_temp.wav"); snippet.export(temp_path, format="wav")
                processed_path = self.engine.run_pipeline(temp_path, options, self.progress_callback, stop_event)
                processed_snippet = AudioSegment.from_file(processed_path)
                if not stop_event.is_set():
                    self.progress_callback("status", "Playing preview...", 0)
                    self.playback_thread = threading.Thread(target=play, args=(processed_snippet,), daemon=True)
                    self.playback_thread.start()
            else:
                final_path = self.engine.run_pipeline(path, options, self.progress_callback, stop_event)
                if not stop_event.is_set():
                    self.progress_callback("success", f"Processing complete!\nFile saved to:\n{final_path}")
        except UserCancelledError:
            log.info("Process was cancelled by the user.")
            self.update_status("Status: Process Cancelled", 0)
        except Exception as e:
            log.error(f"Error during audio processing for {path}: {e}", exc_info=True)
            self.progress_callback("error", str(e))
        finally:
            if self.playback_thread: self.playback_thread.join(timeout=self.config['preview_duration_ms'] / 1000.0 + 2)
            if temp_path and os.path.exists(temp_path): os.remove(temp_path)
            if processed_path and os.path.exists(processed_path): os.remove(processed_path)
            self.is_processing = False
            self.toggle_ui_state(processing=False)
            if not self.stop_event.is_set():
                self.update_status("Status: Idle", 0)

    def process_batch(self, folder_path: str, options: Dict[str, Any], stop_event: threading.Event):
        audio_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp3', '.wav', '.flac'))]
        if not audio_files: messagebox.showinfo("Info", "No audio files found."); self.is_processing = False; self.toggle_ui_state(processing=False); return
        total_files = len(audio_files); log.info(f"Starting batch process for {total_files} files in {folder_path}")
        
        try:
            for i, filename in enumerate(audio_files):
                if stop_event.is_set(): raise UserCancelledError()
                progress_percent = int(((i + 1) / total_files) * 100)
                self.update_status(f"Batch: {i+1}/{total_files}: {filename}", progress_percent)
                file_path = os.path.join(folder_path, filename)
                
                # --- CORRECTED LINE ---
                # The stop_event must be passed to the engine pipeline here as well.
                self.engine.run_pipeline(file_path, options, lambda *args: None, stop_event)
                # --- END CORRECTION ---

        except UserCancelledError:
            log.info("Batch process was cancelled by the user.")
            self.update_status("Status: Batch Cancelled", 0)
        except Exception as e:
             log.error(f"Failed to process batch file {filename}: {e}", exc_info=True)
             messagebox.showerror("Batch Error", f"An error occurred on {filename}:\n{e}")
        finally:
            self.is_processing = False
            self.toggle_ui_state(processing=False)
            if not stop_event.is_set():
                self.update_status("Batch process complete!", 100)
            log.info("Batch process finished.")

    def start_batch_thread(self):
        folder_path = self.batch_entry.get()
        if not folder_path or not os.path.isdir(folder_path): messagebox.showerror("Error", "Please select a valid folder."); return
        if self.is_processing: messagebox.showwarning("Busy", "Another process is already running."); return
        self.stop_event.clear()
        self.is_processing = True
        self.toggle_ui_state(processing=True)
        thread = threading.Thread(target=self.process_batch, args=(folder_path, self._get_processing_options(), self.stop_event), daemon=True)
        thread.start()

    def toggle_ui_state(self, processing: bool):
        if processing:
            state = "disabled"; self.preview_button.grid_remove(); self.process_button.grid_remove()
            self.stop_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        else:
            state = "normal"; self.stop_button.grid_remove(); self.preview_button.grid(); self.process_button.grid()
            self.stop_button.configure(state="normal", text="Stop Process")
        self.preset_menu.configure(state=state)
        # The other buttons are now hidden/shown, so no need to disable them
    
    # The rest of the file is unchanged.
    def _load_presets(self):
        if not os.path.exists(self.presets_path): return {}
        try:
            with open(self.presets_path, 'r') as f:
                presets = yaml.safe_load(f) or {}
                log.info(f"Loaded {len(presets)} presets from {self.presets_path}")
                return presets
        except (yaml.YAMLError, IOError) as e:
            log.error(f"Failed to load presets: {e}", exc_info=True); messagebox.showerror("Preset Load Error", f"Failed to load presets.yaml: {e}"); return {}

    def _save_presets(self):
        try:
            with open(self.presets_path, 'w') as f: yaml.dump(self.presets, f, default_flow_style=False, indent=2)
            log.info(f"Saved {len(self.presets)} presets to {self.presets_path}")
        except IOError as e:
            log.error(f"Failed to save presets: {e}", exc_info=True); messagebox.showerror("Preset Save Error", f"Failed to save presets.yaml: {e}")
    
    def _create_widgets(self):
        left_panel = ctk.CTkFrame(self); left_panel.grid(row=0, column=0, padx=20, pady=20, sticky="nsew"); left_panel.grid_rowconfigure(1, weight=1)
        right_panel = ctk.CTkFrame(self, fg_color="transparent"); right_panel.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew"); right_panel.grid_rowconfigure(0, weight=3); right_panel.grid_rowconfigure(1, weight=1)
        self._create_file_selection(left_panel); self._create_processing_tabs(left_panel); self._create_waveform_display(right_panel); self._create_status_display(right_panel)

    def _create_file_selection(self, parent: ctk.CTkFrame):
        file_frame = ctk.CTkFrame(parent, fg_color="transparent"); file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew"); file_frame.grid_columnconfigure(0, weight=1)
        self.file_entry = ctk.CTkEntry(file_frame, placeholder_text="Select an audio file..."); self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(file_frame, text="Browse", width=80, command=self.browse_file).grid(row=0, column=1)

    def _create_processing_tabs(self, parent: ctk.CTkFrame):
        tab_view = ctk.CTkTabview(parent, anchor="w"); tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tab_view.add("Processing"); tab_view.add("Batch"); tab_view.add("Settings")
        self._create_processing_chain_tab(tab_view.tab("Processing")); self._create_batch_tab(tab_view.tab("Batch")); self._create_settings_tab(tab_view.tab("Settings"))

    def _create_waveform_display(self, parent: ctk.CTkFrame):
        waveform_frame = ctk.CTkFrame(parent); waveform_frame.grid(row=0, column=0, sticky="nsew")
        fig = Figure(figsize=(5, 4), dpi=100, facecolor="#2B2B2B"); self.ax = fig.add_subplot(111)
        self.ax.set_facecolor("#2B2B2B"); self.ax.tick_params(axis='x', colors='white'); self.ax.tick_params(axis='y', colors='white')
        self.ax.spines['bottom'].set_color('white'); self.ax.spines['left'].set_color('white'); self.ax.spines['top'].set_color('none'); self.ax.spines['right'].set_color('none')
        fig.tight_layout(); self.canvas = FigureCanvasTkAgg(fig, master=waveform_frame); self.canvas.draw(); self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _create_processing_chain_tab(self, tab: ctk.CTkFrame):
        tab.grid_columnconfigure(0, weight=1)
        self._create_preset_controls(tab); self._create_separation_controls(tab); self._create_eq_controls(tab); self._create_dynamics_controls(tab)

    def _create_preset_controls(self, parent: ctk.CTkFrame):
        preset_frame = ctk.CTkFrame(parent, fg_color="transparent"); preset_frame.pack(fill='x', pady=5, padx=10); preset_frame.grid_columnconfigure(0, weight=1)
        self.preset_var = ctk.StringVar(value="Select Preset..."); self.preset_menu = ctk.CTkOptionMenu(preset_frame, variable=self.preset_var, values=list(self.presets.keys()) or ["No Presets"], command=self.load_preset)
        self.preset_menu.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        ctk.CTkButton(preset_frame, text="Save", width=60, command=self.save_preset).grid(row=0, column=1, padx=(0, 5))
        ctk.CTkButton(preset_frame, text="Delete", width=60, command=self.delete_preset, fg_color="#D2691E", hover_color="#B85B1A").grid(row=0, column=2)

    def _create_separation_controls(self, parent: ctk.CTkFrame):
        self.sep_var = ctk.BooleanVar(value=True); ctk.CTkCheckBox(parent, text="AI Vocal Separation", variable=self.sep_var).pack(anchor='w', pady=(15, 5), padx=10)
        self.sep_model_display_var = ctk.StringVar(value=list(self.sep_model_map.keys())[0]); ctk.CTkOptionMenu(parent, variable=self.sep_model_display_var, values=list(self.sep_model_map.keys())).pack(anchor='w', padx=30, pady=5, fill='x')

    def _create_eq_controls(self, parent: ctk.CTkFrame):
        self.eq_var = ctk.BooleanVar(value=True); ctk.CTkCheckBox(parent, text="3-Band Parametric EQ", variable=self.eq_var).pack(anchor='w', pady=(15, 5), padx=10)
        eq_frame = ctk.CTkFrame(parent, fg_color="transparent"); eq_frame.pack(fill='x', padx=30); eq_frame.grid_columnconfigure(1, weight=1)
        self.eq_low_var, self.eq_mid_var, self.eq_high_var = tk.DoubleVar(value=0), tk.DoubleVar(value=0), tk.DoubleVar(value=0)
        ctk.CTkLabel(eq_frame, text="Low").grid(row=0, column=0, padx=5); ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_low_var).grid(row=0, column=1, sticky='ew')
        ctk.CTkLabel(eq_frame, text="Mid").grid(row=1, column=0, padx=5); ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_mid_var).grid(row=1, column=1, sticky='ew')
        ctk.CTkLabel(eq_frame, text="High").grid(row=2, column=0, padx=5); ctk.CTkSlider(eq_frame, from_=-12, to=12, variable=self.eq_high_var).grid(row=2, column=1, sticky='ew')

    def _create_dynamics_controls(self, parent: ctk.CTkFrame):
        self.gate_var = ctk.BooleanVar(value=True); ctk.CTkCheckBox(parent, text="Noise Gate", variable=self.gate_var).pack(anchor='w', pady=(15, 5), padx=10)
        self.compress_var = ctk.BooleanVar(value=True); ctk.CTkCheckBox(parent, text="Dynamic Compression", variable=self.compress_var).pack(anchor='w', pady=5, padx=10)

    def _create_batch_tab(self, tab: ctk.CTkFrame):
        tab.grid_columnconfigure(0, weight=1); ctk.CTkLabel(tab, text="Apply current settings to all audio files in a folder.", wraplength=400, justify="left").pack(fill='x', pady=10, padx=10)
        batch_frame = ctk.CTkFrame(tab, fg_color="transparent"); batch_frame.pack(fill='x', pady=10, padx=10, expand=True); batch_frame.grid_columnconfigure(0, weight=1)
        self.batch_entry = ctk.CTkEntry(batch_frame, placeholder_text="Select a folder..."); self.batch_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        ctk.CTkButton(batch_frame, text="Browse", width=100, command=self.browse_folder).grid(row=0, column=1); ctk.CTkButton(tab, text="Start Batch Process", command=self.start_batch_thread).pack(pady=20, fill='x', padx=10)

    def _create_settings_tab(self, tab: ctk.CTkFrame):
        tab.grid_columnconfigure(0, weight=1); self.use_cuda_var = ctk.BooleanVar(value=self.is_cuda_available)
        gpu_checkbox = ctk.CTkCheckBox(tab, text="Use GPU (NVIDIA CUDA) for AI Models", variable=self.use_cuda_var); gpu_checkbox.pack(anchor='w', pady=10, padx=10)
        if not self.is_cuda_available: gpu_checkbox.configure(state='disabled'); ctk.CTkLabel(tab, text="NVIDIA GPU not detected. CPU will be used.", font=ctk.CTkFont(size=12)).pack(anchor='w', padx=10)

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select an Audio File", filetypes=[("Audio Files", "*.mp3 *.wav *.flac")]);
        if path: self.file_entry.delete(0, tk.END); self.file_entry.insert(0, path); self.draw_waveform(path)

    def browse_folder(self):
        path = filedialog.askdirectory(title="Select a Folder");
        if path: self.batch_entry.delete(0, tk.END); self.batch_entry.insert(0, path)

    def draw_waveform(self, path: str):
        try:
            self.update_status("Status: Loading waveform...", 0); y, sr = librosa.load(path, sr=None, mono=True); self.ax.clear()
            librosa.display.waveshow(y, sr=sr, ax=self.ax, color='#00AFFF'); self.ax.set_xlabel(''); self.ax.set_ylabel(''); self.ax.set_yticks([])
            self.canvas.draw(); self.update_status("Status: Idle", 0)
        except Exception as e:
            self.update_status(f"Status: Error loading waveform", 0); log.error(f"Could not load waveform for {path}: {e}", exc_info=True); messagebox.showerror("Waveform Error", f"Could not load waveform:\n{e}")

    def _get_processing_options(self) -> Dict[str, Any]:
        return {'use_separation': self.sep_var.get(), 'separation_model': self.sep_model_map[self.sep_model_display_var.get()],'use_eq': self.eq_var.get(), 'eq_low': self.eq_low_var.get(), 'eq_mid': self.eq_mid_var.get(), 'eq_high': self.eq_high_var.get(),'use_gate': self.gate_var.get(), 'gate_threshold': self.config['defaults']['gate_threshold_dbfs'],'use_compression': self.compress_var.get(), 'use_cuda': self.use_cuda_var.get()}

    def save_preset(self):
        dialog = ctk.CTkInputDialog(text="Enter preset name:", title="Save Preset"); preset_name = dialog.get_input()
        if preset_name:
            if preset_name in self.presets and not messagebox.askyesno("Confirm Overwrite", f"Preset '{preset_name}' already exists. Overwrite?"): return
            self.presets[preset_name] = self._get_processing_options(); self._save_presets()
            self.preset_menu.configure(values=list(self.presets.keys())); self.preset_var.set(preset_name)
            self.update_status(f"Status: Preset '{preset_name}' saved."); log.info(f"Saved preset: {preset_name}")

    def load_preset(self, preset_name: str):
        if preset_name in ["No Presets", "Select Preset..."]: return
        settings = self.presets.get(preset_name)
        if not settings: return
        self.sep_var.set(settings.get('use_separation', True)); model_key = settings.get('separation_model', list(self.sep_model_map.values())[0])
        display_name = next((k for k, v in self.sep_model_map.items() if v == model_key), list(self.sep_model_map.keys())[0]); self.sep_model_display_var.set(display_name)
        self.eq_var.set(settings.get('use_eq', True)); self.eq_low_var.set(settings.get('eq_low', 0)); self.eq_mid_var.set(settings.get('eq_mid', 0)); self.eq_high_var.set(settings.get('eq_high', 0))
        self.gate_var.set(settings.get('use_gate', True)); self.compress_var.set(settings.get('use_compression', True)); self.use_cuda_var.set(settings.get('use_cuda', self.is_cuda_available))
        self.update_status(f"Status: Preset '{preset_name}' loaded."); log.info(f"Loaded preset: {preset_name}")

    def delete_preset(self):
        preset_name = self.preset_var.get()
        if not preset_name or preset_name in ["Select Preset...", "No Presets"]: messagebox.showwarning("Warning", "No preset selected to delete."); return
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the preset '{preset_name}'?"):
            if preset_name in self.presets:
                del self.presets[preset_name]; self._save_presets(); self.preset_var.set("Select Preset...")
                self.preset_menu.configure(values=list(self.presets.keys()) or ["No Presets"]); self.update_status(f"Status: Preset '{preset_name}' deleted."); log.info(f"Deleted preset: {preset_name}")
    
    def progress_callback(self, event_type: str, *args: Any):
        if event_type == "status":
            self.update_status(f"Status: {args[0]}", args[1] if len(args) > 1 else None)
        elif event_type == "demucs_output":
            self.update_status(args[0])
        elif event_type == "progress":
            self.progress.set(args[0] / 100.0)
        elif event_type == "error":
            messagebox.showerror("Processing Error", f"An error occurred: {args[0]}")
            self.update_status("Status: Error", 0)
        elif event_type == "success":
            messagebox.showinfo("Success", args[0])
            self.update_status("Status: Complete!", 1)
            
    def update_status(self, text: str, progress: Optional[float] = None):
        self.status_label.configure(text=text)
        if progress is not None:
            self.progress.set(progress / 100.0 if progress > 1 else progress)

    def _on_closing(self):
        if self.is_processing and not messagebox.askyesno("Exit", "A process is still running. Are you sure you want to exit?"): return
        log.info("Application closing."); self.destroy()

if __name__ == "__main__":
    try:
        engine = AudioEngine()
        app = AudioProcessorApp(engine=engine)
        app.mainloop()
    except FileNotFoundError as e:
        log.critical(f"Fatal Error: config.yaml not found. {e}", exc_info=True); messagebox.showerror("Fatal Error", "config.yaml not found.")
    except Exception as e:
        log.critical(f"A fatal error occurred on startup: {e}", exc_info=True); messagebox.showerror("Fatal Error", f"An unexpected error occurred on startup: {e}\n\nCheck logs/app.log for details.")
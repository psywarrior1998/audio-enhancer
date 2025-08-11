import os
import yaml
import logging
import subprocess
import re
import numpy as np
import torch
import threading
import queue # For thread-safe communication

from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
from scipy.signal import iirfilter, sosfilt

log = logging.getLogger("aura_audio_suite")

class UserCancelledError(Exception):
    """Custom exception raised when the user cancels the operation."""
    pass

class AudioEngine:
    """
    Handles all audio processing logic with cancellable operations.
    This version uses a thread-safe queue for cross-platform compatibility.
    """

    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _run_demucs_separation_with_live_output(self, input_path: str, model_key: str, use_cuda: bool, temp_dir: str, progress_callback, stop_event: threading.Event):
        """
        Runs Demucs via subprocess and uses a dedicated thread to read its output,
        ensuring cross-platform compatibility for the stop functionality.
        """
        model_info = self.config['separation_models'][model_key]
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        
        cmd = ["python", "-m", "demucs", "-d", device, "-n", model_info['name'], "--two-stems=vocals", "-o", temp_dir, f'"{input_path}"']
        cmd_str = " ".join(cmd)
        log.info(f"Executing command: {cmd_str}")

        process = subprocess.Popen(cmd_str, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, universal_newlines=True, shell=True, encoding='utf-8')
        
        # --- MODIFICATION: Thread-safe queue for reading output ---
        q = queue.Queue()
        
        def reader_thread(pipe, q):
            try:
                for line in iter(pipe.readline, ''):
                    q.put(line)
            finally:
                pipe.close()

        threading.Thread(target=reader_thread, args=[process.stderr, q], daemon=True).start()
        
        progress_callback("status", "Step 1/5: Separating Vocals...")
        
        while process.poll() is None:
            if stop_event.is_set():
                log.warning("Termination signal received, killing subprocess.")
                process.terminate()
                raise UserCancelledError("Process cancelled by user.")

            try:
                line = q.get(timeout=0.1)
                clean_line = line.strip()
                if clean_line:
                    progress_callback("demucs_output", clean_line)
                    match = re.search(r'(\d+)\s*%', clean_line)
                    if match:
                        percentage = int(match.group(1))
                        scaled_percentage = percentage * 0.8
                        progress_callback("progress", scaled_percentage)
            except queue.Empty:
                continue # No new output, continue loop to check stop_event
        
        if process.returncode != 0 and not stop_event.is_set():
            raise RuntimeError("Demucs separation failed. Check the logs for details.")

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        vocals_path = os.path.join(temp_dir, model_info['name'], base_name, "vocals.wav")
        if not os.path.exists(vocals_path):
            raise FileNotFoundError("Separated vocals file not found after processing.")
            
        return AudioSegment.from_file(vocals_path)

    def run_pipeline(self, input_path, options, progress_callback, stop_event: threading.Event):
        output_dir = os.path.join(os.path.dirname(input_path), self.config['output_directory_name'])
        temp_dir = os.path.join(output_dir, self.config['temp_directory_name'])
        os.makedirs(output_dir, exist_ok=True); os.makedirs(temp_dir, exist_ok=True)
        log.info(f"Starting pipeline for {input_path}")
        current_audio = AudioSegment.from_file(input_path)
        output_suffix = ""

        if options.get('use_separation'):
            if stop_event.is_set(): raise UserCancelledError()
            model_key = options['separation_model']
            use_cuda = options.get('use_cuda', False)
            output_suffix += "_vocals"
            current_audio = self._run_demucs_separation_with_live_output(input_path, model_key, use_cuda, temp_dir, progress_callback, stop_event)
        else:
            progress_callback("progress", 80)
            
        if options.get('use_eq'):
            if stop_event.is_set(): raise UserCancelledError()
            progress_callback("status", "Step 2/5: Applying Equalizer"); progress_callback("progress", 85)
            output_suffix += "_eq"; current_audio = self.apply_eq(current_audio, options['eq_low'], options['eq_mid'], options['eq_high'])

        if options.get('use_gate'):
            if stop_event.is_set(): raise UserCancelledError()
            progress_callback("status", "Step 3/5: Applying Noise Gate"); progress_callback("progress", 90)
            output_suffix += "_gated"; current_audio = self.apply_noise_gate(current_audio, options['gate_threshold'])

        if options.get('use_compression'):
            if stop_event.is_set(): raise UserCancelledError()
            progress_callback("status", "Step 4/5: Applying Compression"); progress_callback("progress", 95)
            output_suffix += "_compressed"; current_audio = self.apply_compression(current_audio)

        if stop_event.is_set(): raise UserCancelledError()
        progress_callback("status", "Step 5/5: Normalizing and Saving"); progress_callback("progress", 99)
        final_audio = effects.normalize(current_audio)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        final_output_path = os.path.join(output_dir, f"{base_name}{output_suffix}.wav")
        final_audio.export(final_output_path, format="wav")
        
        progress_callback("progress", 100)
        log.info(f"Pipeline complete. File saved to {final_output_path}")
        return final_output_path

    # The rest of the file is unchanged.
    def _create_band_pass_filter(self, low_cut, high_cut, sr, order=5):
        nyq = 0.5 * sr
        low = low_cut / nyq
        high = high_cut / nyq
        return iirfilter(order, [low, high], btype='band', analog=False, ftype='butter', output='sos')

    def apply_eq(self, segment, low_gain, mid_gain, high_gain):
        sr = segment.frame_rate
        samples = np.array(segment.get_array_of_samples())
        low_filter = self._create_band_pass_filter(30, 250, sr)
        mid_filter = self._create_band_pass_filter(250, 4000, sr)
        high_filter = self._create_band_pass_filter(4000, 16000, sr)
        low_band = sosfilt(low_filter, samples) * (10**(low_gain/20))
        mid_band = sosfilt(mid_filter, samples) * (10**(mid_gain/20))
        high_band = sosfilt(high_filter, samples) * (10**(high_gain/20))
        combined_samples = (low_band + mid_band + high_band).astype(samples.dtype)
        return segment._spawn(combined_samples)

    def apply_noise_gate(self, segment, threshold_dbfs):
        return sum(split_on_silence(segment, min_silence_len=500, silence_thresh=threshold_dbfs, keep_silence=100)) or AudioSegment.silent(duration=len(segment))

    def apply_compression(self, segment):
        params = self.config['defaults']
        return effects.compress_dynamic_range(segment, threshold=params['compression_threshold_dbfs'], ratio=params['compression_ratio'])
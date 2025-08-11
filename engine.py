import os
import yaml
import logging
import subprocess
import re
import numpy as np # <-- Ensure numpy is imported
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
from scipy.signal import iirfilter, sosfilt

log = logging.getLogger("aura_audio_suite")

class AudioEngine:
    """
    Handles all audio processing logic. Uses subprocess for Demucs to
    capture and display its real-time text output.
    """

    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _run_demucs_separation_with_live_output(self, input_path: str, model_key: str, use_cuda: bool, temp_dir: str, progress_callback):
        """
        Runs Demucs via subprocess to capture its detailed stderr output.
        """
        model_info = self.config['separation_models'][model_key]
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        
        cmd = [
            "python", "-m", "demucs",
            "-d", device,
            "-n", model_info['name'],
            "--two-stems=vocals",
            "-o", temp_dir,
            f'"{input_path}"'
        ]
        cmd_str = " ".join(cmd)
        log.info(f"Executing command: {cmd_str}")

        process = subprocess.Popen(
            cmd_str,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            universal_newlines=True,
            shell=True
        )
        
        for line in iter(process.stderr.readline, ''):
            clean_line = line.strip()
            if clean_line:
                progress_callback("demucs_output", clean_line)
        
        process.wait()
        if process.returncode != 0:
            log.error(f"Demucs process failed with return code {process.returncode}")
            raise RuntimeError("Demucs separation failed. Check the logs for details.")

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        vocals_path = os.path.join(temp_dir, model_info['name'], base_name, "vocals.wav")
        
        if not os.path.exists(vocals_path):
            log.error(f"Separated vocals file not found at expected path: {vocals_path}")
            raise FileNotFoundError("Separated vocals file not found after processing.")
            
        return AudioSegment.from_file(vocals_path)

    def _create_band_pass_filter(self, low_cut, high_cut, sr, order=5):
        nyq = 0.5 * sr; low = low_cut / nyq; high = high_cut / nyq
        return iirfilter(order, [low, high], btype='band', analog=False, ftype='butter', output='sos')

    def apply_eq(self, segment, low_gain, mid_gain, high_gain):
        sr = segment.frame_rate
        samples = segment.get_array_of_samples()
        
        # --- CORRECTED LINE ---
        # Convert the standard Python array from pydub into a NumPy array.
        samples = np.array(samples)
        # --- END CORRECTION ---

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

    def run_pipeline(self, input_path, options, progress_callback):
        output_dir = os.path.join(os.path.dirname(input_path), self.config['output_directory_name'])
        temp_dir = os.path.join(output_dir, self.config['temp_directory_name'])
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        log.info(f"Starting pipeline for {input_path} with options: {options}")
        current_audio = AudioSegment.from_file(input_path)
        output_suffix = ""

        if options.get('use_separation'):
            model_key = options['separation_model']
            use_cuda = options.get('use_cuda', False)
            output_suffix += "_vocals"
            
            if 'demucs' in model_key:
                current_audio = self._run_demucs_separation_with_live_output(input_path, model_key, use_cuda, temp_dir, progress_callback)
            else:
                log.error("Spleeter is not supported in this engine version.")
                raise NotImplementedError("Only Demucs models are supported for status reporting.")
            
        if options.get('use_eq'):
            progress_callback("status", "Applying Equalizer...")
            output_suffix += "_eq"
            current_audio = self.apply_eq(current_audio, options['eq_low'], options['eq_mid'], options['eq_high'])

        if options.get('use_gate'):
            progress_callback("status", "Applying Noise Gate...")
            output_suffix += "_gated"
            current_audio = self.apply_noise_gate(current_audio, options['gate_threshold'])

        if options.get('use_compression'):
            progress_callback("status", "Applying Compression...")
            output_suffix += "_compressed"
            current_audio = self.apply_compression(current_audio)

        progress_callback("status", "Normalizing and saving...")
        final_audio = effects.normalize(current_audio)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        final_output_path = os.path.join(output_dir, f"{base_name}{output_suffix}.wav")
        final_audio.export(final_output_path, format="wav")
        log.info(f"Pipeline complete. File saved to {final_output_path}")
        
        return final_output_path
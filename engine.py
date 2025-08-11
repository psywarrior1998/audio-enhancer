import os
import subprocess
import yaml
import re
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
from scipy.signal import iirfilter, sosfilt

class AudioEngine:
    """Handles all audio processing logic."""

    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _get_model_cmd(self, model_key, use_cuda, input_path, output_dir):
        """Constructs the command for the selected separation model."""
        model_info = self.config['separation_models'][model_key]
        cmd = []
        if 'demucs' in model_key:
            cmd = ["demucs", "-d", "cuda" if use_cuda else "cpu", "-n", model_info['name'], "--two-stems=vocals", "-o", output_dir, input_path]
        elif 'spleeter' in model_key:
            cmd = ["spleeter", "separate", "-p", model_info['name'], "-o", output_dir, input_path]
            if use_cuda:
                cmd.extend(["-d", "cuda"]) # Spleeter also supports a device flag
        return cmd

    # ... (the rest of the engine.py file remains the same) ...
    # (No other changes are needed in engine.py)
    def _create_band_pass_filter(self, low_cut, high_cut, sr, order=5):
        """Creates a band-pass filter using scipy."""
        nyq = 0.5 * sr
        low = low_cut / nyq
        high = high_cut / nyq
        sos = iirfilter(order, [low, high], btype='band', analog=False, ftype='butter', output='sos')
        return sos

    def apply_eq(self, segment, low_gain, mid_gain, high_gain):
        """Applies a 3-band parametric equalizer."""
        sr = segment.frame_rate
        samples = segment.get_array_of_samples()
        
        # Define frequency bands
        low_filter = self._create_band_pass_filter(30, 250, sr)
        mid_filter = self._create_band_pass_filter(250, 4000, sr)
        high_filter = self._create_band_pass_filter(4000, 16000, sr)

        # Apply filters
        low_band = sosfilt(low_filter, samples) * (10**(low_gain/20))
        mid_band = sosfilt(mid_filter, samples) * (10**(mid_gain/20))
        high_band = sosfilt(high_filter, samples) * (10**(high_gain/20))

        # Combine bands
        combined_samples = (low_band + mid_band + high_band).astype(samples.dtype)
        
        return segment._spawn(combined_samples)

    def apply_noise_gate(self, segment, threshold_dbfs):
        """Applies a noise gate."""
        return sum(split_on_silence(segment, min_silence_len=500, silence_thresh=threshold_dbfs, keep_silence=100)) or AudioSegment.silent(duration=len(segment))

    def apply_compression(self, segment):
        """Applies dynamic range compression."""
        params = self.config['defaults']
        return effects.compress_dynamic_range(
            segment,
            threshold=params['compression_threshold_dbfs'],
            ratio=params['compression_ratio']
        )

    def run_pipeline(self, input_path, options, progress_callback):
        """Executes the full audio processing pipeline based on user options."""
        output_dir = os.path.join(os.path.dirname(input_path), self.config['output_directory_name'])
        temp_dir = os.path.join(output_dir, self.config['temp_directory_name'])
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        current_audio = AudioSegment.from_file(input_path)
        output_suffix = ""

        if options.get('use_separation'):
            model_key = options['separation_model']
            use_cuda = options.get('use_cuda', False)
            progress_callback("status", f"Separating vocals with {model_key}...", 0)
            output_suffix += "_vocals"
            
            cmd = self._get_model_cmd(model_key, use_cuda, input_path, temp_dir)
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, universal_newlines=True)
            
            for line in iter(process.stderr.readline, ''):
                match = re.search(r'\|\s*(\d+)%', line)
                if match:
                    percentage = int(match.group(1))
                    progress_callback("progress", percentage)
            process.wait()

            base_name = os.path.splitext(os.path.basename(input_path))[0]
            model_info = self.config['separation_models'][model_key]
            vocals_path = os.path.join(temp_dir, model_info['name'], base_name, "vocals.wav") if 'demucs' in model_key else os.path.join(temp_dir, base_name, "vocals.wav")
            if not os.path.exists(vocals_path): raise FileNotFoundError("Separated vocals file not found.")
            current_audio = AudioSegment.from_file(vocals_path)

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

        progress_callback("status", "Normalizing and saving...", 98)
        final_audio = effects.normalize(current_audio)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        final_output_path = os.path.join(output_dir, f"{base_name}{output_suffix}.wav")
        final_audio.export(final_output_path, format="wav")
        
        return final_output_path
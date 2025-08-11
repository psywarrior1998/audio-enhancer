# engine.py

import os
import yaml
import logging
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
from scipy.signal import iirfilter, sosfilt

# --- Direct API Imports ---
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio

# Get the logger configured in the main app
log = logging.getLogger("aura_audio_suite")

class AudioEngine:
    """Handles all audio processing logic using direct APIs."""

    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _run_demucs_separation(self, input_path: str, model_name: str, use_cuda: bool, progress_callback) -> AudioSegment:
        """
        Runs Demucs separation using its native Python API.
        Returns the separated vocal track as a pydub AudioSegment.
        """
        progress_callback("status", f"Loading Demucs model: {model_name}...")
        try:
            model = get_model(name=model_name)
        except Exception as e:
            log.error(f"Failed to load Demucs model: {e}")
            raise RuntimeError(f"Could not load Demucs model '{model_name}'. Ensure it's a valid pretrained model name.")

        if use_cuda and torch.cuda.is_available():
            model.to('cuda')
            device_str = "CUDA"
        else:
            model.to('cpu')
            device_str = "CPU"
        log.info(f"Running Demucs separation on {device_str}.")
        progress_callback("status", f"Separating vocals on {device_str}...")

        wav = AudioFile(input_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
        wav = wav.to(model.device)
        
        # apply_model returns a tensor of all separated sources
        sources = apply_model(model, wav[None], split=True, overlap=0.25, progress=True)[0]
        
        # Find the 'vocals' source
        if 'vocals' not in model.sources:
             raise RuntimeError(f"The model '{model_name}' does not provide a 'vocals' stem.")
        
        vocals_tensor = sources[model.sources.index('vocals')]
        
        # Convert tensor back to a pydub AudioSegment for the rest of the pipeline
        vocals_np = vocals_tensor.cpu().numpy().T
        if vocals_np.ndim == 1:
            vocals_np = vocals_np[:, None] # Ensure stereo format for AudioSegment

        vocals_segment = AudioSegment(
            data=vocals_np.tobytes(),
            sample_width=vocals_tensor.dtype.itemsize,
            frame_rate=model.samplerate,
            channels=vocals_tensor.shape[0]
        )
        return vocals_segment

    def _create_band_pass_filter(self, low_cut, high_cut, sr, order=5):
        nyq = 0.5 * sr
        low = low_cut / nyq
        high = high_cut / nyq
        sos = iirfilter(order, [low, high], btype='band', analog=False, ftype='butter', output='sos')
        return sos

    def apply_eq(self, segment, low_gain, mid_gain, high_gain):
        sr = segment.frame_rate
        samples = segment.get_array_of_samples()
        
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
        return effects.compress_dynamic_range(
            segment,
            threshold=params['compression_threshold_dbfs'],
            ratio=params['compression_ratio']
        )

    def run_pipeline(self, input_path, options, progress_callback):
        output_dir = os.path.join(os.path.dirname(input_path), self.config['output_directory_name'])
        os.makedirs(output_dir, exist_ok=True)

        log.info(f"Starting pipeline for {input_path} with options: {options}")
        current_audio = AudioSegment.from_file(input_path)
        output_suffix = ""

        if options.get('use_separation'):
            model_key = options['separation_model']
            use_cuda = options.get('use_cuda', False)
            output_suffix += "_vocals"
            
            if 'demucs' in model_key:
                model_info = self.config['separation_models'][model_key]
                current_audio = self._run_demucs_separation(input_path, model_info['name'], use_cuda, progress_callback)
            elif 'spleeter' in model_key:
                log.error("Spleeter API call is not implemented in this version.")
                raise NotImplementedError("Spleeter direct API integration is not supported in this version. Please use a Demucs model.")
            
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
        log.info(f"Pipeline complete. File saved to {final_output_path}")
        
        return final_output_path
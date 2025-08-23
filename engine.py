import os
import yaml
import logging
import subprocess
import re
import numpy as np
import torch
import threading
import concurrent.futures
import math
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence
from scipy.signal import iirfilter, sosfilt

log = logging.getLogger("aura_audio_suite")

class UserCancelledError(Exception):
    """Custom exception raised when the user cancels the operation."""
    pass

class AudioEngine:
    """
    Final engine version with parallel processing for long audio files,
    silence trimming, and lossless compression.
    """

    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def _run_demucs_on_chunk(self, chunk_path: str, options: dict, temp_dir_root: str):
        model_key = options['separation_model']
        use_cuda = options.get('use_cuda', False)
        low_ram = options.get('low_ram_mode', False)
        model_info = self.config['separation_models'][model_key]
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"

        chunk_name = os.path.splitext(os.path.basename(chunk_path))[0]
        chunk_temp_dir = os.path.join(temp_dir_root, chunk_name)
        os.makedirs(chunk_temp_dir, exist_ok=True)

        cmd = ["python", "-u", "-m", "demucs", "-d", device, "-n", model_info['name'], "--two-stems=vocals", "-o", chunk_temp_dir]
        if low_ram:
            cmd.extend(["--shifts", "1"])
        cmd.append(chunk_path)
        
        process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if process.returncode != 0:
            log.error(f"Demucs failed on chunk {chunk_name}: {process.stderr}")
            return None

        vocals_path = os.path.join(chunk_temp_dir, model_info['name'], chunk_name, "vocals.wav")
        if not os.path.exists(vocals_path):
            log.error(f"Vocals file not found for chunk {chunk_name} at {vocals_path}")
            return None
        
        return AudioSegment.from_file(vocals_path)

    def apply_post_processing(self, segment: AudioSegment, options: dict):
        if options.get('trim_silence'):
            segment = self.apply_silence_trimming(segment)
        if options.get('use_eq'):
            segment = self.apply_eq(segment, options['eq_low'], options['eq_mid'], options['eq_high'])
        if options.get('use_gate'):
            segment = self.apply_noise_gate(segment, options['gate_threshold'])
        if options.get('use_compression'):
            segment = self.apply_compression(segment)
        return segment

    def run_pipeline(self, input_path, options, progress_callback, stop_event: threading.Event):
        """Main entry point. Dispatches to parallel or single-core pipeline."""
        audio = AudioSegment.from_file(input_path)
        parallel_threshold_ms = 300 * 1000 # 5 minutes
        
        if options.get('parallel_processing') and len(audio) > parallel_threshold_ms and options.get('use_separation'):
            log.info("Long audio file detected. Starting parallel processing pipeline.")
            return self.run_parallel_pipeline(input_path, audio, options, progress_callback, stop_event)
        else:
            log.info("Starting single-core processing pipeline.")
            return self.run_single_core_pipeline(input_path, audio, options, progress_callback, stop_event)
            
    def run_parallel_pipeline(self, input_path, audio: AudioSegment, options, progress_callback, stop_event: threading.Event):
        """Processes a long audio file by splitting it into chunks and processing them in parallel."""
        output_dir = os.path.join(os.path.dirname(input_path), self.config['output_directory_name'])
        temp_dir = os.path.join(output_dir, self.config['temp_directory_name'])
        os.makedirs(output_dir, exist_ok=True); os.makedirs(temp_dir, exist_ok=True)

        num_workers = min(os.cpu_count(), 8)
        chunk_length_ms = math.ceil(len(audio) / num_workers)
        
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            if stop_event.is_set(): raise UserCancelledError()
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)
        
        processed_chunks = [None] * len(chunks)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_chunk = {executor.submit(self._run_demucs_on_chunk, path, options, temp_dir): i for i, path in enumerate(chunk_paths)}
            
            completed_count = 0
            for future in concurrent.futures.as_completed(future_to_chunk):
                if stop_event.is_set():
                    for f in future_to_chunk: f.cancel()
                    raise UserCancelledError()
                
                chunk_index = future_to_chunk[future]
                try:
                    processed_chunks[chunk_index] = future.result()
                except Exception as exc:
                    log.error(f"Chunk {chunk_index} generated an exception: {exc}")
                    processed_chunks[chunk_index] = None
                
                completed_count += 1
                progress = (completed_count / len(chunks)) * 70
                if progress_callback:
                    progress_callback("status", f"Processing chunk {completed_count}/{len(chunks)}...")
                    progress_callback("progress", progress)

        if any(c is None for c in processed_chunks):
            raise RuntimeError("One or more chunks failed to process. Check the logs for details.")
        
        stitched_audio = sum(processed_chunks, AudioSegment.silent(duration=0))
        
        if progress_callback: progress_callback("status", "Applying Post-Processing..."); progress_callback("progress", 80)
        final_audio = self.apply_post_processing(stitched_audio, options)
        
        if progress_callback: progress_callback("status", "Normalizing and Saving"); progress_callback("progress", 99)
        final_audio = effects.normalize(final_audio)
        
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_format = options.get('output_format', 'wav')
        final_output_path = os.path.join(output_dir, f"{base_name}_parallel_processed.{output_format}")
        final_audio.export(final_output_path, format=output_format)
        if progress_callback: progress_callback("progress", 100)
        
        return final_output_path

    def run_single_core_pipeline(self, input_path, audio: AudioSegment, options, progress_callback, stop_event: threading.Event):
        output_dir = os.path.join(os.path.dirname(input_path), self.config['output_directory_name'])
        temp_dir = os.path.join(output_dir, self.config['temp_directory_name'])
        os.makedirs(output_dir, exist_ok=True); os.makedirs(temp_dir, exist_ok=True)
        
        output_suffix = ""
        current_audio = audio

        if options.get('use_separation'):
            if stop_event.is_set(): raise UserCancelledError()
            model_key = options['separation_model']
            use_cuda = options.get('use_cuda', False)
            low_ram = options.get('low_ram_mode', False)
            output_suffix += "_vocals"
            temp_input_path = os.path.join(temp_dir, "single_core_input.wav")
            current_audio.export(temp_input_path, format="wav")
            current_audio = self._run_demucs_separation_with_live_output(
                temp_input_path, model_key, use_cuda, low_ram, temp_dir, progress_callback, stop_event
            )
        elif progress_callback: progress_callback("progress", 70)
        
        if options.get('trim_silence'):
            if stop_event.is_set(): raise UserCancelledError()
            if progress_callback: progress_callback("status", "Step 2/6: Trimming Silence"); progress_callback("progress", 75)
            output_suffix += "_trimmed"; current_audio = self.apply_silence_trimming(current_audio)

        if options.get('use_eq'):
            if stop_event.is_set(): raise UserCancelledError()
            if progress_callback: progress_callback("status", "Step 3/6: Applying Equalizer"); progress_callback("progress", 80)
            output_suffix += "_eq"; current_audio = self.apply_eq(current_audio, options['eq_low'], options['eq_mid'], options['eq_high'])

        if options.get('use_gate'):
            if stop_event.is_set(): raise UserCancelledError()
            if progress_callback: progress_callback("status", "Step 4/6: Applying Noise Gate"); progress_callback("progress", 85)
            output_suffix += "_gated"; current_audio = self.apply_noise_gate(current_audio, options['gate_threshold'])

        if options.get('use_compression'):
            if stop_event.is_set(): raise UserCancelledError()
            if progress_callback: progress_callback("status", "Step 5/6: Applying Compression"); progress_callback("progress", 90)
            output_suffix += "_compressed"; current_audio = self.apply_compression(current_audio)

        if stop_event.is_set(): raise UserCancelledError()
        if progress_callback: progress_callback("status", "Step 6/6: Normalizing and Saving"); progress_callback("progress", 99)
        final_audio = effects.normalize(current_audio)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_format = options.get('output_format', 'wav')
        final_output_path = os.path.join(output_dir, f"{base_name}{output_suffix}.{output_format}")
        final_audio.export(final_output_path, format=output_format)
        
        if progress_callback: progress_callback("progress", 100)
        log.info(f"Pipeline complete. File saved to {final_output_path}")
        return final_output_path
        
    def _run_demucs_separation_with_live_output(self, input_path, model_key, use_cuda, low_ram, temp_dir, progress_callback, stop_event):
        model_info = self.config['separation_models'][model_key]
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        cmd = ["python", "-u", "-m", "demucs", "-d", device, "-n", model_info['name'], "--two-stems=vocals", "-o", temp_dir]
        if low_ram:
            cmd.extend(["--shifts", "1"])
        cmd.append(input_path)
        log.info(f"Executing command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, universal_newlines=True, encoding='utf-8')
        stderr_output = []
        for line in iter(process.stderr.readline, ''):
            if stop_event.is_set():
                log.warning("Termination signal received."); process.terminate(); raise UserCancelledError("Process cancelled by user.")
            clean_line = line.strip()
            stderr_output.append(clean_line)
            if not clean_line: continue
            if progress_callback:
                progress_callback("status", f"Separating: {clean_line}")
                match = re.search(r'(\d+)\s*%', clean_line)
                if match:
                    percentage = int(match.group(1))
                    scaled_percentage = percentage * 0.7
                    progress_callback("progress", scaled_percentage)
        process.wait()
        if process.returncode != 0 and not stop_event.is_set():
            full_error_log = "\n".join(stderr_output)
            error_message = f"Demucs process failed.\n\n--- Full Log ---\n{full_error_log}"
            log.error(error_message); raise RuntimeError(error_message)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        vocals_path = os.path.join(temp_dir, model_info['name'], base_name, "vocals.wav")
        if not os.path.exists(vocals_path):
            raise FileNotFoundError(f"Separated vocals file not found. Check logs for errors.")
        return AudioSegment.from_file(vocals_path)

    def apply_silence_trimming(self, segment: AudioSegment) -> AudioSegment:
        chunks = split_on_silence(segment, min_silence_len=1000, silence_thresh=segment.dBFS - 16, keep_silence=250)
        return sum(chunks) if chunks else AudioSegment.silent(duration=0)
    def _create_band_pass_filter(self, low_cut, high_cut, sr, order=5):
        nyq = 0.5 * sr; low = low_cut / nyq; high = high_cut / nyq
        return iirfilter(order, [low, high], btype='band', analog=False, ftype='butter', output='sos')
    def apply_eq(self, segment, low_gain, mid_gain, high_gain):
        sr = segment.frame_rate; samples = np.array(segment.get_array_of_samples())
        low_filter = self._create_band_pass_filter(30, 250, sr); mid_filter = self._create_band_pass_filter(250, 4000, sr); high_filter = self._create_band_pass_filter(4000, 16000, sr)
        low_band = sosfilt(low_filter, samples) * (10**(low_gain/20)); mid_band = sosfilt(mid_filter, samples) * (10**(mid_gain/20)); high_band = sosfilt(high_filter, samples) * (10**(high_gain/20))
        combined_samples = (low_band + mid_band + high_band).astype(samples.dtype)
        return segment._spawn(combined_samples)
    def apply_noise_gate(self, segment, threshold_dbfs):
        return sum(split_on_silence(segment, min_silence_len=500, silence_thresh=threshold_dbfs, keep_silence=100)) or AudioSegment.silent(duration=len(segment))
    def apply_compression(self, segment):
        params = self.config['defaults']
        return effects.compress_dynamic_range(segment, threshold=params['compression_threshold_dbfs'], ratio=params['compression_ratio'])
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import soundfile as sf
import librosa
import noisereduce as nr
from spleeter.separator import Separator
from demucs import Demucs
import numpy as np
from pydub import AudioSegment
import soundfile as sf

# Function to load an audio file and convert to waveform
def load_audio(file_path):
    audio, sr = librosa.load(file_path, sr=None)
    return audio, sr

# Function to save audio as a WAV file
def save_audio(output_path, audio, sr):
    sf.write(output_path, audio, sr)

# Function to denoise the audio
def denoise_audio(audio, sr, passes=1):
    for _ in range(passes):
        audio = nr.reduce_noise(y=audio, sr=sr)
    return audio

# Function to process with Demucs (Separates vocals from background)
def demucs_separate(audio_file):
    # Using Demucs for source separation (vocals, drums, etc.)
    separator = Separator('demucs')
    separator.separate_to_file(audio_file, './output_audio')

# Function to process with Spleeter (Separates vocals from background)
def spleeter_separate(audio_file):
    separator = Separator('spleeter:2stems')  # 2-stem model (vocals + accompaniment)
    separator.separate(audio_file)

# Function to normalize audio to a specific dB
def normalize_audio(audio, target_dB=-3):
    peak = np.max(np.abs(audio))
    scaling_factor = 10**((target_dB - 20 * np.log10(peak)) / 20)
    return audio * scaling_factor

# GUI setup
def create_gui():
    root = tk.Tk()
    root.title("Audio Enhancer Tool")

    def browse_file():
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3;*.wav;*.flac")])
        if file_path:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, file_path)

    def process_audio():
        file_path = file_entry.get()
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "Invalid file path")
            return
        
        input_audio, sr = load_audio(file_path)

        # Select options for the processing steps
        passes = int(passes_entry.get())
        output_type = output_type_var.get()
        normalize = normalize_var.get()

        # Denoise audio
        denoised_audio = denoise_audio(input_audio, sr, passes)
        
        # Normalize audio if selected
        if normalize:
            denoised_audio = normalize_audio(denoised_audio)
        
        # Choose between Spleeter and Demucs for separation
        if separation_type_var.get() == 'Demucs':
            demucs_separate(file_path)
            messagebox.showinfo("Processing Complete", "Audio processed with Demucs!")
        elif separation_type_var.get() == 'Spleeter':
            spleeter_separate(file_path)
            messagebox.showinfo("Processing Complete", "Audio processed with Spleeter!")

        # Saving the final enhanced output
        output_file = file_path.replace(".mp3", f"_enhanced.{output_type}")
        save_audio(output_file, denoised_audio, sr)

    # UI elements for the user interface
    file_label = tk.Label(root, text="Select Input Audio File:")
    file_label.pack()

    file_entry = tk.Entry(root, width=50)
    file_entry.pack()

    browse_button = tk.Button(root, text="Browse", command=browse_file)
    browse_button.pack()

    passes_label = tk.Label(root, text="Enter Number of Denoise Passes:")
    passes_label.pack()

    passes_entry = tk.Entry(root)
    passes_entry.insert(0, "1")  # Default pass is 1
    passes_entry.pack()

    normalize_var = tk.BooleanVar()
    normalize_check = tk.Checkbutton(root, text="Normalize to -3 dB", variable=normalize_var)
    normalize_check.pack()

    separation_type_var = tk.StringVar(value='Demucs')
    separation_label = tk.Label(root, text="Select Separation Model:")
    separation_label.pack()

    separation_radio1 = tk.Radiobutton(root, text="Demucs", variable=separation_type_var, value='Demucs')
    separation_radio1.pack()

    separation_radio2 = tk.Radiobutton(root, text="Spleeter", variable=separation_type_var, value='Spleeter')
    separation_radio2.pack()

    output_type_var = tk.StringVar(value="wav")
    output_type_label = tk.Label(root, text="Choose Output File Format:")
    output_type_label.pack()

    output_type_menu = tk.OptionMenu(root, output_type_var, "mp3", "wav", "flac")
    output_type_menu.pack()

    process_button = tk.Button(root, text="Process Audio", command=process_audio)
    process_button.pack()

    root.mainloop()

if __name__ == "__main__":
    create_gui()

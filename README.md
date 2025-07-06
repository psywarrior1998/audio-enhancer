# **Audio Enhancer Tool**

This tool enhances the quality of audio files by separating vocals from the background music, reducing noise, and improving vocal clarity. It supports popular models like Demucs, and you can fine-tune parameters for the best results.

## Features

* **Voice Separation**: Separate vocals and background music.
* **Noise Reduction**: Automatically reduce background noise in audio files.
* **Vocal Enhancement**: Improve the quality and clarity of the vocals.
* **Multiple Audio Formats Supported**: Process `.mp3`, `.wav`, and `.flac` files.
* **Batch Processing**: Process multiple files in a folder at once.
* **Offline Demucs Model**: Optional offline usage with pre-downloaded models.
* **Normalization**: Normalize the audio to a specific dB level.

## Getting Started

Follow these instructions to get the project up and running on your machine.

### Prerequisites

* **Python 3.7 or higher**
* **pip** for managing Python packages.
* **FFmpeg** (required for handling certain audio formats like `.mp3`).

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/audio-enhancer-tool.git
cd audio-enhancer-tool
```

### 2. Set Up the Virtual Environment

Create a virtual environment to isolate dependencies:

```bash
python -m venv venv_audio_tool
```

Activate the virtual environment:

* **Windows**:

  ```bash
  venv_audio_tool\Scripts\activate
  ```

* **Mac/Linux**:

  ```bash
  source venv_audio_tool/bin/activate
  ```

### 3. Install Dependencies

Run the following command to install the required Python libraries:

```bash
pip install -r requirements.txt
```

### 4. Setup FFmpeg (Optional)

To work with `.mp3` or `.flac` files, you may need FFmpeg installed on your system.

* **Windows**: Download FFmpeg from the [official website](https://ffmpeg.org/download.html). Add it to your system’s PATH.
* **Mac/Linux**: You can install FFmpeg using `brew` (Mac) or `apt` (Linux).

Example for macOS:

```bash
brew install ffmpeg
```

### 5. Running the Tool

Once everything is set up, run the tool by using the Python script:

```bash
python audio_enhancer.py
```

You’ll be prompted to input details such as the audio file type, the number of passes for enhancement, and which files you’d like to process.

### 6. Batch Mode (Optional)

If you want to process all files in a folder, move your files to the `input_audio/` folder, and the script will process all files in that folder.

### 7. Output

The processed audio files will be saved in the `output_audio/` folder.

---

## Folder Structure

```
audio-enhancer-tool/
├── audio_enhancer.py          # Main Python script with GUI and processing logic
├── launch_audio_enhancer.bat  # Windows batch script to setup environment & launch
├── requirements.txt           # Python dependencies
├── README.md                  # Project overview and instructions
├── .gitignore                 # Files/folders to ignore in Git
├── models/                    # Folder for pre-downloaded Demucs models (if applicable)
├── input_audio/               # Folder for input audio files
├── output_audio/              # Folder for processed output audio files
├── docs/                      # Folder for documentation (optional)
```

* **`models/`**: Optional folder for storing pre-downloaded Demucs models.
* **`input_audio/`**: Store the audio files you want to enhance here.
* **`output_audio/`**: Processed audio files will be saved here.
* **`docs/`**: Documentation for the project (optional).

---

## Usage

* **Input Audio**: Place your audio files (MP3, WAV, FLAC) in the `input_audio/` folder.
* **Process Audio**: Run the Python script to enhance your audio.
* **Output Audio**: Enhanced audio files will be placed in the `output_audio/` folder.

---

## Optional: Pre-Download Demucs Models

If you'd like to use the tool offline, you can download the necessary Demucs models and place them in the `models/` folder.

To specify the model path in the script, ensure the `models/` folder is set up correctly and the path is properly referenced in the code.

---

## Troubleshooting

If you encounter any issues, here are a few things to check:

* Ensure **FFmpeg** is installed correctly on your system, especially if you're processing `.mp3` or `.flac` files.
* Make sure all required Python dependencies are installed by running `pip install -r requirements.txt`.
* If the tool doesn't detect your input files, ensure they are in the `input_audio/` folder and that the filenames are correct.

---

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

---

## Contributing

We welcome contributions to improve the tool! To contribute, follow these steps:

1. Fork this repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Open a Pull Request.

---

### Acknowledgments

* Thanks to the creators of Demucs and other open-source tools that made this project possible!

---

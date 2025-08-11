# Audio Enhancer Tool

This tool enhances the quality of audio files by reducing noise and separating vocals from background music. It provides a simple graphical user interface to process audio files using powerful libraries like Demucs and Spleeter.

## Features

* **Noise Reduction**: Automatically reduce background noise in audio files.
* **Source Separation**: Separate vocals from accompaniment using either Demucs or Spleeter.
* **Audio Normalization**: Normalize audio to a standard -3 dB level.
* **Multiple Audio Formats**: Process `.mp3`, `.wav`, and `.flac` files.
* **User-Friendly GUI**: Easy-to-use interface for selecting files and processing options.

## Prerequisites

* **Python 3.7 or higher**
* **pip** for managing Python packages.
* **FFmpeg**: Required by many audio processing libraries for handling various audio formats.

---

## Installation

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/audio-enhancer-tool.git](https://github.com/your-username/audio-enhancer-tool.git)
cd audio-enhancer-tool
````

### 2\. Set Up a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

  * **Windows**:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
  * **macOS/Linux**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

### 3\. Install Dependencies

Install the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4\. Install FFmpeg

FFmpeg is essential for processing audio files like MP3s.

  * **Windows**: Download FFmpeg from the [official website](https://ffmpeg.org/download.html) and add the `bin` directory to your system's PATH.
  * **macOS (using Homebrew)**:
    ```bash
    brew install ffmpeg
    ```
  * **Linux (using apt)**:
    ```bash
    sudo apt-get update
    sudo apt-get install ffmpeg
    ```

-----

## How to Run the Tool

With the environment activated and dependencies installed, launch the application by running the `audio_enhancer.py` script:

```bash
python audio_enhancer.py
```

The application window will open, allowing you to:

1.  **Browse** for an audio file.
2.  Set the number of **noise reduction passes**.
3.  Choose whether to **normalize** the audio.
4.  Select a **source separation model** (Demucs or Spleeter).
5.  Select the desired **output file format**.
6.  Click **"Process Audio"** to begin.

The enhanced audio file will be saved in the same directory as the input file with `_enhanced` appended to its name.

-----

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

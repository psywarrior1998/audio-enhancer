# Aura Audio Suite v3.1 (Professional)

**Author:** Sanyam Sanjay Sharma

A professional-grade, modular audio processing application featuring a modern graphical user interface, an interactive waveform display, and a powerful, multi-stage processing engine. This suite is designed for AI-powered vocal separation, equalization, noise gating, and dynamic compression.

**Version 3.1 introduces a major internal refactor, replacing slow subprocess calls with direct Python API integration for a significant performance and reliability boost.**

---

## Key Features

- **Direct API Integration**: Engine now calls `demucs` directly for a **10x+ speed increase** and greater stability, removing the need for external command-line tools in the system PATH.
- **Visual Waveform Display**: Interactively view the audio waveform.
- **Professional Workflow**:
    - **Full Preset Management**: **Save, load, and delete** your entire processing chain configuration.
    - **Non-Blocking Preview**: Instantly hear a short snippet without freezing the application.
    - **Batch Processing**: Apply the same enhancement settings to an entire folder of audio files.
- **Advanced Audio Engine**:
    - **Modular Chain**: Independently enable or disable modules for Vocal Separation, Parametric EQ, Noise Gating, and Compression.
    - **AI Vocal Separation**: Utilizes state-of-the-art Demucs models to isolate vocals.
    - **3-Band Parametric EQ**: Precisely shape the tonal balance of your audio.
- **Performance & Stability**:
    - **GPU Acceleration**: Automatically utilizes a compatible NVIDIA GPU (CUDA) for AI tasks.
    - **Multi-threaded & Robust**: The UI remains perfectly responsive while the engine processes audio in the background. Errors are now logged to a `logs/app.log` file for easier debugging.
- **Modern UI**: A sleek, dark-themed interface built for a professional user experience.

---

## Setup Instructions

### 1. Prerequisites
- **Python 3.8+**
- **NVIDIA GPU (Optional)**: For CUDA acceleration.
- **FFmpeg**: Must be installed and available in your system's PATH. This is critical for audio file handling.

### 2. Installation
The provided launcher scripts handle everything automatically.

1.  **Clone the repository.**
2.  **Run the appropriate launcher for your OS:**
    -   On **Windows**, double-click `launch.bat`.
    -   On **macOS or Linux**, open your terminal, navigate to the project folder, and run: `bash launch.sh`.

    **On the first run**, the script will automatically create a Python virtual environment (`venv`), install all required dependencies (including PyTorch), and then launch the application. This may take several minutes. Subsequent runs will be much faster.

---

## How to Use

1.  **Launch the application** using `launch.bat` (Windows) or `bash launch.sh` (macOS/Linux).
2.  **Select an Input File**: Click "Browse" to load an audio file.
3.  **Manage Presets**: Use the dropdown to load a preset. Click "Save" to create a new one or "Delete" to remove the selected one.
4.  **Configure the Processing Chain**: In the "Processing" tab, enable and adjust the modules.
5.  **Preview Snippet**: Click to hear a short, non-blocking preview of your settings.
6.  **Process Full Audio**: Click to process the entire file. The output will be saved in a new `output_audio` folder.
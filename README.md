# Aura Audio Suite v3.0 (Professional)

**Author:** Sanyam Sanjay Sharma

A professional-grade, modular audio processing application featuring a modern graphical user interface, an interactive waveform display, and a powerful, multi-stage processing engine. This suite is designed for AI-powered vocal separation, equalization, noise gating, and dynamic compression.



---

## Key Features

- **Visual Waveform Display**: Interactively view the audio waveform and see the impact of your processing in real-time.
- **Professional Workflow**:
    - **Preset System**: Save and load your entire processing chain configuration to a preset for instant recall.
    - **Real-Time Preview**: Instantly hear how your settings sound on a short snippet without processing the entire file.
    - **Batch Processing**: Apply the same enhancement settings to an entire folder of audio files automatically.
- **Advanced Audio Engine**:
    - **Modular Chain**: Independently enable or disable modules for Vocal Separation, Parametric EQ, Noise Gating, and Compression.
    - **AI Vocal Separation**: Utilizes state-of-the-art Demucs models to isolate vocals from an instrumental track.
    - **3-Band Parametric EQ**: Precisely shape the tonal balance of your audio with adjustable Low, Mid, and High frequency bands.
- **Performance**:
    - **GPU Acceleration**: Automatically detects and utilizes a compatible NVIDIA GPU (CUDA) for a 10x+ speed increase on AI tasks.
    - **Multi-threaded**: The UI remains perfectly responsive while the engine processes audio in the background.
- **Modern UI**: A sleek, dark-themed interface built with a modern framework for a professional user experience.
- **Highly Configurable**: Core parameters and model settings are managed in an external `config.yaml` for easy customization.

---

## Project Structure

The application is architected with a clean separation of concerns:

```

aura-audio-suite/
├── app.py             \# Main application file (GUI logic)
├── engine.py          \# Core audio processing engine
├── config.yaml        \# Main configuration for engine parameters
├── presets.yaml       \# Stores user-saved presets
├── requirements.txt   \# All Python dependencies
└── launch.bat         \# Windows launcher script

````

---

## Setup Instructions

### 1. Prerequisites
- **Python 3.8+**
- **NVIDIA GPU (Optional)**: For CUDA acceleration.
- **FFmpeg**: Must be installed and available in your system's PATH. This is critical for audio file handling.

### 2. Installation
The provided launcher script handles everything automatically.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/psywarrior1998/aura-audio-suite
    cd aura-audio-suite
    ```

2.  **Run the launcher:**
    - On Windows, simply double-click `launch.bat`.
    - **On the first run**, it will automatically create a Python virtual environment (`venv`), install all required dependencies (including PyTorch for GPU support), and then launch the application. This may take several minutes.
    - Subsequent runs will be much faster as they will use the existing environment.

---

## How to Use

1.  **Launch the application** using `launch.bat`.
2.  **Select an Input File**: Click "Browse" to load an audio file. The waveform will appear in the right-hand panel.
3.  **Load a Preset (Optional)**: Use the "Select Preset..." dropdown to instantly apply saved settings.
4.  **Configure the Processing Chain**: In the "Processing" tab, enable the modules you need and adjust their parameters (EQ sliders, AI model, etc.).
5.  **Preview Snippet**: Click this button to hear a short preview of your current settings.
6.  **Process Full Audio**: When satisfied, click this button to process the entire file. The output will be saved in a new `output_audio` folder.
7.  **Save a Preset**: If you've created a configuration you like, click "Save" next to the preset menu to name and save it for future use.
8.  **Batch Processing**: To process multiple files, go to the "Batch" tab, select a folder, and start the process. It will use the currently active settings from the "Processing" tab.
9.  **Settings**: In the "Settings" tab, you can enable or disable GPU acceleration if an NVIDIA GPU is detected.
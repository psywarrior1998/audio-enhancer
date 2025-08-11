# Aura Audio Suite v3.5 (Professional)

**Author:** Sanyam Sanjay Sharma

A professional-grade, modular audio processing application featuring a modern, dynamic GUI, an interactive waveform display, and a powerful, multi-stage processing engine. This suite is designed for AI-powered vocal separation, equalization, noise gating, and dynamic compression.

**Version 3.5 introduces a cancellable processing pipeline with a continuous, user-friendly progress bar and a fully resizable user interface.**

---

## Key Features

-   **Cancellable Operations**: A "Stop Process" button allows the user to safely and instantly terminate audio processing at any stage.
-   **Dynamic & Responsive UI**: The application window is now fully resizable, with all components intelligently scaling to fit any screen size.
-   **Accurate, User-Friendly Progress Bar**: A single, continuous progress bar from 0-100% tracks the entire pipeline, with real-time updates during the main AI separation task and clear markers for the fast post-processing steps.
-   **Visual Waveform Display**: Interactively view the audio waveform and see the impact of your processing in real-time.
-   **Professional Workflow**:
    -   **Full Preset Management**: Save, load, and delete your entire processing chain configuration.
    -   **Non-Blocking Preview**: Instantly hear a short snippet without freezing the application.
    -   **Batch Processing**: Apply the same enhancement settings to an entire folder of audio files automatically.
-   **Advanced Audio Engine**:
    -   **Modular Chain**: Independently enable or disable modules for Vocal Separation, Parametric EQ, Noise Gating, and Compression.
    -   **AI Vocal Separation**: Utilizes state-of-the-art Demucs models to isolate vocals from an instrumental track.
-   **Performance & Stability**:
    -   **Cross-Platform Engine**: The core processing engine is architected to be fully compatible with Windows, macOS, and Linux.
    -   **GPU Acceleration**: Automatically detects and utilizes a compatible NVIDIA GPU (CUDA) for a 10x+ speed increase on AI tasks.
    -   **Robust Error Logging**: Errors are logged to a `logs/app.log` file for easier debugging.

---

## Project Structure

```

aura-audio-suite/
├── app.py             # Main application file (GUI logic)
├── engine.py          # Core audio processing engine
├── config.yaml        # Main configuration for engine parameters
├── presets.yaml       # Stores user-saved presets
├── requirements.txt   # All Python dependencies
└── launch.bat         # Windows launcher script
└── launch.sh          # macOS / Linux launcher script

```

---

## Setup Instructions

### 1. Prerequisites

-   **Python 3.8+**
-   **NVIDIA GPU (Optional)**: For CUDA acceleration.
-   **FFmpeg**: Must be installed and available in your system's PATH. This is critical for audio file handling.

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
2.  **Select an Input File**: Click "Browse" to load an audio file. The waveform will appear.
3.  **Manage Presets**: Use the dropdown to load a preset. Click "Save" to create a new one or "Delete" to remove the selected one.
4.  **Configure the Processing Chain**: In the "Processing" tab, enable and adjust the modules.
5.  **Preview or Process**: Click "Preview Snippet" for a short preview or "Process Full Audio" to run the full pipeline.
6.  **Stop (Optional)**: If a process is running, a "Stop Process" button will appear. Click it to cancel the current operation immediately.


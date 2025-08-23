# Aura Audio Suite v4.1 (Parallel Engine)

**Author:** Sanyam Sanjay Sharma

A professional-grade, modular audio processing application featuring a dynamic GUI, an interactive waveform display, and a powerful, multi-stage processing engine with intelligent parallel processing for maximum efficiency on long audio files.

**Version 4.1 introduces a fully resizable user interface and an intelligent parallel processing core that dramatically speeds up the processing of long audio files on multi-core systems.**

---

## Key Features

-   **Intelligent Parallel Processing**: Automatically detects long audio files (over 5 minutes), splits them into chunks based on your CPU core count, processes them simultaneously, and seamlessly stitches them back together for a massive performance increase.
-   **Dynamic & Responsive UI**: The application window is now fully resizable, with all components intelligently scaling to fit any screen size without misalignment.
-   **Cancellable Operations**: A "Stop Process" button allows the user to safely and instantly terminate audio processing at any stage.
-   **Accurate, User-Friendly Progress Bar**: A single, continuous progress bar from 0-100% tracks the entire pipeline, with real-time updates during the main AI separation task and clear markers for the fast post-processing steps.
-   **Advanced Audio Engine**:
    -   **Trim Long Silences**: A new, selectable module in the processing chain to automatically remove dead air and long pauses from your audio.
    -   **Lossless Compression**: Choose to export your final audio in the high-quality, lossless FLAC format in addition to standard WAV.
    -   **AI Vocal Separation**: Utilizes state-of-the-art Demucs models to isolate vocals from an instrumental track.
-   **Professional Workflow**:
    -   **Full Preset Management**: Save, load, and delete your entire processing chain configuration.
    -   **Non-Blocking Preview**: Instantly hear a short snippet without freezing the application.
    -   **Batch Processing**: Apply the same enhancement settings to an entire folder of audio files automatically.
-   **Performance & Stability**:
    -   **Low RAM Mode**: An optional setting to significantly reduce memory usage for AI models, ensuring stability on systems with less than 8GB of RAM.
    -   **Cross-Platform Engine**: The core processing engine is architected to be fully compatible with Windows, macOS, and Linux.
    -   **GPU Acceleration**: Automatically detects and utilizes a compatible NVIDIA GPU (CUDA) for a 10x+ speed increase on AI tasks.
    -   **Robust Error Logging**: Errors are logged with detailed context to a `logs/app.log` file for easier debugging.

---

## Project Structure

```

aura-audio-suite/
├── app.py             \# Main application file (GUI logic)
├── engine.py          \# Core audio processing engine (with parallel logic)
├── config.yaml        \# Main configuration for engine parameters
├── presets.yaml       \# Stores user-saved presets
├── requirements.txt   \# All Python dependencies
└── launch.bat         \# Windows launcher script
└── launch.sh          \# macOS / Linux launcher script

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
4.  **Configure the Processing Chain**: In the "Processing" tab, enable and adjust the modules, including the new "Trim Long Silences" and "Output Format" options.
5.  **Configure Settings**: In the "Settings" tab, enable "Parallel Processing" for the best performance on long files, or "Low RAM Mode" for memory-constrained systems.
6.  **Preview or Process**: Click "Preview Snippet" for a short preview or "Process Full Audio" to run the full pipeline. The engine will automatically choose between single-core or parallel processing based on your settings and the audio length.
7.  **Stop (Optional)**: If a process is running, a "Stop Process" button will appear. Click it to cancel the current operation immediately.


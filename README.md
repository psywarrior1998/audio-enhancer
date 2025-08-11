# Aura Audio Suite v1.1

A professional-grade, modular audio processing application for AI-powered vocal separation, equalization, noise gating, and dynamic compression.

## Author

- **Sanyam Sanjay Sharma**

## Features

- **Modular Processing Chain**: Independently enable or disable modules for Vocal Separation, Parametric EQ, Noise Gating, and Compression.
- **AI Vocal Separation**: Utilizes state-of-the-art Demucs or Spleeter models to isolate vocals from an instrumental track.
- **3-Band Parametric EQ**: Precisely shape the tonal balance of your audio with adjustable Low, Mid, and High frequency bands.
- **Real-Time Preview**: Instantly hear how your settings sound on a 5-second snippet without processing the entire file.
- **Batch Processing**: Apply the same enhancement settings to an entire folder of audio files automatically.
- **Configurable Engine**: All core parameters and model settings are managed in an external `config.yaml` for easy customization.
- **Professional UI**: A clean, tabbed interface that is responsive and provides real-time progress for long operations.

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- FFmpeg (must be installed and available in your system's PATH)

### 2. Installation
Clone the repository and run the launcher script:

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd aura-audio-suite 
    ```

2.  **Run the launcher:**
    - On Windows, simply double-click `launch.bat`.
    - On the first run, it will automatically create a Python virtual environment (`venv`), install all required dependencies, and then launch the application.
    - Subsequent runs will be much faster as they will use the existing environment.

## How to Use

1.  **Launch the application** using `launch.bat`.
2.  **Select an Input File** using the "Browse..." button.
3.  **Configure the Processing Chain** in the main tab by enabling the desired modules and adjusting their parameters.
4.  **Preview Snippet**: Click this button to hear a short preview of your settings.
5.  **Process Full Audio**: When you are satisfied with the preview, click this button to process the entire file. The output will be saved in the `output_audio` folder.
6.  **Batch Processing**: To process multiple files, go to the "Batch Processing" tab, select a folder, and click "Start Batch Process".
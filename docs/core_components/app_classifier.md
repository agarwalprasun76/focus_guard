# App Classifier Demo

This demo showcases the App Classifier system, which intelligently manages application access based on your calendar events and predefined rules.

## Features

- **Context-Aware Classification**: Automatically detects your current context from calendar events
- **Semantic Understanding**: Uses sentence transformers to understand event meanings
- **Real-time Testing**: Test how different applications would be classified
- **Interactive Interface**: User-friendly Streamlit interface

## Prerequisites

- Python 3.8+
- Required Python packages (install using `pip install -r requirements.txt`)

## Installation

1. Clone the repository (if you haven't already):
   ```bash
   git clone <repository-url>
   cd focus_guard
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Demo

1. Navigate to the demo directory:
   ```bash
   cd demos/app_classifier
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run demo.py
   ```

3. The demo will open in your default web browser at `http://localhost:8501`

## How to Use

1. **Current Context Panel (Left Sidebar)**
   - Shows the current calendar event (simulated)
   - Displays the detected context (e.g., "math_homework", "meeting")
   - Shows when the next context change will occur

2. **Application Testing**
   - The main area shows how different applications would be classified
   - Each application card shows:
     - Application name and window title
     - Classification status (Allowed/Blocked/Flagged)
     - Detailed classification information (expand to view)

3. **Test Custom Applications**
   - Use the form at the bottom to test any application
   - Enter the process name (e.g., "chrome.exe") and optional window title

## Sample Calendar Events

The demo includes these simulated events (all times are relative to current time):

1. **Math Homework - Calculus** (Now ± 1 hour)
2. **Team Standup** (In 2 hours)
3. **Lunch Break** (Now ± 30 minutes)
4. **Research Paper Writing** (In 4 hours)

## Understanding the Results

- ✅ **Allowed**: Application is permitted in the current context
- ⚠️ **Flagged**: Allowed but might be distracting
- ❌ **Blocked**: Not allowed in the current context

## Customization

You can modify:

- `SAMPLE_EVENTS` in `demo.py` to change the simulated calendar events
- `SAMPLE_APPS` to test different applications
- Context rules in `core/app_classifier/context_rules.py`
- App categories in `core/app_classifier/app_categories.py`

## Troubleshooting

- If you get dependency errors, ensure all packages are installed:
  ```bash
  pip install -r ../../requirements.txt
  ```

- For GPU acceleration with PyTorch, you might want to install a CUDA-enabled version:
  ```bash
  pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

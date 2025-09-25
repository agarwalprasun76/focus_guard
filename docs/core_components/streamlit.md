# Focus Guard Streamlit Demo

## Overview

The Focus Guard App Classifier Demo is an interactive web application built with Streamlit that demonstrates how the Focus Guard system classifies applications based on calendar context. It showcases the intelligent decision-making process that determines whether applications are appropriate for different types of activities and calendar events.

## What the Demo Shows

The demo illustrates several key features of the Focus Guard system:

1. **Context-Aware Application Classification**: The system detects the current calendar context (e.g., "Math Homework", "Team Standup", "Lunch Break") and applies different rules for each context.

2. **Real-time Application Evaluation**: For each application, the demo shows whether it would be:
   - ✅ **Allowed**: Appropriate for the current context
   - ⚠️ **Warning**: Potentially distracting but allowed
   - ❌ **Blocked**: Inappropriate for the current context

3. **Custom Application Testing**: Users can input custom application names and window titles to see how they would be classified in the current context.

4. **Context Override**: For demonstration purposes, users can manually override the current context to see how classification changes across different scenarios.

5. **Rule Visualization**: The sidebar displays the number of allowed, flagged, and blocked applications for the current context.

## Design Choices

### Architecture

- **Mock Calendar Integration**: The demo uses a `MockCalendarClient` that simulates Google Calendar API responses, allowing the demo to run without actual calendar credentials.

- **Context Detection**: The system analyzes calendar event titles and descriptions to determine the appropriate context (e.g., "study", "meeting", "break").

- **Rule-Based Classification**: The `ContextRules` class provides context-specific rules that determine which applications are allowed, flagged, or blocked.

### UI/UX

- **Clean, Modern Interface**: The demo uses Streamlit's components with custom CSS to create an intuitive and visually appealing interface.

- **Interactive Elements**: Users can test custom applications, override contexts, and explore classification details through expandable sections.

- **Visual Indicators**: Emojis (✅, ⚠️, ❌) and progress bars provide immediate visual feedback on application status.

- **Responsive Layout**: The interface adapts to different screen sizes using Streamlit's column layout system.

## Technical Implementation

### Streamlit and Torch Compatibility

The demo uses Sentence Transformers (based on PyTorch) for natural language processing, which can cause compatibility issues with Streamlit's file watcher. We implemented several workarounds:

1. **Custom Configuration**: A `.streamlit/config.toml` file disables file watching and excludes torch directories from being monitored.

2. **Custom Runner Script**: The `run_streamlit_app.py` script sets environment variables and launches Streamlit with optimized settings to prevent runtime errors.

3. **Code-Level Workarounds**: The demo includes workarounds for asyncio event loop and torch custom class errors.

### Core Components

- **App Classifier**: Determines if an application is appropriate for the current context based on process name and window title.

- **Context Detector**: Analyzes calendar events to determine the primary context (e.g., study, meeting, leisure).

- **Context Rules**: Defines which applications are allowed, flagged, or blocked for each context type.

## How to Run the Demo

To run the demo without encountering torch/streamlit compatibility errors:

```bash
# Use the custom runner script
python run_streamlit_app.py demos/app_classifier/demo.py
```

This script:
1. Sets environment variables to disable file watching
2. Launches Streamlit with the proper configuration
3. Handles keyboard interrupts gracefully

## Sample Applications

The demo includes several sample applications to demonstrate classification:

- **Chrome with various sites**: Calculator, Overleaf, YouTube, Stack Overflow
- **Code editor**: Working on Python files
- **Teams**: Video conferencing
- **Spotify**: Music streaming
- **Excel**: Spreadsheet work

## Future Enhancements

Potential improvements for the demo include:

1. **Machine Learning Integration**: Enhance context detection with more sophisticated ML models
2. **User Feedback Loop**: Allow users to provide feedback on classification decisions
3. **Historical Analytics**: Show patterns of application usage across different contexts
4. **Personalized Rules**: Demonstrate how rules could adapt to individual user preferences

## Troubleshooting

If you encounter issues with the demo:

1. **Streamlit/Torch Errors**: Use the provided `run_streamlit_app.py` script instead of running Streamlit directly
2. **Missing Dependencies**: Ensure all requirements are installed with `pip install -r requirements.txt`
3. **Port Conflicts**: If port 8501 is in use, specify an alternative port with `--server.port=8502`

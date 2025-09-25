# Calendar Integration Module

## Overview

The Calendar Integration module enables Focus Guard to access and interpret calendar events from Google Calendar. This allows the application to automatically adjust settings based on the user's schedule, providing context-aware functionality.

## Features

- **Google Calendar Integration**: Connect to Google Calendar API to fetch events
- **Service Account Authentication**: Secure access without requiring OAuth verification
- **Context Detection**: Automatically determine user context based on calendar events
- **Timezone Handling**: Proper handling of timezone-aware datetime objects
- **Multiple Authentication Methods**: Support for both OAuth and Service Account authentication

## Components

1. **calendar_integration.py**: Handles authentication and API communication with calendar providers
2. **calendar_context.py**: Interprets calendar events to determine user context
3. **test_calendar.py**: Demo script to test calendar connectivity and event retrieval

## What We Did

1. **Implemented Service Account Authentication**:
   - Added support for Google Cloud service account authentication
   - Created fallback mechanism to use OAuth if service account fails
   - Fixed timezone handling to ensure consistent datetime comparisons

2. **Enhanced Event Retrieval**:
   - Improved direct calendar access using specific calendar IDs
   - Fixed datetime formatting for API requests
   - Added better error handling for API requests

3. **Context Detection**:
   - Implemented algorithms to determine user context based on event keywords
   - Added functionality to predict next context change

## Setup Instructions for Users

### Prerequisites

1. A Google account with Calendar access
2. A Google Cloud project with Calendar API enabled

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API for your project

### Step 2: Set Up Authentication

#### Option A: Service Account (Recommended)

1. In Google Cloud Console, navigate to "IAM & Admin" > "Service Accounts"
2. Create a new service account
3. Download the JSON key file
4. Place the key file in the `config` directory as `service-account.json`
5. Share your Google Calendar with the service account email address:
   - Open Google Calendar
   - Find your calendar in the left sidebar
   - Click the three dots next to your calendar name
   - Select "Settings and sharing"
   - Under "Share with specific people," add the service account email
   - Grant "Make changes to events" permission

#### Option B: OAuth (Alternative)

1. In Google Cloud Console, navigate to "APIs & Services" > "Credentials"
2. Create OAuth client ID credentials (Desktop application)
3. Download the JSON file
4. Place the file in the `config` directory as `credentials.json`
5. First run will prompt for authorization

### Step 3: Configure the Application

1. When initializing `GoogleCalendarClient`, specify your calendar ID:
   ```python
   client = GoogleCalendarClient(calendar_id='your.email@gmail.com')
   ```

2. For testing, use the provided script:
   ```
   python demos/test_calendar.py --calendar-id your.email@gmail.com
   ```

## Future Improvements

1. **Streamlined Setup**:
   - Create a setup wizard to guide users through authentication
   - Implement automatic calendar detection
   - Add UI for calendar selection

2. **Enhanced Calendar Integration**:
   - Support for multiple calendars
   - Calendar event creation and modification
   - Support for other calendar providers (Microsoft Outlook, Apple Calendar)

3. **Improved Context Detection**:
   - Machine learning for better context classification
   - User-defined context rules
   - Learning from user behavior

4. **Performance Optimizations**:
   - Caching of calendar events
   - Batch processing of API requests
   - Background synchronization

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Ensure the service account JSON file is correctly placed
   - Verify the calendar has been shared with the service account
   - Check that the Calendar API is enabled in Google Cloud Console

2. **No Events Found**:
   - Verify the correct calendar ID is being used
   - Ensure the service account has permission to view the calendar
   - Check that the calendar contains events in the queried time range

3. **Timezone Issues**:
   - The application uses UTC for all datetime operations
   - Ensure your calendar events have proper timezone information

### Getting Help

For additional assistance, please refer to:
- [Google Calendar API Documentation](https://developers.google.com/calendar/api/guides/overview)
- [Google Cloud Authentication Documentation](https://cloud.google.com/docs/authentication)

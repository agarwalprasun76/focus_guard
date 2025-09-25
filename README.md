# Focus Guard

Focus Guard is a powerful productivity tool that helps you stay focused by monitoring and managing your digital activities. This repository contains the core functionality of Focus Guard, including activity monitoring, distraction blocking, and usage analytics.

## Features

- **Activity Monitoring**: Track application usage, active windows, and user activity
- **Idle Detection**: Detect when you're away from your computer
- **Distraction Blocking**: Block distracting websites and applications
- **Usage Analytics**: Get insights into your digital habits
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/focus-guard.git
   cd focus-guard
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python -m focus_guard.cli.main
   ```

## Core Components

### Activity Monitoring

Track and analyze your computer usage patterns:
- Monitor active applications and windows
- Detect idle time and user presence
- Generate detailed usage statistics

[Learn more about Activity Monitoring](./docs/core_components/activity/README.md)

### Distraction Blocking

Block distracting websites and applications during focus sessions:
- Create custom blocklists
- Schedule blocking sessions
- Temporary overrides when needed

### Usage Analytics

Gain insights into your digital habits:
- Daily and weekly usage reports
- Application usage breakdowns
- Productivity trends over time

## Documentation

- [API Reference](./docs/api/)
- [Developer Guide](./docs/DEVELOPER.md)
- [Testing Guide](./docs/TESTING.md)

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](./CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Acknowledgments

- Thanks to all contributors who have helped improve Focus Guard
- Built with ❤️ by the Focus Guard team

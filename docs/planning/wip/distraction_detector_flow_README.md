# Distraction Detector Flow Diagram

```mermaid
flowchart TD
    A[Activity Monitor: New activity event] --> B{Is app allowed?}
    B -- Yes --> C[Track time spent in app]
    B -- No --> D[Track time spent in app]
    D --> E{Threshold exceeded?}
    E -- No --> F[Continue monitoring]
    E -- Yes --> G[Trigger alert]
    G --> H[Log distraction event]
    H --> I[Update distraction summary]
    C --> F
    F --> J{User marks app as allowed/distraction?}
    J -- Yes --> K[Update user overrides]
    K --> F
    J -- No --> F
    H --> L[Report to reporting system]
    L --> M[Provide distraction summary]
```

---

**Legend:**
- Activity events are received from the activity monitor.
- Allowed/disallowed status is determined by config, user overrides, and fuzzy matching.
- Time spent is tracked for each app/process.
- Alerts are triggered if distraction thresholds are exceeded.
- User can mark apps as allowed or distractions, updating future behavior.
- All events can be logged and reported.

# FocusGuard – High Level Process Flow Diagram

```mermaid
flowchart TD
    A[Start App] --> B[Load Task Profiles]
    B --> C1[Initialize Calendar Integration]
    C1 --> C2[Initialize Domain Classifier]
    C2 --> C[User Selects Task]
    
    C --> CA[Fetch Calendar Events]
    CA --> CB[Determine Calendar Context]
    CB --> CC[Update Domain Allowances]
    CC --> D[Begin Monitoring Loop]
    
    D --> E[Get Active Window/App]
    E --> F[Cross Platform Detection]
    F --> G[Return App Title and URL]
    
    G --> G1[Extract Domain from URL]
    G1 --> G2[Classify Domain]
    G2 --> G3[Classify App]
    
    G3 --> H[Distraction Check]
    H --> H1{Check Calendar Context}
    H1 -- Relevant --> I[Continue Monitoring]
    H1 -- Irrelevant --> H2{Check Domain Allowance}
    
    H2 -- Allowed --> I
    H2 -- Blocked --> J[Trigger Alert]
    
    J --> K[Log Event]
    I --> L{Session End?}
    K --> L
    
    L -- No --> CA
    L -- Yes --> M[Save Session Log]
    M --> N[Session Review/Report]
    N --> O[End]
```

**Legend:**
- **Rectangles**: Modules or major steps
- **Diamonds**: Decision points
- **Arrows**: Data/control flow

## Key Components

### Calendar Integration
- **Initialize Calendar Integration**: Sets up connection to calendar services (Google Calendar)
- **Fetch Calendar Events**: Retrieves upcoming and current calendar events
- **Determine Calendar Context**: Identifies context (meeting, focus, break) from events
- **Update Domain Allowances**: Sets domain allowance rules based on calendar context

### Activity Monitoring
- **Get Active Window/App**: Detects currently active application
- **Extract Domain from URL**: Parses domains from browser URLs
- **Classify Domain**: Categorizes domains (work, social, entertainment, etc.)
- **Classify App**: Categorizes applications by purpose

### Distraction Detection
- **Check Calendar Context**: Determines if activity is relevant to current calendar context
- **Check Domain Allowance**: Verifies if domain is allowed in current context
- **Trigger Alert**: Notifies user of distraction based on context and domain rules

## Module Reference

- **calendar_integration.py**: Google Calendar API client
- **calendar_context.py**: Calendar event parsing and context detection
- **calendar_domain_allowance.py**: Context-based domain filtering
- **domain_classifier**: Domain categorization and filtering
- **activity_monitor**: Cross-platform window/app detection
- **distraction_detector**: Combines all signals to detect distractions

---

This diagram provides a north star for understanding the overall architecture and flow of FocusGuard, including the calendar-based domain allowance system.

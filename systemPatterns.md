# System Patterns

## Architecture
- **Memory Bank**: A set of Markdown files in the project root used to store context.
  - `projectContext.md`: High-level goals and description.
  - `activeContext.md`: Current focus and active tasks.
  - `systemPatterns.md`: Architecture and design patterns.
  - `techContext.md`: Technology stack and constraints.
  - `progress.md`: Status and milestones.
- **Agent Constitution**: A file (`.agent_constitution.md`) defining the agent's behavior.

## Design Patterns
- **Context Persistence**: The agent reads the Memory Bank at the start of a session and updates it at the end or during significant state changes.
- **Constitution Adherence**: The agent checks the Constitution to ensure compliance with user preferences (e.g., language).

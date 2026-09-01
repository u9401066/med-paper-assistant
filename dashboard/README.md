# MedPaper Dashboard

A lightweight project management dashboard for Medical Paper Assistant, designed for VS Code's Simple Browser.

## Features

### 📁 Project Management

- View and switch between research projects
- Display project status and metadata
- Quick access to project directories

### 🎯 Focus Mode

- Set current writing focus (Introduction, Methods, Results, Discussion)
- Track progress across sections
- Context switching for AI assistance

### 🎨 Diagrams Integration

- List project diagrams
- Preview diagram thumbnails
- Integration with Draw.io MCP

## Quick Start

Source development uses Node.js 24 or newer, matching the repository CI baseline.

```bash
# Install dependencies
npm ci

# Start development server (port 3002)
npm run dev -- -p 3002
```

Then open in VS Code's Simple Browser: `http://localhost:3002`

## Architecture

```
dashboard/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main dashboard page
│   │   └── api/              # API routes (proxy to MCP)
│   ├── components/
│   │   ├── ProjectSelector.tsx   # Project dropdown
│   │   ├── ProjectCard.tsx       # Project info display
│   │   ├── FocusSelector.tsx     # Focus mode selector
│   │   ├── DiagramsPanel.tsx     # Diagrams list
│   │   ├── DrawioEditor.tsx      # Draw.io embed
│   │   └── EnvironmentBadge.tsx  # Environment indicator
│   ├── hooks/
│   │   ├── useProjects.ts    # Project state management
│   │   └── useEnvironment.ts # Environment detection
│   └── types/
│       └── project.ts        # TypeScript interfaces
└── package.json
```

## Integration with MedPaper MCP

The dashboard communicates with the MCP server via HTTP API:

| Endpoint                | Method   | Description           |
| ----------------------- | -------- | --------------------- |
| `/api/projects`         | GET      | List all projects     |
| `/api/projects/current` | GET      | Get current project   |
| `/api/projects/switch`  | POST     | Switch active project |
| `/api/focus`            | GET/POST | Get/set writing focus |
| `/api/diagrams`         | GET      | List project diagrams |

## Environment Detection

The dashboard automatically detects its runtime environment:

- **VS Code Browser**: Optimized for embedded use
- **External Browser**: Full standalone mode

## Tech Stack

- **Next.js 16** - React framework
- **React 19** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS 4** - Styling
- **react-drawio** - Draw.io integration

## Development

```bash
# Run with hot reload
npm run dev -- -p 3002

# Build for production
npm run build

# Run production build
npm start -- -p 3002

# Lint code
npm run lint
```

## Related

- [Medical Paper Assistant](../README.md) - Main project
- [Draw.io MCP Integration](../integrations/README.md) - Diagram tools

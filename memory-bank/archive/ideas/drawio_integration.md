# Draw.io Integration Idea - 2025-11-28

## Source Project

- **Repository**: https://github.com/u9401066/next-ai-draw-io
- **Original**: Forked from DayuanJiang/next-ai-draw-io
- **Tech Stack**: Next.js + Python MCP Server + Draw.io

## Available MCP Tools in next-ai-draw-io

| Tool                   | Description                           |
| ---------------------- | ------------------------------------- |
| `create_diagram`       | Create a new diagram from description |
| `edit_diagram`         | Edit an existing diagram              |
| `read_diagram`         | Read and describe diagram contents    |
| `list_templates`       | List available diagram templates      |
| `create_from_template` | Create diagram from template          |
| `export_diagram`       | Export diagram to SVG/PNG/PDF         |

## Integration Use Cases for med-paper-assistant

### 1. Concept → Diagram (文字轉圖)

After user creates `concept.md`, generate visual diagrams:

- **Study Flow Diagram**: Patient enrollment → Intervention → Outcomes
- **CONSORT Flowchart**: Screening → Randomization → Follow-up → Analysis
- **Methodology Flowchart**: Data collection → Processing → Analysis steps
- **Research Framework**: Conceptual model showing variables and relationships

### 2. Diagram → Text (圖轉文字)

User uploads/draws a diagram, AI interprets it:

- Extract study design from flowchart
- Identify key variables from conceptual diagram
- Generate Methods section draft from process diagram
- Create figure legends from diagrams

### 3. Interactive Refinement

- User sketches rough idea → AI enhances to professional diagram
- AI suggests diagram types based on paper type (RCT → CONSORT, Review → PRISMA)
- Bidirectional: Edit text ↔ Update diagram

## Technical Integration Options

### Option A: Separate MCP Servers (Recommended)

```
VS Code + Copilot
    ├── mdpaper MCP Server (Python) - Paper writing tools
    └── drawio MCP Server (Python) - Diagram tools
```

- Pros: Clean separation, independent development
- Cons: User needs to run both servers

### Option B: Unified MCP Server

Merge drawio tools into med-paper-assistant:

- Add new tool category: **Diagram Tools**
- `create_study_diagram` - Generate study flow from concept
- `create_consort_flowchart` - CONSORT diagram for RCTs
- `create_prisma_flowchart` - PRISMA diagram for reviews
- `diagram_to_text` - Extract text from uploaded diagram

### Option C: Cross-MCP Communication

mdpaper calls drawio MCP via HTTP API:

- mdpaper generates diagram prompt
- Sends to drawio MCP
- Returns diagram XML/image

## Suggested New Tools for med-paper-assistant

```python
# diagram_tools.py

@mcp.tool()
def generate_study_flow(concept_file: str) -> str:
    """Generate study flow diagram from concept.md"""
    # Parse concept → Extract study design
    # Call drawio API or generate XML

@mcp.tool()
def generate_consort_diagram(enrollment: int, randomized: int, ...) -> str:
    """Generate CONSORT flowchart for RCT"""

@mcp.tool()
def generate_prisma_diagram(identified: int, screened: int, ...) -> str:
    """Generate PRISMA flowchart for systematic review"""

@mcp.tool()
def interpret_diagram(image_path: str) -> str:
    """Read diagram image and describe its content as study design"""
```

## Next Steps

1. [ ] Set up next-ai-draw-io locally
2. [ ] Test MCP tools integration
3. [ ] Design unified workflow
4. [ ] Create diagram templates for medical papers:
   - CONSORT (RCT)
   - PRISMA (Systematic Review)
   - STROBE (Observational)
   - STARD (Diagnostic)
5. [ ] Implement bidirectional conversion

## Priority

**High** - Visual diagrams are essential for medical papers:

- Figure 1 is often a study flow diagram
- Required by many journals (CONSORT, PRISMA mandatory)
- Helps readers understand complex study designs

## References

- CONSORT Statement: http://www.consort-statement.org/
- PRISMA Statement: http://www.prisma-statement.org/
- STROBE Statement: https://www.strobe-statement.org/

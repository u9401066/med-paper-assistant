# Prompts Directory

This directory contains MCP Prompts that map to Capabilities.

## Structure

Each prompt is a Markdown file that defines a workflow.

## Available Prompts

| Prompt                   | Slash Command                      | Description                     |
| ------------------------ | ---------------------------------- | ------------------------------- |
| `write-paper.md`         | `/mcp.mdpaper.write-paper`         | Complete paper writing workflow |
| `literature-survey.md`   | `/mcp.mdpaper.literature-survey`   | Systematic literature survey    |
| `manuscript-revision.md` | `/mcp.mdpaper.manuscript-revision` | Respond to reviewer comments    |

## How Prompts Work

1. User invokes a slash command in Agent Mode
2. VS Code sends the prompt content to the LLM
3. The LLM follows the workflow defined in the prompt
4. MCP tools are invoked as needed

## Adding New Prompts

1. Create a new Markdown file in this directory
2. Define the workflow with phases and steps
3. Reference appropriate Skills and Tools
4. Register in the Python MCP server

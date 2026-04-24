# Prompts Directory

This directory contains MCP Prompts that map to Capabilities.

## Structure

Each prompt is a Markdown file that defines a workflow.

## Available Prompts

Prompt workflows use the modern `/mdpaper.<name>` slash namespace.

| Prompt                                  | Slash Command                  | Description                        |
| --------------------------------------- | ------------------------------ | ---------------------------------- |
| `mdpaper.write-paper.prompt.md`         | `/mdpaper.write-paper`         | Complete paper writing workflow    |
| `mdpaper.literature-survey.prompt.md`   | `/mdpaper.literature-survey`   | Systematic literature survey       |
| `mdpaper.manuscript-revision.prompt.md` | `/mdpaper.manuscript-revision` | Respond to reviewer comments       |
| `mdpaper.search.prompt.md`              | `/mdpaper.search`              | Literature search and exploration  |
| `mdpaper.project.prompt.md`             | `/mdpaper.project`             | Project setup and switching        |
| `mdpaper.concept.prompt.md`             | `/mdpaper.concept`             | Concept development and validation |
| `mdpaper.draft.prompt.md`               | `/mdpaper.draft`               | Draft writing workflow             |
| `mdpaper.analysis.prompt.md`            | `/mdpaper.analysis`            | Data analysis and figures          |
| `mdpaper.clarify.prompt.md`             | `/mdpaper.clarify`             | Clarification and revision passes  |
| `mdpaper.format.prompt.md`              | `/mdpaper.format`              | Export and formatting              |
| `mdpaper.strategy.prompt.md`            | `/mdpaper.strategy`            | Search strategy setup              |
| `mdpaper.audit.prompt.md`               | `/mdpaper.audit`               | Independent audit and review loop  |
| `mdpaper.help.prompt.md`                | `/mdpaper.help`                | Prompt and workflow reference      |

## `@mdpaper` Chat Commands

These prompt workflows are distinct from the `@mdpaper` chat participant commands.
The chat participant exposes interactive commands such as `@mdpaper /search`,
`@mdpaper /draft`, `@mdpaper /concept`, `@mdpaper /project`, `@mdpaper /format`,
`@mdpaper /autopaper`, `@mdpaper /drawio`, `@mdpaper /analysis`, `@mdpaper /strategy`,
and `@mdpaper /help`.

## How Prompts Work

1. User invokes a slash command in Agent Mode
2. VS Code sends the prompt content to the LLM
3. The LLM follows the workflow defined in the prompt
4. MCP tools are invoked as needed

## Adding New Prompts

1. Create a new Markdown file in this directory
2. Define the workflow with phases and steps
3. Reference appropriate Skills and Tools
4. Add the prompt name to `bundle-manifest.json` and keep package/README docs in sync

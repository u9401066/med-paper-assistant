/**
 * Extension Helpers — Pure functions extracted from extension.ts for testability.
 *
 * These functions contain the core decision logic but have NO dependency
 * on the `vscode` API, making them easy to unit test.
 */

import * as path from 'path';
import * as fs from 'fs';

type BundledSupportFile = {
    destination: string;
    workspaceDestination: string;
};

/**
 * Determine if the workspace has a user-defined mdpaper MCP server
 * in .vscode/mcp.json, meaning we should skip auto-registration.
 *
 * @param mcpJsonContent - Raw content of .vscode/mcp.json file
 * @returns true if mdpaper is already configured and should be skipped
 */
export function shouldSkipMcpRegistration(mcpJsonContent: string): boolean {
    return mcpJsonContent.includes('"mdpaper"') && mcpJsonContent.includes('med_paper_assistant');
}

/**
 * Determine if the workspace is a development workspace
 * (has source code for med_paper_assistant).
 *
 * @param wsRoot - Workspace root directory path
 * @returns true if this is a dev workspace with source code
 */
export function isDevWorkspace(wsRoot: string): boolean {
    return fs.existsSync(path.join(wsRoot, 'src', 'med_paper_assistant'));
}

/**
 * Check if a pyproject.toml file belongs to the med-paper-assistant project.
 *
 * @param pyprojectPath - Path to pyproject.toml
 * @returns true if this is the med-paper-assistant project's pyproject.toml
 */
export function isMedPaperProject(pyprojectPath: string): boolean {
    try {
        if (!fs.existsSync(pyprojectPath)) {
            return false;
        }
        const content = fs.readFileSync(pyprojectPath, 'utf-8');
        return content.includes('med-paper-assistant');
    } catch {
        return false;
    }
}

/**
 * Determine the Python path to use based on available resources.
 * This is the pure decision logic extracted from getPythonPath().
 *
 * Priority:
 * 1. User configuration (if valid)
 * 2. 'uv' if workspace is the med-paper-assistant project
 * 3. Virtual environment in workspace
 * 4. Bundled Python
 * 5. Fallback to 'uv'
 *
 * @param options - All inputs needed for the decision
 * @returns The Python path string to use
 */
export function determinePythonPath(options: {
    configuredPath?: string;
    wsRoot?: string;
    extensionPath: string;
}): string {
    const { configuredPath, wsRoot, extensionPath } = options;

    // 1. User configuration
    if (configuredPath) {
        if (configuredPath === 'uv' || configuredPath === 'uvx') {
            return configuredPath;
        }
        if (fs.existsSync(configuredPath)) {
            return configuredPath;
        }
    }

    // 2. Check pyproject.toml for med-paper-assistant project
    if (wsRoot) {
        const pyprojectPath = path.join(wsRoot, 'pyproject.toml');
        if (isMedPaperProject(pyprojectPath)) {
            return 'uv';
        }
    }

    // 3. Virtual environment in workspace
    if (wsRoot) {
        const venvCandidates = [
            path.join(wsRoot, '.venv', 'bin', 'python'),
            path.join(wsRoot, '.venv', 'bin', 'python3'),
            path.join(wsRoot, '.venv', 'Scripts', 'python.exe'),
            path.join(wsRoot, 'venv', 'bin', 'python'),
            path.join(wsRoot, 'venv', 'Scripts', 'python.exe'),
        ];
        for (const venvPath of venvCandidates) {
            if (fs.existsSync(venvPath)) {
                return venvPath;
            }
        }
    }

    // 4. Bundled Python
    const bundledPython = path.join(extensionPath, 'bundled', 'python', 'bin', 'python3');
    if (fs.existsSync(bundledPython)) {
        return bundledPython;
    }

    // 5. Fallback
    return 'uv';
}

/**
 * Count missing bundled items (skills, agents, prompts) in a workspace.
 *
 * @param wsRoot - Workspace root directory
 * @param extPath - Extension installation path
 * @param bundledSkills - Array of skill names
 * @param bundledAgents - Array of agent names
 * @param bundledPrompts - Array of prompt names
 * @param bundledSupportFiles - Array of support file metadata
 * @returns Object with counts and details
 */
export function countMissingBundledItems(
    wsRoot: string,
    extPath: string,
    bundledSkills: readonly string[],
    bundledAgents: readonly string[],
    bundledPrompts: readonly string[],
    bundledSupportFiles: readonly BundledSupportFile[],
): {
    missingSkills: number;
    missingAgents: number;
    missingPrompts: number;
    missingSupportFiles: number;
    total: number;
} {
    const skillsDir = path.join(wsRoot, '.claude', 'skills');
    const agentsDir = path.join(wsRoot, '.github', 'agents');
    const promptsDir = path.join(wsRoot, '.github', 'prompts');

    let missingSkills = 0;
    for (const skill of bundledSkills) {
        const src = path.join(extPath, 'skills', skill, 'SKILL.md');
        const dst = path.join(skillsDir, skill, 'SKILL.md');
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            missingSkills++;
        }
    }

    let missingAgents = 0;
    for (const agent of bundledAgents) {
        const src = path.join(extPath, 'agents', `${agent}.agent.md`);
        const dst = path.join(agentsDir, `${agent}.agent.md`);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            missingAgents++;
        }
    }

    let missingPrompts = 0;
    for (const prompt of bundledPrompts) {
        const src = path.join(extPath, 'prompts', `${prompt}.prompt.md`);
        const dst = path.join(promptsDir, `${prompt}.prompt.md`);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            missingPrompts++;
        }
    }

    let missingSupportFiles = 0;
    for (const file of bundledSupportFiles) {
        const src = path.join(extPath, file.destination);
        const dst = path.join(wsRoot, file.workspaceDestination);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            missingSupportFiles++;
        }
    }

    return {
        missingSkills,
        missingAgents,
        missingPrompts,
        missingSupportFiles,
        total: missingSkills + missingAgents + missingPrompts + missingSupportFiles,
    };
}

/**
 * Build the PYTHONPATH for development mode.
 * Combines workspace src, CGU integration, and bundled tool paths.
 *
 * @param wsRoot - Workspace root directory
 * @param bundledToolPath - Path to bundled tool directory
 * @returns Concatenated PYTHONPATH string
 */
export function buildDevPythonPath(wsRoot: string, bundledToolPath: string): string {
    let pythonPath = bundledToolPath;

    const srcPath = path.join(wsRoot, 'src');
    if (fs.existsSync(srcPath)) {
        pythonPath = `${srcPath}${path.delimiter}${pythonPath}`;
    }

    const cguSrc = path.join(wsRoot, 'integrations', 'cgu', 'src');
    if (fs.existsSync(cguSrc)) {
        pythonPath = `${cguSrc}${path.delimiter}${pythonPath}`;
    }

    return pythonPath;
}

/**
 * Extension Helpers — Pure functions extracted from extension.ts for testability.
 *
 * These functions contain the core decision logic but have NO dependency
 * on the `vscode` API, making them easy to unit test.
 */

import * as path from 'path';
import * as fs from 'fs';

const EXTERNAL_MCP_EXTENSION_TARGETS = {
    pubmed: {
        labels: ['pubmed search'],
        ids: ['pubmed-search', 'pubmed-search-mcp'],
        keywords: ['pubmed', 'pubmed-search'],
    },
    zotero: {
        labels: ['zotero keeper'],
        ids: ['zotero-keeper', 'zoterokeeper'],
        keywords: ['zotero', 'zotero-keeper'],
    },
} as const;

function normalizeExtensionText(value: unknown): string {
    return typeof value === 'string'
        ? value.trim().toLowerCase()
        : '';
}

function matchesAnyToken(value: string, tokens: readonly string[]): boolean {
    return tokens.some(token => value.includes(token));
}

function packageJsonProvidesMcpLabel(packageJson: any, labels: readonly string[]): boolean {
    const providers = Array.isArray(packageJson?.contributes?.mcpServerDefinitionProviders)
        ? packageJson.contributes.mcpServerDefinitionProviders
        : [];

    return providers.some((provider: any) => {
        const label = normalizeExtensionText(provider?.label);
        const id = normalizeExtensionText(provider?.id);
        return matchesAnyToken(label, labels) || matchesAnyToken(id, labels);
    });
}

function packageJsonMatchesExtensionMetadata(packageJson: any, ids: readonly string[], keywords: readonly string[]): boolean {
    const textCandidates = [
        packageJson?.name,
        packageJson?.displayName,
        packageJson?.description,
    ].map(normalizeExtensionText);

    return textCandidates.some(candidate =>
        matchesAnyToken(candidate, ids) || matchesAnyToken(candidate, keywords)
    );
}

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
 * @returns Object with counts and details
 */
export function countMissingBundledItems(
    wsRoot: string,
    extPath: string,
    bundledSkills: readonly string[],
    bundledAgents: readonly string[],
    bundledPrompts: readonly string[],
): { missingSkills: number; missingAgents: number; missingPrompts: number; total: number } {
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

    return {
        missingSkills,
        missingAgents,
        missingPrompts,
        total: missingSkills + missingAgents + missingPrompts,
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

/**
 * Detect which managed external MCP servers are already provided by other
 * installed VS Code extensions, so MedPaper can avoid duplicate registration.
 *
 * @param extensions - Installed VS Code extensions metadata
 * @param selfExtensionId - Current extension id to exclude from checks
 * @returns Object describing whether PubMed / Zotero are externally provided
 */
export function detectExternallyProvidedMcpServers(
    extensions: ReadonlyArray<{ id?: string; packageJSON?: any }>,
    selfExtensionId?: string,
): { pubmed: boolean; zotero: boolean } {
    const result = { pubmed: false, zotero: false };

    for (const extension of extensions) {
        const extensionId = normalizeExtensionText(extension.id);
        if (selfExtensionId && extensionId === normalizeExtensionText(selfExtensionId)) {
            continue;
        }

        const packageJson = extension.packageJSON;
        if (!packageJson) {
            continue;
        }

        if (!result.pubmed) {
            result.pubmed =
                packageJsonProvidesMcpLabel(packageJson, EXTERNAL_MCP_EXTENSION_TARGETS.pubmed.labels)
                || packageJsonMatchesExtensionMetadata(
                    packageJson,
                    EXTERNAL_MCP_EXTENSION_TARGETS.pubmed.ids,
                    EXTERNAL_MCP_EXTENSION_TARGETS.pubmed.keywords,
                );
        }

        if (!result.zotero) {
            result.zotero =
                packageJsonProvidesMcpLabel(packageJson, EXTERNAL_MCP_EXTENSION_TARGETS.zotero.labels)
                || packageJsonMatchesExtensionMetadata(
                    packageJson,
                    EXTERNAL_MCP_EXTENSION_TARGETS.zotero.ids,
                    EXTERNAL_MCP_EXTENSION_TARGETS.zotero.keywords,
                );
        }

        if (result.pubmed && result.zotero) {
            return result;
        }
    }

    return result;
}

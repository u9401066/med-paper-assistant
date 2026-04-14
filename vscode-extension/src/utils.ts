/**
 * Utility functions for MedPaper Assistant VS Code Extension.
 * Extracted for testability — NO vscode API dependency.
 */

import * as path from 'path';
import * as fs from 'fs';
import bundleManifest from '../bundle-manifest.json';

type SupportFile = {
    name: string;
    source: string;
    destination: string;
    workspaceDestination: string;
};

type PythonSourceBundle = {
    name: string;
    source: string;
    destination: string;
    required?: boolean;
};

type BundleManifest = {
    skills: string[];
    prompts: string[];
    agents: string[];
    templates: string[];
    supportFiles: SupportFile[];
    chatCommands: string[];
    paletteCommands: string[];
    pythonSources: PythonSourceBundle[];
};

export const BUNDLE_MANIFEST = bundleManifest as BundleManifest;

/**
 * Determine the correct Python args based on the command being used.
 * Handles uv, uvx, python, and fallback cases.
 */
export function getPythonArgs(command: string, module: string): string[] {
    const baseCommand = path.basename(command).toLowerCase();
    const commandName = baseCommand.replace(/\.exe$/, '');

    // Case 1: uv run python -m ...
    if (commandName === 'uv') {
        return ['run', 'python', '-m', module];
    }

    // Case 2: uvx package (NO -m)
    if (commandName === 'uvx') {
        const packageMap: Record<string, string> = {
            'med_paper_assistant.interfaces.mcp': 'med-paper-assistant',
            'pubmed_search.mcp': 'pubmed-search-mcp',
            'cgu.server': 'creativity-generation-unit'
        };
        const pkg = packageMap[module];
        if (pkg) {
            return [pkg];
        }
        return [module];
    }

    // Case 3: Standard python -m ... (match python, python3, python3.12, py, etc.)
    if (commandName === 'python' || commandName === 'py' || /^python3(\.\d+)?$/.test(commandName)) {
        return ['-m', module];
    }

    // Case 4: Path contains venv
    if (command.includes('.venv') || command.includes('venv')) {
        return ['-m', module];
    }

    return [module];
}

/**
 * Load all SKILL.md files from a directory as concatenated instructions.
 */
export function loadSkillsAsInstructions(skillsPath: string): string {
    const instructions: string[] = [];

    if (!fs.existsSync(skillsPath)) {
        return '';
    }

    const skillDirs = fs.readdirSync(skillsPath, { withFileTypes: true })
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name);

    for (const skillDir of skillDirs) {
        const skillFile = path.join(skillsPath, skillDir, 'SKILL.md');
        if (fs.existsSync(skillFile)) {
            const content = fs.readFileSync(skillFile, 'utf-8');
            instructions.push(`## Skill: ${skillDir}\n\n${content}`);
        }
    }

    return instructions.join('\n\n---\n\n');
}

/**
 * Load a single skill's content.
 */
export function loadSkillContent(skillsPath: string, skillName: string): string | null {
    const skillFile = path.join(skillsPath, skillName, 'SKILL.md');
    if (fs.existsSync(skillFile)) {
        return fs.readFileSync(skillFile, 'utf-8');
    }
    return null;
}

/**
 * Bundle manifest data shared by build scripts, validation, tests, and workflows.
 */
export const BUNDLED_SKILLS = [...BUNDLE_MANIFEST.skills];

/**
 * Prompts bundled in the VSX extension.
 */
export const BUNDLED_PROMPTS = [...BUNDLE_MANIFEST.prompts];

/**
 * Agents bundled in the VSX extension.
 */
export const BUNDLED_AGENTS = [...BUNDLE_MANIFEST.agents];

/**
 * Templates bundled in the VSX extension.
 */
export const BUNDLED_TEMPLATES = [...BUNDLE_MANIFEST.templates];

/**
 * Additional support files bundled in the VSX extension.
 */
export const BUNDLED_SUPPORT_FILES = [...BUNDLE_MANIFEST.supportFiles];

/**
 * Chat commands expected in package.json.
 */
export const BUNDLED_CHAT_COMMANDS = [...BUNDLE_MANIFEST.chatCommands];

/**
 * Palette commands expected in package.json.
 */
export const BUNDLED_PALETTE_COMMANDS = [...BUNDLE_MANIFEST.paletteCommands];

/**
 * Python source bundles copied into the VSIX during build-time packaging.
 */
export const PYTHON_SOURCE_BUNDLES = [...BUNDLE_MANIFEST.pythonSources];

/**
 * Validate that bundled skills match the source directory.
 * Returns a report of missing/extra skills.
 */
export function validateBundledSkills(
    bundledSkillsDir: string,
    sourceSkillsDir: string,
): { missing: string[]; extra: string[]; synced: string[] } {
    const missing: string[] = [];
    const extra: string[] = [];
    const synced: string[] = [];

    for (const skill of BUNDLED_SKILLS) {
        const srcFile = path.join(sourceSkillsDir, skill, 'SKILL.md');
        const dstFile = path.join(bundledSkillsDir, skill, 'SKILL.md');

        if (!fs.existsSync(srcFile)) {
            extra.push(skill); // In bundled list but not in source
        } else if (!fs.existsSync(dstFile)) {
            missing.push(skill); // In source but not bundled
        } else {
            // Check content matches
            const srcContent = fs.readFileSync(srcFile, 'utf-8');
            const dstContent = fs.readFileSync(dstFile, 'utf-8');
            if (srcContent !== dstContent) {
                missing.push(skill + ' (outdated)');
            } else {
                synced.push(skill);
            }
        }
    }

    return { missing, extra, synced };
}

/**
 * Validate that bundled prompts match the source directory.
 */
export function validateBundledPrompts(
    bundledPromptsDir: string,
    sourcePromptsDir: string,
): { missing: string[]; extra: string[]; synced: string[] } {
    const missing: string[] = [];
    const extra: string[] = [];
    const synced: string[] = [];

    // Check listed prompts
    for (const prompt of BUNDLED_PROMPTS) {
        const filename = `${prompt}.prompt.md`;
        const srcFile = path.join(sourcePromptsDir, filename);
        const dstFile = path.join(bundledPromptsDir, filename);

        if (!fs.existsSync(srcFile)) {
            extra.push(prompt);
        } else if (!fs.existsSync(dstFile)) {
            missing.push(prompt);
        } else {
            const srcContent = fs.readFileSync(srcFile, 'utf-8');
            const dstContent = fs.readFileSync(dstFile, 'utf-8');
            if (srcContent !== dstContent) {
                missing.push(prompt + ' (outdated)');
            } else {
                synced.push(prompt);
            }
        }
    }

    // Check _capability-index.md
    const idxSrc = path.join(sourcePromptsDir, '_capability-index.md');
    const idxDst = path.join(bundledPromptsDir, '_capability-index.md');
    if (fs.existsSync(idxSrc) && !fs.existsSync(idxDst)) {
        missing.push('_capability-index.md');
    }

    return { missing, extra, synced };
}

/**
 * Validate that bundled support files match the source directory.
 */
export function validateBundledSupportFiles(
    extensionRootDir: string,
    repoRootDir: string,
): { missing: string[]; extra: string[]; synced: string[] } {
    const missing: string[] = [];
    const extra: string[] = [];
    const synced: string[] = [];

    for (const file of BUNDLED_SUPPORT_FILES) {
        const srcFile = path.join(repoRootDir, file.source);
        const dstFile = path.join(extensionRootDir, file.destination);

        if (!fs.existsSync(srcFile)) {
            extra.push(file.name);
        } else if (!fs.existsSync(dstFile)) {
            missing.push(file.name);
        } else {
            const srcContent = fs.readFileSync(srcFile, 'utf-8');
            const dstContent = fs.readFileSync(dstFile, 'utf-8');
            if (srcContent !== dstContent) {
                missing.push(file.name + ' (outdated)');
            } else {
                synced.push(file.name);
            }
        }
    }

    return { missing, extra, synced };
}

/**
 * Validate that bundled templates match the source directory.
 */
export function validateBundledTemplates(
    bundledTemplatesDir: string,
    sourceTemplatesDir: string,
): { missing: string[]; extra: string[]; synced: string[] } {
    const missing: string[] = [];
    const extra: string[] = [];
    const synced: string[] = [];

    for (const tmpl of BUNDLED_TEMPLATES) {
        const srcFile = path.join(sourceTemplatesDir, tmpl);
        const dstFile = path.join(bundledTemplatesDir, tmpl);

        if (!fs.existsSync(srcFile)) {
            extra.push(tmpl);
        } else if (!fs.existsSync(dstFile)) {
            missing.push(tmpl);
        } else {
            const srcContent = fs.readFileSync(srcFile, 'utf-8');
            const dstContent = fs.readFileSync(dstFile, 'utf-8');
            if (srcContent !== dstContent) {
                missing.push(tmpl + ' (outdated)');
            } else {
                synced.push(tmpl);
            }
        }
    }

    return { missing, extra, synced };
}

/**
 * Validate that bundled agents match the source directory.
 */
export function validateBundledAgents(
    bundledAgentsDir: string,
    sourceAgentsDir: string,
): { missing: string[]; extra: string[]; synced: string[] } {
    const missing: string[] = [];
    const extra: string[] = [];
    const synced: string[] = [];

    for (const agent of BUNDLED_AGENTS) {
        const filename = `${agent}.agent.md`;
        const srcFile = path.join(sourceAgentsDir, filename);
        const dstFile = path.join(bundledAgentsDir, filename);

        if (!fs.existsSync(srcFile)) {
            extra.push(agent);
        } else if (!fs.existsSync(dstFile)) {
            missing.push(agent);
        } else {
            const srcContent = fs.readFileSync(srcFile, 'utf-8');
            const dstContent = fs.readFileSync(dstFile, 'utf-8');
            if (srcContent !== dstContent) {
                missing.push(agent + ' (outdated)');
            } else {
                synced.push(agent);
            }
        }
    }

    return { missing, extra, synced };
}

/**
 * Validate package.json chat commands match bundled prompts.
 */
export function validateChatCommands(packageJsonPath: string): { valid: boolean; issues: string[] } {
    const issues: string[] = [];

    if (!fs.existsSync(packageJsonPath)) {
        return { valid: false, issues: ['package.json not found'] };
    }

    const pkg = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
    const chatParticipants = pkg.contributes?.chatParticipants;
    if (!chatParticipants || chatParticipants.length === 0) {
        return { valid: false, issues: ['No chatParticipants defined'] };
    }

    const commands = chatParticipants[0].commands || [];
    const commandNames = commands.map((c: { name: string }) => c.name);

    // Required commands
    for (const cmd of BUNDLED_CHAT_COMMANDS) {
        if (!commandNames.includes(cmd)) {
            issues.push(`Missing chat command: /${cmd}`);
        }
    }

    return { valid: issues.length === 0, issues };
}

/**
 * Extract version from package.json.
 */
export function getPackageVersion(packageJsonPath: string): string | null {
    if (!fs.existsSync(packageJsonPath)) {
        return null;
    }
    const pkg = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
    return pkg.version || null;
}

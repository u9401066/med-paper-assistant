import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import {
    BUNDLE_MANIFEST,
    getPythonArgs,
    loadSkillsAsInstructions,
    loadSkillContent,
    validateBundledSkills,
    validateBundledPrompts,
    validateBundledSupportFiles,
    validateBundledTemplates,
    validateBundledAgents,
    validateChatCommands,
    getPackageVersion,
    BUNDLED_SKILLS,
    BUNDLED_PROMPTS,
    BUNDLED_SUPPORT_FILES,
    BUNDLED_TEMPLATES,
    BUNDLED_AGENTS,
    BUNDLED_CHAT_COMMANDS,
    BUNDLED_PALETTE_COMMANDS,
    PYTHON_SOURCE_BUNDLES,
} from '../utils';

// ──────────────────────────────────────────────────────────
// getPythonArgs
// ──────────────────────────────────────────────────────────

describe('getPythonArgs', () => {
    const MODULE = 'med_paper_assistant.interfaces.mcp';

    it('uv → run python -m module', () => {
        expect(getPythonArgs('uv', MODULE)).toEqual(['run', 'python', '-m', MODULE]);
    });

    it('uvx → package name from map', () => {
        expect(getPythonArgs('uvx', MODULE)).toEqual(['med-paper-assistant']);
        expect(getPythonArgs('uvx', 'cgu.server')).toEqual(['creativity-generation-unit']);
        expect(getPythonArgs('uvx', 'pubmed_search.mcp')).toEqual(['pubmed-search-mcp']);
    });

    it('uvx → module as fallback for unmapped', () => {
        expect(getPythonArgs('uvx', 'some.unknown.module')).toEqual(['some.unknown.module']);
    });

    it('python → -m module', () => {
        expect(getPythonArgs('python', MODULE)).toEqual(['-m', MODULE]);
        expect(getPythonArgs('python3', MODULE)).toEqual(['-m', MODULE]);
        expect(getPythonArgs('py', MODULE)).toEqual(['-m', MODULE]);
    });

    it('versioned python (homebrew/macOS) → -m module', () => {
        expect(getPythonArgs('/opt/homebrew/bin/python3.12', MODULE)).toEqual(['-m', MODULE]);
        expect(getPythonArgs('python3.11', MODULE)).toEqual(['-m', MODULE]);
    });

    it('python.exe (Windows) → -m module', () => {
        expect(getPythonArgs('python.exe', MODULE)).toEqual(['-m', MODULE]);
    });

    it('venv python path → -m module', () => {
        expect(getPythonArgs('/path/.venv/bin/python', MODULE)).toEqual(['-m', MODULE]);
        expect(getPythonArgs('C:\\project\\venv\\Scripts\\python.exe', MODULE)).toEqual(['-m', MODULE]);
    });

    it('unknown command → module only', () => {
        expect(getPythonArgs('/usr/bin/custom', MODULE)).toEqual([MODULE]);
    });
});

// ──────────────────────────────────────────────────────────
// loadSkillsAsInstructions / loadSkillContent
// ──────────────────────────────────────────────────────────

describe('loadSkillsAsInstructions', () => {
    let tmpDir: string;

    beforeAll(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-test-skills-'));
        // Create 2 test skills
        fs.mkdirSync(path.join(tmpDir, 'skill-a'));
        fs.writeFileSync(path.join(tmpDir, 'skill-a', 'SKILL.md'), '# Skill A\nContent A');
        fs.mkdirSync(path.join(tmpDir, 'skill-b'));
        fs.writeFileSync(path.join(tmpDir, 'skill-b', 'SKILL.md'), '# Skill B\nContent B');
        // Create a dir without SKILL.md (should be skipped)
        fs.mkdirSync(path.join(tmpDir, 'empty-dir'));
    });

    afterAll(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('loads all SKILL.md files', () => {
        const result = loadSkillsAsInstructions(tmpDir);
        expect(result).toContain('## Skill: skill-a');
        expect(result).toContain('Content A');
        expect(result).toContain('## Skill: skill-b');
        expect(result).toContain('Content B');
    });

    it('skips directories without SKILL.md', () => {
        const result = loadSkillsAsInstructions(tmpDir);
        expect(result).not.toContain('empty-dir');
    });

    it('returns empty string for non-existent path', () => {
        expect(loadSkillsAsInstructions('/non/existent/path')).toBe('');
    });
});

describe('loadSkillContent', () => {
    let tmpDir: string;

    beforeAll(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-test-skill-'));
        fs.mkdirSync(path.join(tmpDir, 'test-skill'));
        fs.writeFileSync(path.join(tmpDir, 'test-skill', 'SKILL.md'), '# Test Skill');
    });

    afterAll(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('loads existing skill', () => {
        expect(loadSkillContent(tmpDir, 'test-skill')).toBe('# Test Skill');
    });

    it('returns null for missing skill', () => {
        expect(loadSkillContent(tmpDir, 'nonexistent')).toBeNull();
    });
});

// ──────────────────────────────────────────────────────────
// validateBundledSkills / validateBundledPrompts
// ──────────────────────────────────────────────────────────

describe('validateBundledSkills', () => {
    let srcDir: string;
    let dstDir: string;

    beforeAll(() => {
        srcDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-src-skills-'));
        dstDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-dst-skills-'));
        // Create source skills matching BUNDLED_SKILLS
        for (const skill of BUNDLED_SKILLS) {
            fs.mkdirSync(path.join(srcDir, skill));
            fs.writeFileSync(path.join(srcDir, skill, 'SKILL.md'), `# ${skill}`);
        }
    });

    afterAll(() => {
        fs.rmSync(srcDir, { recursive: true, force: true });
        fs.rmSync(dstDir, { recursive: true, force: true });
    });

    it('detects all missing when destination is empty', () => {
        const result = validateBundledSkills(dstDir, srcDir);
        expect(result.missing.length).toBe(BUNDLED_SKILLS.length);
        expect(result.synced.length).toBe(0);
    });

    it('detects synced when content matches', () => {
        // Copy one skill
        const skill = BUNDLED_SKILLS[0];
        fs.mkdirSync(path.join(dstDir, skill), { recursive: true });
        fs.writeFileSync(path.join(dstDir, skill, 'SKILL.md'), `# ${skill}`);

        const result = validateBundledSkills(dstDir, srcDir);
        expect(result.synced).toContain(skill);
    });

    it('detects outdated content', () => {
        const skill = BUNDLED_SKILLS[1];
        fs.mkdirSync(path.join(dstDir, skill), { recursive: true });
        fs.writeFileSync(path.join(dstDir, skill, 'SKILL.md'), 'OUTDATED');

        const result = validateBundledSkills(dstDir, srcDir);
        expect(result.missing).toContain(`${skill} (outdated)`);
    });
});

describe('validateBundledPrompts', () => {
    let srcDir: string;
    let dstDir: string;

    beforeAll(() => {
        srcDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-src-prompts-'));
        dstDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-dst-prompts-'));
        for (const prompt of BUNDLED_PROMPTS) {
            fs.writeFileSync(path.join(srcDir, `${prompt}.prompt.md`), `# ${prompt}`);
        }
        fs.writeFileSync(path.join(srcDir, '_capability-index.md'), '# Index');
    });

    afterAll(() => {
        fs.rmSync(srcDir, { recursive: true, force: true });
        fs.rmSync(dstDir, { recursive: true, force: true });
    });

    it('detects missing prompts', () => {
        const result = validateBundledPrompts(dstDir, srcDir);
        expect(result.missing.length).toBeGreaterThan(0);
    });

    it('detects missing _capability-index.md', () => {
        const result = validateBundledPrompts(dstDir, srcDir);
        expect(result.missing).toContain('_capability-index.md');
    });
});

describe('validateBundledSupportFiles', () => {
    let repoRootDir: string;
    let extensionRootDir: string;

    beforeAll(() => {
        repoRootDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-support-repo-'));
        extensionRootDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-support-ext-'));

        for (const file of BUNDLED_SUPPORT_FILES) {
            const srcFile = path.join(repoRootDir, file.source);
            const dstFile = path.join(extensionRootDir, file.destination);
            fs.mkdirSync(path.dirname(srcFile), { recursive: true });
            fs.mkdirSync(path.dirname(dstFile), { recursive: true });
            fs.writeFileSync(srcFile, `source:${file.name}`);
        }
    });

    afterAll(() => {
        fs.rmSync(repoRootDir, { recursive: true, force: true });
        fs.rmSync(extensionRootDir, { recursive: true, force: true });
    });

    it('detects missing support files', () => {
        const result = validateBundledSupportFiles(extensionRootDir, repoRootDir);
        expect(result.missing.length).toBe(BUNDLED_SUPPORT_FILES.length);
    });

    it('detects synced support files when content matches', () => {
        const file = BUNDLED_SUPPORT_FILES[0];
        const srcFile = path.join(repoRootDir, file.source);
        const dstFile = path.join(extensionRootDir, file.destination);
        fs.mkdirSync(path.dirname(dstFile), { recursive: true });
        fs.copyFileSync(srcFile, dstFile);

        const result = validateBundledSupportFiles(extensionRootDir, repoRootDir);
        expect(result.synced).toContain(file.name);
    });
});

// ──────────────────────────────────────────────────────────
// validateChatCommands
// ──────────────────────────────────────────────────────────

describe('validateChatCommands', () => {
    let tmpFile: string;

    afterAll(() => {
        if (tmpFile && fs.existsSync(tmpFile)) {
            fs.unlinkSync(tmpFile);
        }
    });

    it('validates real package.json', () => {
        const pkgPath = path.resolve(__dirname, '..', '..', 'package.json');
        const result = validateChatCommands(pkgPath);
        expect(result.valid).toBe(true);
        expect(result.issues).toHaveLength(0);
    });

    it('detects missing commands', () => {
        tmpFile = path.join(os.tmpdir(), 'test-pkg.json');
        fs.writeFileSync(tmpFile, JSON.stringify({
            contributes: {
                chatParticipants: [{
                    commands: [{ name: 'search' }]
                }]
            }
        }));
        const result = validateChatCommands(tmpFile);
        expect(result.valid).toBe(false);
        expect(result.issues.length).toBeGreaterThan(0);
    });

    it('handles missing file', () => {
        const result = validateChatCommands('/no/such/file.json');
        expect(result.valid).toBe(false);
    });
});

// ──────────────────────────────────────────────────────────
// getPackageVersion
// ──────────────────────────────────────────────────────────

describe('getPackageVersion', () => {
    it('reads version from package.json', () => {
        const pkgPath = path.resolve(__dirname, '..', '..', 'package.json');
        const version = getPackageVersion(pkgPath);
        expect(version).toMatch(/^\d+\.\d+\.\d+/);
    });

    it('returns null for missing file', () => {
        expect(getPackageVersion('/no/file')).toBeNull();
    });
});

// ──────────────────────────────────────────────────────────
// Constants integrity
// ──────────────────────────────────────────────────────────

describe('BUNDLED_SKILLS', () => {
    it('contains expected core skills', () => {
        expect(BUNDLED_SKILLS).toContain('auto-paper');
        expect(BUNDLED_SKILLS).toContain('literature-review');
        expect(BUNDLED_SKILLS).toContain('draft-writing');
        expect(BUNDLED_SKILLS).toContain('git-precommit');
    });

    it('has no duplicates', () => {
        const unique = new Set(BUNDLED_SKILLS);
        expect(unique.size).toBe(BUNDLED_SKILLS.length);
    });
});

describe('BUNDLED_PROMPTS', () => {
    it('contains expected prompts', () => {
        expect(BUNDLED_PROMPTS).toContain('mdpaper.search');
        expect(BUNDLED_PROMPTS).toContain('mdpaper.draft');
        expect(BUNDLED_PROMPTS).toContain('mdpaper.write-paper');
    });

    it('has no duplicates', () => {
        const unique = new Set(BUNDLED_PROMPTS);
        expect(unique.size).toBe(BUNDLED_PROMPTS.length);
    });
});

describe('BUNDLE_MANIFEST', () => {
    it('defines all shared bundle groups', () => {
        expect(BUNDLE_MANIFEST.skills.length).toBe(BUNDLED_SKILLS.length);
        expect(BUNDLE_MANIFEST.prompts.length).toBe(BUNDLED_PROMPTS.length);
        expect(BUNDLE_MANIFEST.supportFiles.length).toBe(BUNDLED_SUPPORT_FILES.length);
        expect(BUNDLE_MANIFEST.templates.length).toBe(BUNDLED_TEMPLATES.length);
        expect(BUNDLE_MANIFEST.agents.length).toBe(BUNDLED_AGENTS.length);
        expect(BUNDLE_MANIFEST.chatCommands.length).toBe(BUNDLED_CHAT_COMMANDS.length);
        expect(BUNDLE_MANIFEST.paletteCommands.length).toBe(BUNDLED_PALETTE_COMMANDS.length);
        expect(BUNDLE_MANIFEST.pythonSources.length).toBe(PYTHON_SOURCE_BUNDLES.length);
    });

    it('has no duplicate bundle identifiers within each group', () => {
        const groups = [
            BUNDLED_SKILLS,
            BUNDLED_PROMPTS,
            BUNDLED_TEMPLATES,
            BUNDLED_AGENTS,
            BUNDLED_CHAT_COMMANDS,
            BUNDLED_PALETTE_COMMANDS,
        ];

        for (const group of groups) {
            expect(new Set(group).size).toBe(group.length);
        }
    });
});

// ──────────────────────────────────────────────────────────
// Integration: Source ↔ VSX Sync Check
// ──────────────────────────────────────────────────────────

describe('Source ↔ VSX Sync', () => {
    const rootDir = path.resolve(__dirname, '..', '..', '..');
    const extDir = path.resolve(__dirname, '..', '..');
    const sourceSkillsDir = path.join(rootDir, '.claude', 'skills');
    const sourcePromptsDir = path.join(rootDir, '.github', 'prompts');
    const sourceTemplatesDir = path.join(rootDir, 'templates');
    const sourceAgentsDir = path.join(rootDir, '.github', 'agents');
    const bundledSkillsDir = path.join(extDir, 'skills');
    const bundledPromptsDir = path.join(extDir, 'prompts');
    const bundledSupportRoot = extDir;
    const bundledTemplatesDir = path.join(extDir, 'templates');
    const bundledAgentsDir = path.join(extDir, 'agents');

    it('all BUNDLED_SKILLS exist in source .claude/skills/', () => {
        for (const skill of BUNDLED_SKILLS) {
            const skillPath = path.join(sourceSkillsDir, skill, 'SKILL.md');
            expect(fs.existsSync(skillPath), `Missing source skill: ${skill}`).toBe(true);
        }
    });

    it('all BUNDLED_PROMPTS exist in source .github/prompts/', () => {
        for (const prompt of BUNDLED_PROMPTS) {
            const promptPath = path.join(sourcePromptsDir, `${prompt}.prompt.md`);
            expect(fs.existsSync(promptPath), `Missing source prompt: ${prompt}`).toBe(true);
        }
    });

    it('bundled skills are in sync with source (after build)', () => {
        // Only run if bundled dir exists (post-build)
        if (!fs.existsSync(bundledSkillsDir)) {
            return; // Skip pre-build
        }
        const result = validateBundledSkills(bundledSkillsDir, sourceSkillsDir);
        expect(result.missing, `Out of sync skills: ${result.missing.join(', ')}`).toHaveLength(0);
    });

    it('bundled prompts are in sync with source (after build)', () => {
        if (!fs.existsSync(bundledPromptsDir)) {
            return; // Skip pre-build
        }
        const result = validateBundledPrompts(bundledPromptsDir, sourcePromptsDir);
        expect(result.missing, `Out of sync prompts: ${result.missing.join(', ')}`).toHaveLength(0);
    });

    it('bundled support files are in sync with source (after build)', () => {
        const result = validateBundledSupportFiles(bundledSupportRoot, rootDir);
        expect(result.missing, `Out of sync support files: ${result.missing.join(', ')}`).toHaveLength(0);
    });

    it('all BUNDLED_TEMPLATES exist in source templates/', () => {
        for (const tmpl of BUNDLED_TEMPLATES) {
            const tmplPath = path.join(sourceTemplatesDir, tmpl);
            expect(fs.existsSync(tmplPath), `Missing source template: ${tmpl}`).toBe(true);
        }
    });

    it('bundled templates are in sync with source (after build)', () => {
        if (!fs.existsSync(bundledTemplatesDir)) {
            return; // Skip pre-build
        }
        const result = validateBundledTemplates(bundledTemplatesDir, sourceTemplatesDir);
        expect(result.missing, `Out of sync templates: ${result.missing.join(', ')}`).toHaveLength(0);
    });

    it('all BUNDLED_AGENTS exist in source .github/agents/', () => {
        for (const agent of BUNDLED_AGENTS) {
            const agentPath = path.join(sourceAgentsDir, `${agent}.agent.md`);
            expect(fs.existsSync(agentPath), `Missing source agent: ${agent}`).toBe(true);
        }
    });

    it('bundled agents are in sync with source (after build)', () => {
        if (!fs.existsSync(bundledAgentsDir)) {
            return; // Skip pre-build
        }
        const result = validateBundledAgents(bundledAgentsDir, sourceAgentsDir);
        expect(result.missing, `Out of sync agents: ${result.missing.join(', ')}`).toHaveLength(0);
    });
});

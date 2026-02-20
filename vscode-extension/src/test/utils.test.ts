import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import {
    getPythonArgs,
    loadSkillsAsInstructions,
    loadSkillContent,
    validateBundledSkills,
    validateBundledPrompts,
    validateChatCommands,
    getPackageVersion,
    BUNDLED_SKILLS,
    BUNDLED_PROMPTS,
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

// ──────────────────────────────────────────────────────────
// Integration: Source ↔ VSX Sync Check
// ──────────────────────────────────────────────────────────

describe('Source ↔ VSX Sync', () => {
    const rootDir = path.resolve(__dirname, '..', '..', '..');
    const extDir = path.resolve(__dirname, '..', '..');
    const sourceSkillsDir = path.join(rootDir, '.claude', 'skills');
    const sourcePromptsDir = path.join(rootDir, '.github', 'prompts');
    const bundledSkillsDir = path.join(extDir, 'skills');
    const bundledPromptsDir = path.join(extDir, 'prompts');

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
});

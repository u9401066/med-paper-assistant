import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import {
    shouldSkipMcpRegistration,
    isDevWorkspace,
    isMedPaperProject,
    determinePythonPath,
    countMissingBundledItems,
    buildDevPythonPath,
    detectExternallyProvidedMcpServers,
} from '../extensionHelpers';

// ──────────────────────────────────────────────────────────
// shouldSkipMcpRegistration
// ──────────────────────────────────────────────────────────

describe('shouldSkipMcpRegistration', () => {
    it('returns true when both "mdpaper" and med_paper_assistant are present', () => {
        const content = `{
            "servers": {
                "mdpaper": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "med_paper_assistant.interfaces.mcp"]
                }
            }
        }`;
        expect(shouldSkipMcpRegistration(content)).toBe(true);
    });

    it('returns false when only "mdpaper" is present (no med_paper_assistant)', () => {
        const content = `{
            "servers": {
                "mdpaper": {
                    "command": "python",
                    "args": ["-m", "some_other_module"]
                }
            }
        }`;
        expect(shouldSkipMcpRegistration(content)).toBe(false);
    });

    it('returns false when only med_paper_assistant is present (different server name)', () => {
        const content = `{
            "servers": {
                "my-server": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "med_paper_assistant.interfaces.mcp"]
                }
            }
        }`;
        expect(shouldSkipMcpRegistration(content)).toBe(false);
    });

    it('returns false for empty mcp.json', () => {
        expect(shouldSkipMcpRegistration('{}')).toBe(false);
    });

    it('returns false for mcp.json with other servers only', () => {
        const content = `{
            "servers": {
                "pubmed": { "command": "uvx", "args": ["pubmed-search"] },
                "cgu": { "command": "uvx", "args": ["cgu"] }
            }
        }`;
        expect(shouldSkipMcpRegistration(content)).toBe(false);
    });

    it('handles JSON5 comments (string match, not parse)', () => {
        const content = `{
            // Main server
            "servers": {
                "mdpaper": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "med_paper_assistant.interfaces.mcp"]
                }
            }
        }`;
        expect(shouldSkipMcpRegistration(content)).toBe(true);
    });
});

// ──────────────────────────────────────────────────────────
// isDevWorkspace
// ──────────────────────────────────────────────────────────

describe('isDevWorkspace', () => {
    let tmpDir: string;

    beforeAll(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-devws-'));
    });

    afterAll(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('returns true when src/med_paper_assistant exists', () => {
        fs.mkdirSync(path.join(tmpDir, 'src', 'med_paper_assistant'), { recursive: true });
        expect(isDevWorkspace(tmpDir)).toBe(true);
    });

    it('returns false when src/med_paper_assistant does not exist', () => {
        const emptyDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-empty-'));
        try {
            expect(isDevWorkspace(emptyDir)).toBe(false);
        } finally {
            fs.rmSync(emptyDir, { recursive: true, force: true });
        }
    });

    it('returns false when only src exists (no med_paper_assistant)', () => {
        const srcOnlyDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-srconly-'));
        fs.mkdirSync(path.join(srcOnlyDir, 'src'), { recursive: true });
        try {
            expect(isDevWorkspace(srcOnlyDir)).toBe(false);
        } finally {
            fs.rmSync(srcOnlyDir, { recursive: true, force: true });
        }
    });
});

// ──────────────────────────────────────────────────────────
// isMedPaperProject
// ──────────────────────────────────────────────────────────

describe('isMedPaperProject', () => {
    let tmpDir: string;

    beforeAll(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-pyproj-'));
    });

    afterAll(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('returns true for med-paper-assistant pyproject.toml', () => {
        const pyprojectPath = path.join(tmpDir, 'pyproject.toml');
        fs.writeFileSync(pyprojectPath, `[project]\nname = "med-paper-assistant"\nversion = "0.4.5"\n`);
        expect(isMedPaperProject(pyprojectPath)).toBe(true);
    });

    it('returns false for unrelated pyproject.toml', () => {
        const pyprojectPath = path.join(tmpDir, 'other-pyproject.toml');
        fs.writeFileSync(pyprojectPath, `[project]\nname = "my-web-app"\nversion = "1.0.0"\n`);
        expect(isMedPaperProject(pyprojectPath)).toBe(false);
    });

    it('returns false for non-existent file', () => {
        expect(isMedPaperProject('/nonexistent/pyproject.toml')).toBe(false);
    });

    it('returns true when med-paper-assistant appears in dependencies', () => {
        const pyprojectPath = path.join(tmpDir, 'dep-pyproject.toml');
        fs.writeFileSync(pyprojectPath, `[project]\nname = "my-tool"\ndependencies = ["med-paper-assistant>=0.4"]\n`);
        expect(isMedPaperProject(pyprojectPath)).toBe(true);
    });
});

// ──────────────────────────────────────────────────────────
// determinePythonPath
// ──────────────────────────────────────────────────────────

describe('determinePythonPath', () => {
    let tmpDir: string;
    let extDir: string;

    beforeAll(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-pypath-'));
        extDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-ext-'));
    });

    afterAll(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
        fs.rmSync(extDir, { recursive: true, force: true });
    });

    it('returns "uv" when configured as "uv"', () => {
        expect(determinePythonPath({
            configuredPath: 'uv',
            extensionPath: extDir,
        })).toBe('uv');
    });

    it('returns "uvx" when configured as "uvx"', () => {
        expect(determinePythonPath({
            configuredPath: 'uvx',
            extensionPath: extDir,
        })).toBe('uvx');
    });

    it('returns configured path if it exists on disk', () => {
        const fakePython = path.join(tmpDir, 'custom-python');
        fs.writeFileSync(fakePython, '');
        expect(determinePythonPath({
            configuredPath: fakePython,
            extensionPath: extDir,
        })).toBe(fakePython);
    });

    it('ignores configured path if it does not exist (not "uv"/"uvx")', () => {
        const result = determinePythonPath({
            configuredPath: '/no/such/python',
            extensionPath: extDir,
        });
        // Falls through to fallback 'uv'
        expect(result).toBe('uv');
    });

    it('returns "uv" when workspace has med-paper-assistant pyproject.toml', () => {
        const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-ws-'));
        fs.writeFileSync(path.join(wsDir, 'pyproject.toml'),
            `[project]\nname = "med-paper-assistant"\n`);
        try {
            expect(determinePythonPath({
                wsRoot: wsDir,
                extensionPath: extDir,
            })).toBe('uv');
        } finally {
            fs.rmSync(wsDir, { recursive: true, force: true });
        }
    });

    it('skips pyproject.toml check for unrelated project', () => {
        const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-wsother-'));
        fs.writeFileSync(path.join(wsDir, 'pyproject.toml'),
            `[project]\nname = "my-web-app"\n`);
        try {
            const result = determinePythonPath({
                wsRoot: wsDir,
                extensionPath: extDir,
            });
            // Should NOT return 'uv' from pyproject check
            // Should fall to venv check or fallback
            expect(result).toBe('uv'); // fallback (no venv)
        } finally {
            fs.rmSync(wsDir, { recursive: true, force: true });
        }
    });

    it('finds .venv/bin/python when it exists', () => {
        const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-venv-'));
        const venvPython = path.join(wsDir, '.venv', 'bin', 'python');
        fs.mkdirSync(path.dirname(venvPython), { recursive: true });
        fs.writeFileSync(venvPython, '');
        try {
            expect(determinePythonPath({
                wsRoot: wsDir,
                extensionPath: extDir,
            })).toBe(venvPython);
        } finally {
            fs.rmSync(wsDir, { recursive: true, force: true });
        }
    });

    it('finds bundled Python when it exists', () => {
        const myExtDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-bundled-'));
        const bundledPy = path.join(myExtDir, 'bundled', 'python', 'bin', 'python3');
        fs.mkdirSync(path.dirname(bundledPy), { recursive: true });
        fs.writeFileSync(bundledPy, '');
        try {
            expect(determinePythonPath({
                extensionPath: myExtDir,
            })).toBe(bundledPy);
        } finally {
            fs.rmSync(myExtDir, { recursive: true, force: true });
        }
    });

    it('falls back to "uv" when nothing else matches', () => {
        expect(determinePythonPath({
            extensionPath: extDir,
        })).toBe('uv');
    });

    it('priority: configuredPath > pyproject > venv', () => {
        const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-priority-'));
        // Setup both pyproject + venv
        fs.writeFileSync(path.join(wsDir, 'pyproject.toml'),
            `[project]\nname = "med-paper-assistant"\n`);
        const venvPy = path.join(wsDir, '.venv', 'bin', 'python');
        fs.mkdirSync(path.dirname(venvPy), { recursive: true });
        fs.writeFileSync(venvPy, '');

        try {
            // configuredPath wins
            expect(determinePythonPath({
                configuredPath: 'uv',
                wsRoot: wsDir,
                extensionPath: extDir,
            })).toBe('uv');

            // Without configuredPath, pyproject wins
            expect(determinePythonPath({
                wsRoot: wsDir,
                extensionPath: extDir,
            })).toBe('uv'); // from pyproject check
        } finally {
            fs.rmSync(wsDir, { recursive: true, force: true });
        }
    });
});

// ──────────────────────────────────────────────────────────
// countMissingBundledItems
// ──────────────────────────────────────────────────────────

describe('countMissingBundledItems', () => {
    let wsDir: string;
    let extDir: string;

    beforeAll(() => {
        wsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-count-ws-'));
        extDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-count-ext-'));
    });

    afterAll(() => {
        fs.rmSync(wsDir, { recursive: true, force: true });
        fs.rmSync(extDir, { recursive: true, force: true });
    });

    it('returns all missing when workspace is empty', () => {
        // Create source skills in ext
        const skills = ['skill-a', 'skill-b'];
        const agents = ['agent-x'];
        const prompts = ['prompt-1'];

        for (const s of skills) {
            const src = path.join(extDir, 'skills', s, 'SKILL.md');
            fs.mkdirSync(path.dirname(src), { recursive: true });
            fs.writeFileSync(src, `# ${s}`);
        }
        for (const a of agents) {
            const src = path.join(extDir, 'agents', `${a}.agent.md`);
            fs.mkdirSync(path.dirname(src), { recursive: true });
            fs.writeFileSync(src, `# ${a}`);
        }
        for (const p of prompts) {
            const src = path.join(extDir, 'prompts', `${p}.prompt.md`);
            fs.mkdirSync(path.dirname(src), { recursive: true });
            fs.writeFileSync(src, `# ${p}`);
        }

        const result = countMissingBundledItems(wsDir, extDir, skills, agents, prompts);
        expect(result.missingSkills).toBe(2);
        expect(result.missingAgents).toBe(1);
        expect(result.missingPrompts).toBe(1);
        expect(result.total).toBe(4);
    });

    it('returns 0 when all items exist in workspace', () => {
        const skills = ['skill-a'];
        const agents = ['agent-x'];
        const prompts = ['prompt-1'];

        // Create in ext (source)
        const srcSkill = path.join(extDir, 'skills', 'skill-a', 'SKILL.md');
        fs.mkdirSync(path.dirname(srcSkill), { recursive: true });
        fs.writeFileSync(srcSkill, '# skill-a');

        // Create in workspace (destination)
        const dstSkill = path.join(wsDir, '.claude', 'skills', 'skill-a', 'SKILL.md');
        fs.mkdirSync(path.dirname(dstSkill), { recursive: true });
        fs.writeFileSync(dstSkill, '# skill-a');

        const dstAgent = path.join(wsDir, '.github', 'agents', 'agent-x.agent.md');
        fs.mkdirSync(path.dirname(dstAgent), { recursive: true });
        fs.writeFileSync(dstAgent, '# agent-x');

        const dstPrompt = path.join(wsDir, '.github', 'prompts', 'prompt-1.prompt.md');
        fs.mkdirSync(path.dirname(dstPrompt), { recursive: true });
        fs.writeFileSync(dstPrompt, '# prompt-1');

        const result = countMissingBundledItems(wsDir, extDir, skills, agents, prompts);
        expect(result.total).toBe(0);
    });

    it('handles empty arrays', () => {
        const result = countMissingBundledItems(wsDir, extDir, [], [], []);
        expect(result.total).toBe(0);
    });
});

// ──────────────────────────────────────────────────────────
// buildDevPythonPath
// ──────────────────────────────────────────────────────────

describe('buildDevPythonPath', () => {
    let wsDir: string;

    beforeAll(() => {
        wsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-devpy-'));
    });

    afterAll(() => {
        fs.rmSync(wsDir, { recursive: true, force: true });
    });

    it('starts with bundledToolPath when no src or cgu exists', () => {
        const emptyWs = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-empty-'));
        try {
            const result = buildDevPythonPath(emptyWs, '/ext/bundled/tool');
            expect(result).toBe('/ext/bundled/tool');
        } finally {
            fs.rmSync(emptyWs, { recursive: true, force: true });
        }
    });

    it('prepends src/ when it exists', () => {
        fs.mkdirSync(path.join(wsDir, 'src'), { recursive: true });
        const result = buildDevPythonPath(wsDir, '/ext/bundled/tool');
        const srcPath = path.join(wsDir, 'src');
        expect(result).toContain(srcPath);
        expect(result.startsWith(srcPath)).toBe(true);
    });

    it('prepends cgu/src when it exists', () => {
        const cguWs = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-cgu-'));
        fs.mkdirSync(path.join(cguWs, 'src'), { recursive: true });
        fs.mkdirSync(path.join(cguWs, 'integrations', 'cgu', 'src'), { recursive: true });
        try {
            const result = buildDevPythonPath(cguWs, '/ext/bundled/tool');
            expect(result).toContain('integrations/cgu/src');
        } finally {
            fs.rmSync(cguWs, { recursive: true, force: true });
        }
    });

    it('uses correct path delimiter', () => {
        fs.mkdirSync(path.join(wsDir, 'src'), { recursive: true });
        const result = buildDevPythonPath(wsDir, '/ext/bundled/tool');
        expect(result).toContain(path.delimiter);
    });
});

// ──────────────────────────────────────────────────────────
// detectExternallyProvidedMcpServers
// ──────────────────────────────────────────────────────────

describe('detectExternallyProvidedMcpServers', () => {
    it('detects MCP providers by contributed labels', () => {
        const result = detectExternallyProvidedMcpServers([
            {
                id: 'someone.pubmed-extension',
                packageJSON: {
                    contributes: {
                        mcpServerDefinitionProviders: [
                            { id: 'pubmed-search', label: 'PubMed Search' },
                        ],
                    },
                },
            },
            {
                id: 'someone.zotero-extension',
                packageJSON: {
                    contributes: {
                        mcpServerDefinitionProviders: [
                            { id: 'zotero-keeper', label: 'Zotero Keeper' },
                        ],
                    },
                },
            },
        ]);

        expect(result).toEqual({ pubmed: true, zotero: true });
    });

    it('falls back to extension metadata when provider labels are absent', () => {
        const result = detectExternallyProvidedMcpServers([
            {
                id: 'publisher.pubmed-search-mcp',
                packageJSON: {
                    name: 'pubmed-search-mcp',
                    displayName: 'PubMed Search MCP',
                },
            },
            {
                id: 'publisher.zotero-tools',
                packageJSON: {
                    name: 'some-zotero-helper',
                    description: 'Integrates Zotero Keeper tools into VS Code',
                },
            },
        ]);

        expect(result).toEqual({ pubmed: true, zotero: true });
    });

    it('ignores the current MedPaper extension itself', () => {
        const result = detectExternallyProvidedMcpServers([
            {
                id: 'u9401066.medpaper-assistant',
                packageJSON: {
                    contributes: {
                        mcpServerDefinitionProviders: [
                            { id: 'pubmed-search', label: 'PubMed Search' },
                            { id: 'zotero-keeper', label: 'Zotero Keeper' },
                        ],
                    },
                },
            },
        ], 'u9401066.medpaper-assistant');

        expect(result).toEqual({ pubmed: false, zotero: false });
    });

    it('returns false when unrelated extensions are installed', () => {
        const result = detectExternallyProvidedMcpServers([
            {
                id: 'someone.random-extension',
                packageJSON: {
                    name: 'random-tools',
                    displayName: 'Random Tools',
                },
            },
        ]);

        expect(result).toEqual({ pubmed: false, zotero: false });
    });
});

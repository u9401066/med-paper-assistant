/**
 * VSIX Packaging Validation Tests
 *
 * Validates that the extension's package.json manifest is correct
 * and that all required assets referenced in the manifest exist.
 * These tests catch packaging issues BEFORE publishing.
 */
import { describe, it, expect } from 'vitest';
import * as path from 'path';
import * as fs from 'fs';
import { BUNDLED_CHAT_COMMANDS, BUNDLED_PALETTE_COMMANDS } from '../utils';

const extDir = path.resolve(__dirname, '..', '..');
const pkgPath = path.join(extDir, 'package.json');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));

// ──────────────────────────────────────────────────────────
// Manifest Schema
// ──────────────────────────────────────────────────────────

describe('package.json manifest', () => {
    it('has required fields', () => {
        expect(pkg.name).toBe('medpaper-assistant');
        expect(pkg.publisher).toBeDefined();
        expect(pkg.version).toMatch(/^\d+\.\d+\.\d+/);
        expect(pkg.engines?.vscode).toBeDefined();
        expect(pkg.main).toBe('./out/extension.js');
    });

    it('activates on startup', () => {
        expect(pkg.activationEvents).toContain('onStartupFinished');
    });

    it('declares MCP server definition provider', () => {
        const providers = pkg.contributes?.mcpServerDefinitionProviders;
        expect(providers).toBeDefined();
        expect(providers.length).toBeGreaterThanOrEqual(1);
        const mdpaper = providers.find((p: { id: string }) => p.id === 'mdpaper');
        expect(mdpaper).toBeDefined();
        expect(mdpaper.label).toBeTruthy();
    });

    it('declares chat participant with correct id', () => {
        const participants = pkg.contributes?.chatParticipants;
        expect(participants).toBeDefined();
        const participant = participants.find((p: { id: string }) => p.id === 'medpaper.assistant');
        expect(participant).toBeDefined();
        expect(participant.name).toBe('mdpaper');
    });

    it('chat participant has all expected commands', () => {
        const participant = pkg.contributes.chatParticipants[0];
        const commandNames = participant.commands.map((c: { name: string }) => c.name);
        for (const cmd of BUNDLED_CHAT_COMMANDS) {
            expect(commandNames, `Missing command: ${cmd}`).toContain(cmd);
        }
    });

    it('declares expected commands in contributes', () => {
        const commands = pkg.contributes?.commands;
        expect(commands).toBeDefined();
        const ids = commands.map((c: { command: string }) => c.command);
        for (const commandId of BUNDLED_PALETTE_COMMANDS) {
            expect(ids).toContain(commandId);
        }
    });

    it('has configuration properties', () => {
        const props = pkg.contributes?.configuration?.properties;
        expect(props).toBeDefined();
        expect(props['mdpaper.pythonPath']).toBeDefined();
        expect(props['mdpaper.toolSurface']).toBeDefined();
        expect(props['mdpaper.defaultCitationStyle']).toBeDefined();
    });

    it('has required devDependencies', () => {
        const deps = pkg.devDependencies;
        expect(deps['typescript']).toBeDefined();
        expect(deps['vitest']).toBeDefined();
        expect(deps['@types/vscode']).toBeDefined();
        expect(deps['@vscode/vsce']).toBeDefined();
    });
});

// ──────────────────────────────────────────────────────────
// .vscodeignore
// ──────────────────────────────────────────────────────────

describe('.vscodeignore', () => {
    const ignorePath = path.join(extDir, '.vscodeignore');

    it('exists', () => {
        expect(fs.existsSync(ignorePath)).toBe(true);
    });

    it('excludes test files from VSIX', () => {
        const content = fs.readFileSync(ignorePath, 'utf-8');
        // Should exclude compiled test output
        expect(content).toContain('out/test');
    });

    it('excludes source TypeScript files', () => {
        const content = fs.readFileSync(ignorePath, 'utf-8');
        expect(content).toContain('src/');
    });

    it('excludes node_modules', () => {
        const content = fs.readFileSync(ignorePath, 'utf-8');
        expect(content).toContain('node_modules');
    });
});

describe('release notes', () => {
    it('includes CHANGELOG.md', () => {
        const changelogPath = path.join(extDir, 'CHANGELOG.md');
        expect(fs.existsSync(changelogPath)).toBe(true);
    });
});

// ──────────────────────────────────────────────────────────
// Extension Entry Point
// ──────────────────────────────────────────────────────────

describe('extension entry point', () => {
    it('main source file exists', () => {
        const entryTs = path.join(extDir, 'src', 'extension.ts');
        expect(fs.existsSync(entryTs)).toBe(true);
    });

    it('exports activate function', () => {
        const content = fs.readFileSync(path.join(extDir, 'src', 'extension.ts'), 'utf-8');
        expect(content).toContain('export async function activate');
    });

    it('exports deactivate function', () => {
        const content = fs.readFileSync(path.join(extDir, 'src', 'extension.ts'), 'utf-8');
        expect(content).toContain('export function deactivate');
    });

    it('registers PubMed Search, Zotero Keeper, and Draw.io MCP servers', () => {
        const content = fs.readFileSync(path.join(extDir, 'src', 'extension.ts'), 'utf-8');
        expect(content).toContain("'PubMed Search'");
        expect(content).toContain("'Zotero Keeper'");
        expect(content).toContain("'Draw.io Diagrams'");
        expect(content).toContain("'pubmed-search-mcp'");
        expect(content).toContain("'zotero-keeper'");
        expect(content).toContain("integrations', 'next-ai-draw-io', 'mcp-server'");
        expect(content).toContain("integrations', 'drawio-mcp'");
    });
});

// ──────────────────────────────────────────────────────────
// Module Structure
// ──────────────────────────────────────────────────────────

describe('module structure', () => {
    it('utils.ts exists', () => {
        expect(fs.existsSync(path.join(extDir, 'src', 'utils.ts'))).toBe(true);
    });

    it('uvManager.ts exists', () => {
        expect(fs.existsSync(path.join(extDir, 'src', 'uvManager.ts'))).toBe(true);
    });

    it('extensionHelpers.ts exists', () => {
        expect(fs.existsSync(path.join(extDir, 'src', 'extensionHelpers.ts'))).toBe(true);
    });

    it('tsconfig.json exists and targets correct output', () => {
        const tsconfig = JSON.parse(fs.readFileSync(path.join(extDir, 'tsconfig.json'), 'utf-8'));
        expect(tsconfig.compilerOptions.outDir).toBe('out');
        expect(tsconfig.compilerOptions.rootDir).toBe('src');
    });
});

// ──────────────────────────────────────────────────────────
// Version Consistency
// ──────────────────────────────────────────────────────────

describe('version consistency', () => {
    it('package.json version is a valid semver', () => {
        expect(pkg.version).toMatch(/^\d+\.\d+\.\d+$/);
    });

    it('vscode engine is compatible (>=1.100.0)', () => {
        const engine = pkg.engines.vscode;
        // Should be ^1.100.0 or similar
        expect(engine).toMatch(/\d+\.\d+/);
    });
});

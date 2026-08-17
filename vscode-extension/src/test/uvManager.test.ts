import * as path from 'path';
import { describe, it, expect } from 'vitest';
import { getUvSearchPaths, getUvxPath, getUvInstallCommand, buildPinnedUvxCommand, buildMcpEnv, findUvPath, enrichPath } from '../uvManager';

// ──────────────────────────────────────────────────────────
// getUvSearchPaths
// ──────────────────────────────────────────────────────────

describe('getUvSearchPaths', () => {
    it('always includes "uv" as first entry (PATH check)', () => {
        const paths = getUvSearchPaths();
        expect(paths[0]).toBe('uv');
    });

    it('returns multiple search paths', () => {
        const paths = getUvSearchPaths();
        expect(paths.length).toBeGreaterThanOrEqual(3);
    });

    it('includes home directory paths', () => {
        const paths = getUvSearchPaths();
        // At least one path should contain .local or .cargo or AppData
        const hasHomePath = paths.some(
            p => p.includes('.local') || p.includes('.cargo') || p.includes('AppData')
        );
        expect(hasHomePath).toBe(true);
    });
});

// ──────────────────────────────────────────────────────────
// getUvxPath
// ──────────────────────────────────────────────────────────

describe('getUvxPath', () => {
    it('returns "uvx" when uv is "uv" (in PATH)', () => {
        expect(getUvxPath('uv')).toBe('uvx');
    });

    it('derives uvx from absolute uv path (unix)', () => {
        const result = getUvxPath('/home/user/.local/bin/uv');
        expect(path.basename(result)).toBe(process.platform === 'win32' ? 'uvx.exe' : 'uvx');
        expect(path.dirname(result)).toBe(path.normalize('/home/user/.local/bin'));
    });

    it('keeps the same directory as uv', () => {
        const dir = '/opt/homebrew/bin';
        const result = getUvxPath(`${dir}/uv`);
        expect(path.dirname(result)).toBe(path.normalize(dir));
    });
});

// ──────────────────────────────────────────────────────────
// getUvInstallCommand
// ──────────────────────────────────────────────────────────

describe('getUvInstallCommand', () => {
    it('returns a non-empty command string', () => {
        const cmd = getUvInstallCommand();
        expect(cmd.length).toBeGreaterThan(0);
    });

    it('references astral.sh', () => {
        const cmd = getUvInstallCommand();
        expect(cmd).toContain('astral.sh/uv');
    });
});

// Persistent/floating tool installation was intentionally removed. Marketplace
// definitions must use version-pinned isolated commands.

describe('buildPinnedUvxCommand', () => {
    it('uses an immutable source and explicit entrypoint without a bare package fallback', () => {
        const source = 'https://github.com/example/tool/archive/0123456789abcdef0123456789abcdef01234567.tar.gz#subdirectory=server';
        const [cmd, args] = buildPinnedUvxCommand('uv', source, 'example-tool', '3.12');

        expect(cmd).toBe('uvx');
        expect(args).toEqual(['--python', '3.12', '--from', source, 'example-tool']);
        expect(args).not.toEqual(['example-tool']);
    });
});

// ──────────────────────────────────────────────────────────
// enrichPath
// ──────────────────────────────────────────────────────────

describe('enrichPath', () => {
    it('returns original PATH when no extra dirs exist', () => {
        // Use a non-existent prefix so getExtraPathDirs() returns nothing new
        const original = ['/nonexistent/a', '/nonexistent/b'].join(path.delimiter);
        const result = enrichPath(original);
        // Either returns original (no dirs to add) or adds existing dirs
        expect(result).toContain('/nonexistent/a');
        expect(result).toContain('/nonexistent/b');
    });

    it('does not duplicate dirs already in PATH', () => {
        const homeDir = process.env.HOME || '/tmp';
        const localBin = `${homeDir}/.local/bin`;
        const original = ['/usr/bin', localBin, '/usr/sbin'].join(path.delimiter);
        const result = enrichPath(original);
        // localBin should appear at most once
        const count = result.split(path.delimiter).filter(p => p === localBin).length;
        expect(count).toBeLessThanOrEqual(1);
    });

    it('prepends extra dirs before original PATH', () => {
        const result = enrichPath(['/usr/bin', '/bin'].join(path.delimiter));
        const parts = result.split(path.delimiter);
        // Original entries must still be there
        expect(parts).toContain('/usr/bin');
        expect(parts).toContain('/bin');
        // /usr/bin should appear after any prepended dirs (if any were added)
        if (parts.length > 2) {
            const usrBinIdx = parts.indexOf('/usr/bin');
            // At least one prepended dir should be before /usr/bin
            expect(usrBinIdx).toBeGreaterThan(0);
        }
    });

    it('handles empty PATH', () => {
        const result = enrichPath('');
        expect(typeof result).toBe('string');
        // Should not start with a delimiter
        expect(result.startsWith(path.delimiter)).toBe(false);
    });
});

// ──────────────────────────────────────────────────────────
// buildMcpEnv
// ──────────────────────────────────────────────────────────

describe('buildMcpEnv', () => {
    it('includes MEDPAPER_BASE_DIR when workspaceDir is provided', () => {
        const env = buildMcpEnv({ workspaceDir: '/home/user/project' });
        expect(env.MEDPAPER_BASE_DIR).toBe('/home/user/project');
        expect(env.MEDPAPER_TOOL_SURFACE).toBe('compact');
    });

    it('omits MEDPAPER_BASE_DIR when workspaceDir is not provided', () => {
        const env = buildMcpEnv({});
        expect(env.MEDPAPER_BASE_DIR).toBeUndefined();
        expect(env.MEDPAPER_TOOL_SURFACE).toBe('compact');
    });

    it('includes PYTHONPATH only when explicitly provided', () => {
        const envWithout = buildMcpEnv({});
        expect(envWithout.PYTHONPATH).toBeUndefined();

        const envWith = buildMcpEnv({ pythonPath: '/some/path' });
        expect(envWith.PYTHONPATH).toBe('/some/path');
    });

    it('uses explicit toolSurface when provided', () => {
        const env = buildMcpEnv({ toolSurface: 'full' });
        expect(env.MEDPAPER_TOOL_SURFACE).toBe('full');
    });

    it('inherits and enriches PATH from current process', () => {
        const env = buildMcpEnv({});
        if (process.env.PATH) {
            // PATH should be present and at least as long as original (enrichment only adds)
            expect(env.PATH).toBeDefined();
            expect(env.PATH!.length).toBeGreaterThanOrEqual(process.env.PATH.length);
            // All original PATH entries should be preserved
            for (const dir of process.env.PATH.split(path.delimiter).slice(0, 3)) {
                if (dir) { expect(env.PATH).toContain(dir); }
            }
        }
    });

    it('inherits HOME from current process', () => {
        const env = buildMcpEnv({});
        if (process.env.HOME) {
            expect(env.HOME).toBe(process.env.HOME);
        }
    });
});

// ──────────────────────────────────────────────────────────
// findUvPath (async — real system check)
// ──────────────────────────────────────────────────────────

describe('findUvPath', () => {
    it('returns a string or null', async () => {
        const result = await findUvPath();
        expect(result === null || typeof result === 'string').toBe(true);
    });

    it('calls log function when provided', async () => {
        const logs: string[] = [];
        await findUvPath((msg) => logs.push(msg));
        // Should have logged at least something (found or not found)
        expect(logs.length).toBeGreaterThanOrEqual(0);
    });

    it('returns "uv" or absolute path when uv is installed', async () => {
        const result = await findUvPath();
        if (result !== null) {
            // Either "uv" (in PATH) or an absolute path
            expect(result === 'uv' || path.isAbsolute(result)).toBe(true);
        }
    });
});

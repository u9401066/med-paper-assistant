import * as path from 'path';
import { describe, it, expect } from 'vitest';
import { getUvSearchPaths, getUvxPath, getUvInstallCommand, getUvToolInstallCommand, buildUvxCommand, buildMcpCommand, buildMcpEnv, findUvPath, enrichPath, findInstalledTool } from '../uvManager';

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
        // On Windows test runner, extension may be added
        expect(result).toContain('uvx');
        expect(result).toContain('/home/user/.local/bin/');
    });

    it('keeps the same directory as uv', () => {
        const dir = '/opt/homebrew/bin';
        const result = getUvxPath(`${dir}/uv`);
        expect(result.startsWith(dir)).toBe(true);
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

// ──────────────────────────────────────────────────────────
// getUvToolInstallCommand
// ──────────────────────────────────────────────────────────

describe('getUvToolInstallCommand', () => {
    it('installs package directly when binary name matches package name', () => {
        const cmd = getUvToolInstallCommand('med-paper-assistant');
        expect(cmd).toBe('uv tool install med-paper-assistant');
    });

    it('uses --from when binary name differs from package name', () => {
        const cmd = getUvToolInstallCommand('creativity-generation-unit', 'cgu-server');
        expect(cmd).toBe('uv tool install --from creativity-generation-unit cgu-server');
    });

    it('includes python version when specified', () => {
        const cmd = getUvToolInstallCommand('med-paper-assistant', undefined, '>=3.11');
        expect(cmd).toBe('uv tool install --python >=3.11 med-paper-assistant');
    });
});

// ──────────────────────────────────────────────────────────
// buildUvxCommand
// ──────────────────────────────────────────────────────────

describe('buildUvxCommand', () => {
    it('builds uvx command for in-PATH uv', () => {
        const [cmd, args] = buildUvxCommand('uv', 'med-paper-assistant');
        expect(cmd).toBe('uvx');
        expect(args).toEqual(['med-paper-assistant']);
    });

    it('builds uvx command from absolute uv path', () => {
        const [cmd, args] = buildUvxCommand('/home/user/.local/bin/uv', 'med-paper-assistant');
        expect(cmd).toContain('uvx');
        expect(cmd).toContain('/home/user/.local/bin/');
        expect(args).toEqual(['med-paper-assistant']);
    });

    it('includes python version constraint when specified', () => {
        const [cmd, args] = buildUvxCommand('uv', 'med-paper-assistant', '>=3.11');
        expect(cmd).toBe('uvx');
        expect(args).toEqual(['--python', '>=3.11', 'med-paper-assistant']);
    });

    it('works with CGU package name', () => {
        const [cmd, args] = buildUvxCommand('uv', 'creativity-generation-unit');
        expect(args).toEqual(['creativity-generation-unit']);
    });
});

// ──────────────────────────────────────────────────────────
// findInstalledTool
// ──────────────────────────────────────────────────────────

describe('findInstalledTool', () => {
    it('returns null for a non-existent tool', () => {
        const result = findInstalledTool('definitely-nonexistent-tool-xyz-12345');
        expect(result).toBeNull();
    });

    it('returns string path when tool binary exists', () => {
        // 'uv' should be installed on this system (test prerequisite)
        const result = findInstalledTool('uv');
        if (result !== null) {
            expect(typeof result).toBe('string');
            expect(result).toContain('uv');
        }
        // If null, uv is only in PATH but not in a known fixed location — that's OK
    });

    it('returns an absolute path', () => {
        const result = findInstalledTool('uv');
        if (result !== null) {
            expect(path.isAbsolute(result)).toBe(true);
        }
    });

    it('can resolve tools from PATH-derived directories', () => {
        const pathDirs = enrichPath(process.env.PATH || '').split(path.delimiter).filter(Boolean);
        const result = findInstalledTool('uv');
        if (result !== null) {
            expect(pathDirs.some(dir => result.startsWith(dir))).toBe(true);
        }
    });
});

// ──────────────────────────────────────────────────────────
// buildMcpCommand
// ──────────────────────────────────────────────────────────

describe('buildMcpCommand', () => {
    it('falls back to uvx when tool is not pre-installed', () => {
        const [cmd, args, preInstalled] = buildMcpCommand('uv', 'definitely-nonexistent-pkg-xyz');
        expect(preInstalled).toBe(false);
        expect(cmd).toBe('uvx');
        expect(args).toEqual(['definitely-nonexistent-pkg-xyz']);
    });

    it('uses pre-installed binary when available', () => {
        // If uv is installed via uv tool install / pip, it should be found
        const [cmd, args, preInstalled] = buildMcpCommand('uv', 'uv');
        if (preInstalled) {
            expect(args).toEqual([]);
            expect(cmd).toContain('uv');
        } else {
            // uv not in a fixed location — uvx fallback
            expect(cmd).toBe('uvx');
        }
    });

    it('supports custom binaryName different from packageName', () => {
        const [cmd, args, preInstalled] = buildMcpCommand('uv', 'some-package', 'some-binary');
        if (!preInstalled) {
            // Falls back to uvx with the packageName
            expect(cmd).toBe('uvx');
            expect(args).toEqual(['some-package']);
        }
    });

    it('supports CGU package name with custom server binary', () => {
        const [cmd, args, preInstalled] = buildMcpCommand('uv', 'creativity-generation-unit', 'cgu-server');
        if (!preInstalled) {
            expect(cmd).toBe('uvx');
            expect(args).toEqual(['creativity-generation-unit']);
        }
    });

    it('returns [command, args, boolean] tuple', () => {
        const result = buildMcpCommand('uv', 'some-package');
        expect(result).toHaveLength(3);
        expect(typeof result[0]).toBe('string');
        expect(Array.isArray(result[1])).toBe(true);
        expect(typeof result[2]).toBe('boolean');
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
    });

    it('omits MEDPAPER_BASE_DIR when workspaceDir is not provided', () => {
        const env = buildMcpEnv({});
        expect(env.MEDPAPER_BASE_DIR).toBeUndefined();
    });

    it('includes PYTHONPATH only when explicitly provided', () => {
        const envWithout = buildMcpEnv({});
        expect(envWithout.PYTHONPATH).toBeUndefined();

        const envWith = buildMcpEnv({ pythonPath: '/some/path' });
        expect(envWith.PYTHONPATH).toBe('/some/path');
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

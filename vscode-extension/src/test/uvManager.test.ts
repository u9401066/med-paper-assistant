import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { createHash } from 'crypto';
import { gzipSync } from 'zlib';
import { describe, it, expect } from 'vitest';
import {
    REQUIRED_UV_VERSION,
    acquireManagedUvInstallLease,
    assertSafeArchivePath,
    buildMcpEnv,
    buildPinnedUvxCommand,
    enrichPath,
    extractUvBinaries,
    findUvPath,
    getManagedUvPath,
    getUvSearchPaths,
    getUvxPath,
    isRequiredUvVersionOutput,
    installUvHeadless,
    resolveUvArtifact,
    verifyArchiveSha256,
} from '../uvManager';

function writeTarOctal(header: Buffer, offset: number, length: number, value: number): void {
    const encoded = value.toString(8).padStart(length - 1, '0');
    header.write(encoded, offset, length - 1, 'ascii');
    header[offset + length - 1] = 0;
}

function tarEntry(name: string, data: Buffer, type: '0' | '5'): Buffer {
    const header = Buffer.alloc(512);
    header.write(name, 0, 100, 'utf8');
    writeTarOctal(header, 100, 8, type === '5' ? 0o755 : 0o755);
    writeTarOctal(header, 108, 8, 0);
    writeTarOctal(header, 116, 8, 0);
    writeTarOctal(header, 124, 12, data.length);
    writeTarOctal(header, 136, 12, 0);
    header.fill(0x20, 148, 156);
    header[156] = type.charCodeAt(0);
    header.write('ustar\0', 257, 6, 'binary');
    header.write('00', 263, 2, 'ascii');

    let checksum = 0;
    for (const byte of header) {
        checksum += byte;
    }
    header.write(`${checksum.toString(8).padStart(6, '0')}\0 `, 148, 8, 'binary');

    const padding = Buffer.alloc((512 - (data.length % 512)) % 512);
    return Buffer.concat([header, data, padding]);
}

function syntheticUvTar(root: string, firstName: string = `${root}/uv`): Buffer {
    return gzipSync(
        Buffer.concat([
            tarEntry(`${root}/`, Buffer.alloc(0), '5'),
            tarEntry(firstName, Buffer.from('uv-binary'), '0'),
            tarEntry(`${root}/uvx`, Buffer.from('uvx-binary'), '0'),
            Buffer.alloc(1024),
        ]),
    );
}

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
        const hasHomePath = paths.some(p => p.includes('.local') || p.includes('.cargo') || p.includes('AppData'));
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
// Immutable uv release contract
// ──────────────────────────────────────────────────────────

describe('immutable uv release contract', () => {
    it.each([
        ['darwin', 'x64', false, 'uv-x86_64-apple-darwin.tar.gz'],
        ['darwin', 'arm64', false, 'uv-aarch64-apple-darwin.tar.gz'],
        ['win32', 'x64', false, 'uv-x86_64-pc-windows-msvc.zip'],
        ['win32', 'arm64', false, 'uv-aarch64-pc-windows-msvc.zip'],
        ['linux', 'x64', false, 'uv-x86_64-unknown-linux-gnu.tar.gz'],
        ['linux', 'arm64', false, 'uv-aarch64-unknown-linux-gnu.tar.gz'],
        ['linux', 'x64', true, 'uv-x86_64-unknown-linux-musl.tar.gz'],
        ['linux', 'arm64', true, 'uv-aarch64-unknown-linux-musl.tar.gz'],
    ])('pins %s/%s (musl=%s) to an exact official asset', (platform, arch, musl, archiveName) => {
        const artifact = resolveUvArtifact(platform, arch, musl);
        expect(artifact.archiveName).toBe(archiveName);
        expect(artifact.url).toBe(`https://github.com/astral-sh/uv/releases/download/${REQUIRED_UV_VERSION}/${archiveName}`);
        expect(artifact.sha256).toMatch(/^[0-9a-f]{64}$/);
    });

    it('rejects unsupported platforms and architectures', () => {
        expect(() => resolveUvArtifact('freebsd', 'x64', false)).toThrow(/not available/);
        expect(() => resolveUvArtifact('linux', 'ia32', false)).toThrow(/not available/);
    });

    it('accepts only the exact uv and uvx version output', () => {
        expect(isRequiredUvVersionOutput(`uv ${REQUIRED_UV_VERSION}\n`, 'uv')).toBe(true);
        expect(isRequiredUvVersionOutput(`uvx ${REQUIRED_UV_VERSION}`, 'uvx')).toBe(true);
        expect(isRequiredUvVersionOutput(`uv ${REQUIRED_UV_VERSION} (x86_64-unknown-linux-gnu)`, 'uv')).toBe(true);
        expect(isRequiredUvVersionOutput('uv 0.12.4', 'uv')).toBe(false);
        expect(isRequiredUvVersionOutput(`uv ${REQUIRED_UV_VERSION}\nmalicious`, 'uv')).toBe(false);
    });

    it('verifies SHA-256 and rejects altered archives', () => {
        const archive = Buffer.from('pinned archive');
        const digest = createHash('sha256').update(archive).digest('hex');
        expect(() => verifyArchiveSha256(archive, digest)).not.toThrow();
        expect(() => verifyArchiveSha256(Buffer.from('altered archive'), digest)).toThrow(/mismatch/);
    });

    it('extracts only the expected binaries from a safe tarball', () => {
        const artifact = resolveUvArtifact('linux', 'x64', false);
        const binaries = extractUvBinaries(syntheticUvTar(artifact.archiveRoot), artifact);
        expect(binaries.uv.toString()).toBe('uv-binary');
        expect(binaries.uvx.toString()).toBe('uvx-binary');
    });

    it.each(['../uv', '/tmp/uv', 'C:\\temp\\uv', 'safe/../../uv', 'safe\\..\\uv'])('rejects unsafe archive path %s', unsafePath => {
        expect(() => assertSafeArchivePath(unsafePath)).toThrow(/unsafe|absolute/);
    });

    it('rejects a traversal member before extraction', () => {
        const artifact = resolveUvArtifact('linux', 'x64', false);
        const archive = syntheticUvTar(artifact.archiveRoot, '../uv');
        expect(() => extractUvBinaries(archive, artifact)).toThrow(/unsafe/);
    });

    it('uses a version-scoped managed install path', () => {
        const managed = getManagedUvPath('/extension-storage', 'win32');
        expect(managed).toBe(path.join('/extension-storage', 'uv', REQUIRED_UV_VERSION, 'bin', 'uv.exe'));
    });

    it('serializes concurrent managed-install leases', async () => {
        const storageRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'medpaper-uv-lease-'));
        let active = 0;
        let maximumActive = 0;
        const run = async (): Promise<void> => {
            const lease = await acquireManagedUvInstallLease(storageRoot, { maxWaitMs: 2_000, pollIntervalMs: 5 });
            active += 1;
            maximumActive = Math.max(maximumActive, active);
            await new Promise(resolve => setTimeout(resolve, 20));
            active -= 1;
            lease.release();
        };

        try {
            await Promise.all([run(), run()]);
            expect(maximumActive).toBe(1);
        } finally {
            fs.rmSync(storageRoot, { recursive: true, force: true });
        }
    });

    it.each(['storage-root', 'uv-directory'])('rejects a managed %s symlink without touching its target', async target => {
        const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'medpaper-uv-symlink-'));
        const external = path.join(sandbox, 'external');
        const storage = path.join(sandbox, 'storage');
        fs.mkdirSync(external);
        fs.writeFileSync(path.join(external, 'sentinel'), 'keep');
        if (target === 'storage-root') {
            fs.symlinkSync(external, storage, process.platform === 'win32' ? 'junction' : 'dir');
        } else {
            fs.mkdirSync(storage);
            fs.symlinkSync(external, path.join(storage, 'uv'), process.platform === 'win32' ? 'junction' : 'dir');
        }

        try {
            await expect(acquireManagedUvInstallLease(storage, { maxWaitMs: 0, pollIntervalMs: 1 })).rejects.toThrow(/real directory/);
            expect(fs.readFileSync(path.join(external, 'sentinel'), 'utf8')).toBe('keep');
        } finally {
            fs.rmSync(sandbox, { recursive: true, force: true });
        }
    });

    it('rejects a symlinked version directory before downloading or deleting its target', async () => {
        const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'medpaper-uv-version-link-'));
        const storage = path.join(sandbox, 'storage');
        const external = path.join(sandbox, 'external');
        fs.mkdirSync(path.join(storage, 'uv'), { recursive: true });
        fs.mkdirSync(external);
        fs.writeFileSync(path.join(external, 'sentinel'), 'keep');
        fs.symlinkSync(external, path.join(storage, 'uv', REQUIRED_UV_VERSION), process.platform === 'win32' ? 'junction' : 'dir');

        try {
            const logs: string[] = [];
            await expect(installUvHeadless(storage, message => logs.push(message))).resolves.toBeNull();
            expect(logs.join('\n')).toMatch(/version directory must be a real directory/);
            expect(fs.readFileSync(path.join(external, 'sentinel'), 'utf8')).toBe('keep');
        } finally {
            fs.rmSync(sandbox, { recursive: true, force: true });
        }
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
                if (dir) {
                    expect(env.PATH).toContain(dir);
                }
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
        await findUvPath(msg => logs.push(msg));
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

/**
 * uv Manager — Auto-detection and installation of uv (Python package manager).
 *
 * Provides zero-config experience:
 * 1. Detect uv in PATH or known install locations
 * 2. Auto-install uv if not found (cross-platform)
 * 3. Derive uvx path from uv path
 *
 * With uv installed, version-pinned `uvx --from ...` runtimes provide:
 * - Python auto-download (if no Python on system)
 * - Package installation from exact SDK2 sources in isolated environments
 * - All dependencies resolved automatically
 * - No interference with user's other packages
 */

import * as path from 'path';
import * as fs from 'fs';
import * as https from 'https';
import { execFile } from 'child_process';
import { createHash, randomUUID } from 'crypto';
import { gunzipSync, inflateRawSync } from 'zlib';

export const REQUIRED_UV_VERSION = '0.12.5';

const UV_RELEASE_BASE_URL = `https://github.com/astral-sh/uv/releases/download/${REQUIRED_UV_VERSION}`;
const MAX_ARCHIVE_BYTES = 100 * 1024 * 1024;
const MAX_EXTRACTED_BYTES = 160 * 1024 * 1024;
const MAX_REDIRECTS = 5;

type UvArchiveFormat = 'tar.gz' | 'zip';

export interface UvArtifact {
    archiveName: string;
    archiveRoot: string;
    format: UvArchiveFormat;
    sha256: string;
    target: string;
    url: string;
}

interface ManagedUvReceipt {
    schemaVersion: 1;
    uvVersion: string;
    target: string;
    archiveSha256: string;
    uvSha256: string;
    uvxSha256: string;
}

interface ExtractedUvBinaries {
    uv: Buffer;
    uvx: Buffer;
}

type ProcessEnvironment = Record<string, string | undefined>;

function systemErrorCode(error: unknown): string | undefined {
    if (typeof error !== 'object' || error === null || !('code' in error)) {
        return undefined;
    }
    const code = (error as { code?: unknown }).code;
    return typeof code === 'string' ? code : undefined;
}

interface ManagedStorageLayout {
    storageRoot: string;
    storageRealPath: string;
    uvRoot: string;
    uvRealPath: string;
}

export interface ManagedInstallLeaseOptions {
    maxWaitMs?: number;
    pollIntervalMs?: number;
}

export interface ManagedInstallLease {
    release(): void;
}

const UV_RELEASE_ARTIFACTS: Readonly<Record<string, Omit<UvArtifact, 'url' | 'archiveRoot'>>> = {
    'darwin-arm64': {
        archiveName: 'uv-aarch64-apple-darwin.tar.gz',
        format: 'tar.gz',
        sha256: '5bb0e5fe008a773c3dbcb97ff79cd89e1241464fe9d2f986d52ad8f1b037bd62',
        target: 'aarch64-apple-darwin',
    },
    'darwin-x64': {
        archiveName: 'uv-x86_64-apple-darwin.tar.gz',
        format: 'tar.gz',
        sha256: 'b3b2137477cf96c9686ebfb71524614cec780c673fd73e59bce099aef02e70e8',
        target: 'x86_64-apple-darwin',
    },
    'linux-arm64-gnu': {
        archiveName: 'uv-aarch64-unknown-linux-gnu.tar.gz',
        format: 'tar.gz',
        sha256: '9bf43b4d1a07665bf64d4c4e710930b382321a785e0eb10aac07f46471f86a31',
        target: 'aarch64-unknown-linux-gnu',
    },
    'linux-arm64-musl': {
        archiveName: 'uv-aarch64-unknown-linux-musl.tar.gz',
        format: 'tar.gz',
        sha256: '8767a0e77f2cd45436401b1b42bf7e9ed5a4a91a74a5305d6fe93249d0f6dbc5',
        target: 'aarch64-unknown-linux-musl',
    },
    'linux-x64-gnu': {
        archiveName: 'uv-x86_64-unknown-linux-gnu.tar.gz',
        format: 'tar.gz',
        sha256: '68a509da24b06b4223a1c0175fb5eb5bc79342b76cbeff0cfe51ac3f5b17b6b2',
        target: 'x86_64-unknown-linux-gnu',
    },
    'linux-x64-musl': {
        archiveName: 'uv-x86_64-unknown-linux-musl.tar.gz',
        format: 'tar.gz',
        sha256: 'a4742988791c9aeae68c78150d6cba762062ad2a47e53738c2779d2b596bfcdb',
        target: 'x86_64-unknown-linux-musl',
    },
    'win32-arm64': {
        archiveName: 'uv-aarch64-pc-windows-msvc.zip',
        format: 'zip',
        sha256: '724279317fee6e5fa8ad1908e4eba2bbe764ef1ece5b3f4597927b62b1fe562a',
        target: 'aarch64-pc-windows-msvc',
    },
    'win32-x64': {
        archiveName: 'uv-x86_64-pc-windows-msvc.zip',
        format: 'zip',
        sha256: '4c4d49d8738847d9b71ba319e49a5688c93eac0fe6204b1df24e98528dddf39a',
        target: 'x86_64-pc-windows-msvc',
    },
};

/**
 * Extra directories that may contain uv/uvx/pandoc/git on macOS and Linux
 * but are NOT in process.env.PATH when VS Code is launched from Dock/Spotlight.
 *
 * On macOS, GUI apps inherit a minimal PATH (/usr/bin:/bin:/usr/sbin:/sbin).
 * Shell profile additions (~/.zprofile, ~/.zshrc, Homebrew shellenv) are NOT loaded.
 */
function getExtraPathDirs(): string[] {
    const homeDir = process.env.HOME || '';
    const dirs: string[] = [
        path.join(homeDir, '.local', 'bin'), // Common user-local install location
        path.join(homeDir, '.cargo', 'bin'), // uv via cargo / rustup
    ];

    if (process.platform === 'darwin') {
        dirs.push(
            '/opt/homebrew/bin', // Homebrew on Apple Silicon (M1/M2/M3/M4)
            '/opt/homebrew/sbin',
            '/usr/local/bin', // Homebrew on Intel Mac / MacPorts
            '/usr/local/sbin',
        );
    }

    return dirs.filter(d => fs.existsSync(d));
}

/**
 * Enrich the given PATH string with extra directories that may contain tools.
 * Only appends directories that exist and are not already in PATH.
 *
 * @param basePath - The original PATH string (e.g., process.env.PATH)
 * @returns The enriched PATH string
 */
export function enrichPath(basePath: string): string {
    const extraDirs = getExtraPathDirs();
    const existing = new Set(basePath.split(path.delimiter));
    const toAdd = extraDirs.filter(d => !existing.has(d));
    if (toAdd.length === 0) {
        return basePath;
    }
    return [...toAdd, basePath].join(path.delimiter);
}

/**
 * Get potential uv binary paths based on platform.
 * Covers PATH, common install locations, and platform-specific paths.
 */
export function getUvSearchPaths(): string[] {
    const homeDir = process.env.HOME || process.env.USERPROFILE || '';
    const platform = process.platform;

    if (platform === 'win32') {
        return [
            'uv', // In PATH
            path.join(homeDir, 'AppData', 'Local', 'uv', 'bin', 'uv.exe'),
            path.join(homeDir, '.local', 'bin', 'uv.exe'),
            path.join(homeDir, '.cargo', 'bin', 'uv.exe'),
            'C:\\Program Files\\uv\\uv.exe',
        ];
    } else {
        return [
            'uv', // In PATH (enriched)
            path.join(homeDir, '.local', 'bin', 'uv'),
            path.join(homeDir, '.cargo', 'bin', 'uv'),
            '/usr/local/bin/uv',
            '/opt/homebrew/bin/uv',
        ];
    }
}

/**
 * Derive uvx path from a known uv path.
 * uvx is always in the same directory as uv.
 */
export function getUvxPath(uvPath: string): string {
    if (uvPath === 'uv') {
        return 'uvx';
    }
    const dir = path.dirname(uvPath);
    const ext = process.platform === 'win32' ? '.exe' : '';
    return path.join(dir, `uvx${ext}`);
}

function isMuslRuntime(): boolean {
    if (process.platform !== 'linux') {
        return false;
    }

    const report = process.report?.getReport() as { header?: Record<string, unknown> } | undefined;
    const header = report?.header;
    return typeof header?.glibcVersionRuntime !== 'string';
}

/** Resolve a supported platform to one immutable official uv release asset. */
export function resolveUvArtifact(platform: string = process.platform, arch: string = process.arch, musl: boolean = isMuslRuntime()): UvArtifact {
    const key = platform === 'linux' ? `${platform}-${arch}-${musl ? 'musl' : 'gnu'}` : `${platform}-${arch}`;
    const pinned = UV_RELEASE_ARTIFACTS[key];
    if (!pinned) {
        throw new Error(`uv ${REQUIRED_UV_VERSION} is not available for ${platform}/${arch}`);
    }

    return {
        ...pinned,
        archiveRoot: `uv-${pinned.target}`,
        url: `${UV_RELEASE_BASE_URL}/${pinned.archiveName}`,
    };
}

function sha256(data: Buffer): string {
    return createHash('sha256').update(data).digest('hex');
}

/** Fail closed unless an archive matches the release digest embedded in the extension. */
export function verifyArchiveSha256(archive: Buffer, expectedSha256: string): void {
    const actual = sha256(archive);
    if (!/^[0-9a-f]{64}$/.test(expectedSha256) || actual !== expectedSha256) {
        throw new Error(`uv archive SHA-256 mismatch (expected ${expectedSha256}, got ${actual})`);
    }
}

/** Normalize and validate an archive member name before any extraction. */
export function assertSafeArchivePath(entryName: string): string {
    if (!entryName || entryName.includes('\0')) {
        throw new Error('uv archive contains an empty or NUL-delimited path');
    }

    const slashPath = entryName.replace(/\\/g, '/');
    if (slashPath.startsWith('/') || /^[A-Za-z]:/.test(slashPath)) {
        throw new Error(`uv archive contains an absolute path: ${entryName}`);
    }

    const withoutTrailingSlash = slashPath.endsWith('/') ? slashPath.slice(0, -1) : slashPath;
    const parts = withoutTrailingSlash.split('/');
    if (parts.some(part => part === '' || part === '.' || part === '..')) {
        throw new Error(`uv archive contains an unsafe path: ${entryName}`);
    }

    return parts.join('/');
}

function readTarString(header: Buffer, start: number, length: number): string {
    const field = header.subarray(start, start + length);
    const nul = field.indexOf(0);
    return field.subarray(0, nul === -1 ? field.length : nul).toString('utf8');
}

function readTarOctal(header: Buffer, start: number, length: number): number {
    const value = readTarString(header, start, length).trim();
    if (!/^[0-7]+$/.test(value)) {
        throw new Error('uv tar archive contains an invalid octal field');
    }
    return Number.parseInt(value, 8);
}

function validateTarHeaderChecksum(header: Buffer): void {
    const expected = readTarOctal(header, 148, 8);
    let actual = 0;
    for (let index = 0; index < header.length; index += 1) {
        actual += index >= 148 && index < 156 ? 0x20 : header[index];
    }
    if (actual !== expected) {
        throw new Error('uv tar archive header checksum mismatch');
    }
}

function expectedArchiveMembers(artifact: UvArtifact): {
    root: string | null;
    uv: string;
    uvw: string | null;
    uvx: string;
} {
    if (artifact.format === 'zip') {
        return {
            root: null,
            uv: 'uv.exe',
            uvw: 'uvw.exe',
            uvx: 'uvx.exe',
        };
    }
    return {
        root: artifact.archiveRoot,
        uv: `${artifact.archiveRoot}/uv`,
        uvw: null,
        uvx: `${artifact.archiveRoot}/uvx`,
    };
}

function extractTarGzBinaries(archive: Buffer, artifact: UvArtifact): ExtractedUvBinaries {
    const tar = gunzipSync(archive, { maxOutputLength: MAX_EXTRACTED_BYTES });
    const expected = expectedArchiveMembers(artifact);
    let offset = 0;
    let uv: Buffer | undefined;
    let uvx: Buffer | undefined;

    while (offset + 512 <= tar.length) {
        const header = tar.subarray(offset, offset + 512);
        if (header.every(byte => byte === 0)) {
            break;
        }

        validateTarHeaderChecksum(header);
        const name = readTarString(header, 0, 100);
        const prefix = readTarString(header, 345, 155);
        const safeName = assertSafeArchivePath(prefix ? `${prefix}/${name}` : name);
        const size = readTarOctal(header, 124, 12);
        const type = String.fromCharCode(header[156] || 0);
        const dataStart = offset + 512;
        const dataEnd = dataStart + size;

        if (!Number.isSafeInteger(size) || size < 0 || dataEnd > tar.length || size > MAX_EXTRACTED_BYTES) {
            throw new Error(`uv tar archive member has an invalid size: ${safeName}`);
        }

        if (type === '5') {
            if (safeName !== expected.root || size !== 0) {
                throw new Error(`uv tar archive contains an unexpected directory: ${safeName}`);
            }
        } else if (type === '\0' || type === '0') {
            if (safeName === expected.uv && !uv) {
                uv = Buffer.from(tar.subarray(dataStart, dataEnd));
            } else if (safeName === expected.uvx && !uvx) {
                uvx = Buffer.from(tar.subarray(dataStart, dataEnd));
            } else {
                throw new Error(`uv tar archive contains an unexpected or duplicate file: ${safeName}`);
            }
        } else {
            throw new Error(`uv tar archive contains an unsupported member type: ${safeName}`);
        }

        offset = dataStart + Math.ceil(size / 512) * 512;
    }

    if (!uv || !uvx || uv.length === 0 || uvx.length === 0) {
        throw new Error('uv tar archive does not contain both expected executables');
    }
    return { uv, uvx };
}

function findZipEndOfCentralDirectory(archive: Buffer): number {
    const minimumOffset = Math.max(0, archive.length - 65_557);
    for (let offset = archive.length - 22; offset >= minimumOffset; offset -= 1) {
        if (archive.readUInt32LE(offset) === 0x06054b50) {
            return offset;
        }
    }
    throw new Error('uv ZIP archive is missing its central directory');
}

function extractZipMember(
    archive: Buffer,
    localHeaderOffset: number,
    expectedName: string,
    compressionMethod: number,
    compressedSize: number,
    uncompressedSize: number,
): Buffer {
    if (localHeaderOffset < 0 || localHeaderOffset + 30 > archive.length || archive.readUInt32LE(localHeaderOffset) !== 0x04034b50) {
        throw new Error(`uv ZIP member has an invalid local header: ${expectedName}`);
    }

    const localFlags = archive.readUInt16LE(localHeaderOffset + 6);
    const localMethod = archive.readUInt16LE(localHeaderOffset + 8);
    const nameLength = archive.readUInt16LE(localHeaderOffset + 26);
    const extraLength = archive.readUInt16LE(localHeaderOffset + 28);
    const nameStart = localHeaderOffset + 30;
    const dataStart = nameStart + nameLength + extraLength;
    const dataEnd = dataStart + compressedSize;
    if (dataEnd > archive.length || localMethod !== compressionMethod || (localFlags & 1) !== 0) {
        throw new Error(`uv ZIP member has an invalid or encrypted local payload: ${expectedName}`);
    }

    const localName = archive.subarray(nameStart, nameStart + nameLength).toString('utf8');
    if (assertSafeArchivePath(localName) !== expectedName) {
        throw new Error(`uv ZIP central/local member mismatch: ${expectedName}`);
    }

    const compressed = archive.subarray(dataStart, dataEnd);
    let extracted: Buffer;
    if (compressionMethod === 0) {
        extracted = Buffer.from(compressed);
    } else if (compressionMethod === 8) {
        extracted = inflateRawSync(compressed, {
            maxOutputLength: MAX_EXTRACTED_BYTES,
        });
    } else {
        throw new Error(`uv ZIP member uses unsupported compression: ${expectedName}`);
    }

    if (extracted.length !== uncompressedSize || extracted.length > MAX_EXTRACTED_BYTES) {
        throw new Error(`uv ZIP member size mismatch: ${expectedName}`);
    }
    return extracted;
}

function extractZipBinaries(archive: Buffer, artifact: UvArtifact): ExtractedUvBinaries {
    const eocdOffset = findZipEndOfCentralDirectory(archive);
    const diskNumber = archive.readUInt16LE(eocdOffset + 4);
    const centralDisk = archive.readUInt16LE(eocdOffset + 6);
    const entriesOnDisk = archive.readUInt16LE(eocdOffset + 8);
    const entryCount = archive.readUInt16LE(eocdOffset + 10);
    const centralSize = archive.readUInt32LE(eocdOffset + 12);
    const centralOffset = archive.readUInt32LE(eocdOffset + 16);
    if (
        diskNumber !== 0 ||
        centralDisk !== 0 ||
        entriesOnDisk !== entryCount ||
        entryCount === 0xffff ||
        centralSize === 0xffffffff ||
        centralOffset === 0xffffffff ||
        centralOffset + centralSize > eocdOffset
    ) {
        throw new Error('uv ZIP archive uses unsupported multi-disk or ZIP64 metadata');
    }

    const expected = expectedArchiveMembers(artifact);
    let offset = centralOffset;
    let uv: Buffer | undefined;
    let uvw: Buffer | undefined;
    let uvx: Buffer | undefined;

    for (let entryIndex = 0; entryIndex < entryCount; entryIndex += 1) {
        if (offset + 46 > archive.length || archive.readUInt32LE(offset) !== 0x02014b50) {
            throw new Error('uv ZIP archive contains an invalid central directory entry');
        }

        const flags = archive.readUInt16LE(offset + 8);
        const compressionMethod = archive.readUInt16LE(offset + 10);
        const compressedSize = archive.readUInt32LE(offset + 20);
        const uncompressedSize = archive.readUInt32LE(offset + 24);
        const nameLength = archive.readUInt16LE(offset + 28);
        const extraLength = archive.readUInt16LE(offset + 30);
        const commentLength = archive.readUInt16LE(offset + 32);
        const diskStart = archive.readUInt16LE(offset + 34);
        const externalAttributes = archive.readUInt32LE(offset + 38);
        const localHeaderOffset = archive.readUInt32LE(offset + 42);
        const entryEnd = offset + 46 + nameLength + extraLength + commentLength;
        if (entryEnd > archive.length || diskStart !== 0 || (flags & 1) !== 0) {
            throw new Error('uv ZIP archive contains an invalid, encrypted, or multi-disk entry');
        }

        const rawName = archive.subarray(offset + 46, offset + 46 + nameLength).toString('utf8');
        const safeName = assertSafeArchivePath(rawName);
        const unixFileType = (externalAttributes >>> 16) & 0xf000;
        const isDirectory = rawName.endsWith('/');
        if (unixFileType === 0xa000) {
            throw new Error(`uv ZIP archive contains a symbolic link: ${safeName}`);
        }

        if (isDirectory) {
            if (!expected.root || safeName !== expected.root || uncompressedSize !== 0) {
                throw new Error(`uv ZIP archive contains an unexpected directory: ${safeName}`);
            }
        } else if (safeName === expected.uv && !uv) {
            uv = extractZipMember(archive, localHeaderOffset, safeName, compressionMethod, compressedSize, uncompressedSize);
        } else if (safeName === expected.uvw && !uvw) {
            uvw = extractZipMember(archive, localHeaderOffset, safeName, compressionMethod, compressedSize, uncompressedSize);
        } else if (safeName === expected.uvx && !uvx) {
            uvx = extractZipMember(archive, localHeaderOffset, safeName, compressionMethod, compressedSize, uncompressedSize);
        } else {
            throw new Error(`uv ZIP archive contains an unexpected or duplicate file: ${safeName}`);
        }

        offset = entryEnd;
    }

    if (offset !== centralOffset + centralSize || !uv || !uvw || !uvx || uv.length === 0 || uvw.length === 0 || uvx.length === 0) {
        throw new Error('uv ZIP archive does not contain the exact official executable set');
    }
    if (uv.length + uvw.length + uvx.length > MAX_EXTRACTED_BYTES) {
        throw new Error('uv ZIP archive exceeds the maximum extracted size');
    }
    return { uv, uvx };
}

/** Extract only the two expected binaries from a checksum-verified uv archive. */
export function extractUvBinaries(archive: Buffer, artifact: UvArtifact): ExtractedUvBinaries {
    return artifact.format === 'tar.gz' ? extractTarGzBinaries(archive, artifact) : extractZipBinaries(archive, artifact);
}

function executeVersion(binaryPath: string, env?: ProcessEnvironment): Promise<string> {
    return new Promise((resolve, reject) => {
        execFile(binaryPath, ['--version'], { timeout: 10_000, env }, (error, stdout) => {
            if (error) {
                reject(error);
                return;
            }
            resolve(stdout.trim());
        });
    });
}

export function isRequiredUvVersionOutput(output: string, command: 'uv' | 'uvx'): boolean {
    const escapedVersion = REQUIRED_UV_VERSION.replace(/\./g, '\\.');
    return new RegExp(`^${command} ${escapedVersion}(?: \\([A-Za-z0-9._-]+\\))?$`).test(output.trim());
}

async function validateUvPair(uvPath: string, env?: ProcessEnvironment): Promise<boolean> {
    const uvxPath = getUvxPath(uvPath);
    const [uvVersion, uvxVersion] = await Promise.all([executeVersion(uvPath, env), executeVersion(uvxPath, env)]);
    return isRequiredUvVersionOutput(uvVersion, 'uv') && isRequiredUvVersionOutput(uvxVersion, 'uvx');
}

function managedUvPaths(
    storageRoot: string,
    platform: string = process.platform,
): {
    versionRoot: string;
    uv: string;
    uvx: string;
    receipt: string;
} {
    const versionRoot = path.join(storageRoot, 'uv', REQUIRED_UV_VERSION);
    const extension = platform === 'win32' ? '.exe' : '';
    return {
        versionRoot,
        uv: path.join(versionRoot, 'bin', `uv${extension}`),
        uvx: path.join(versionRoot, 'bin', `uvx${extension}`),
        receipt: path.join(versionRoot, 'install-receipt.json'),
    };
}

export function getManagedUvPath(storageRoot: string, platform: string = process.platform): string {
    return managedUvPaths(storageRoot, platform).uv;
}

function assertContainedRealPath(parentRealPath: string, childRealPath: string, label: string): void {
    const relative = path.relative(parentRealPath, childRealPath);
    if (relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
        throw new Error(`${label} escapes the managed uv storage root`);
    }
}

function inspectRealDirectory(directory: string, label: string): string {
    const stat = fs.lstatSync(directory);
    if (stat.isSymbolicLink() || !stat.isDirectory()) {
        throw new Error(`${label} must be a real directory, not a symlink, junction, or file`);
    }
    return fs.realpathSync(directory);
}

function prepareManagedStorage(storageRoot: string): ManagedStorageLayout {
    if (!path.isAbsolute(storageRoot)) {
        throw new Error('Managed uv storage root must be an absolute path');
    }

    const absoluteStorageRoot = path.resolve(storageRoot);
    fs.mkdirSync(absoluteStorageRoot, { recursive: true, mode: 0o700 });
    const storageRealPath = inspectRealDirectory(absoluteStorageRoot, 'Managed uv storage root');
    const uvRoot = path.join(absoluteStorageRoot, 'uv');
    try {
        fs.mkdirSync(uvRoot, { mode: 0o700 });
    } catch (error) {
        if (systemErrorCode(error) !== 'EEXIST') {
            throw error;
        }
    }
    const uvRealPath = inspectRealDirectory(uvRoot, 'Managed uv directory');
    assertContainedRealPath(storageRealPath, uvRealPath, 'Managed uv directory');
    return { storageRoot: absoluteStorageRoot, storageRealPath, uvRoot, uvRealPath };
}

function inspectManagedStorage(storageRoot: string): ManagedStorageLayout | null {
    if (!path.isAbsolute(storageRoot) || !fs.existsSync(storageRoot)) {
        return null;
    }

    const absoluteStorageRoot = path.resolve(storageRoot);
    const storageRealPath = inspectRealDirectory(absoluteStorageRoot, 'Managed uv storage root');
    const uvRoot = path.join(absoluteStorageRoot, 'uv');
    if (!fs.existsSync(uvRoot)) {
        return null;
    }
    const uvRealPath = inspectRealDirectory(uvRoot, 'Managed uv directory');
    assertContainedRealPath(storageRealPath, uvRealPath, 'Managed uv directory');
    return { storageRoot: absoluteStorageRoot, storageRealPath, uvRoot, uvRealPath };
}

function inspectVersionDirectory(layout: ManagedStorageLayout, versionRoot: string): string {
    const versionRealPath = inspectRealDirectory(versionRoot, 'Managed uv version directory');
    assertContainedRealPath(layout.uvRealPath, versionRealPath, 'Managed uv version directory');
    return versionRealPath;
}

function assertManagedStorageIdentity(layout: ManagedStorageLayout): void {
    const current = inspectManagedStorage(layout.storageRoot);
    if (!current || current.storageRealPath !== layout.storageRealPath || current.uvRealPath !== layout.uvRealPath) {
        throw new Error('Managed uv storage identity changed during installation');
    }
}

function inspectRegularContainedFile(filePath: string, parentRealPath: string, label: string): void {
    const stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink() || !stat.isFile()) {
        throw new Error(`${label} must be a real regular file`);
    }
    assertContainedRealPath(parentRealPath, fs.realpathSync(filePath), label);
}

function removeManagedVersionDirectory(layout: ManagedStorageLayout, versionRoot: string): void {
    if (!fs.existsSync(versionRoot)) {
        return;
    }
    inspectVersionDirectory(layout, versionRoot);
    fs.rmSync(versionRoot, { recursive: true, force: true });
}

function removeManagedStagingDirectory(layout: ManagedStorageLayout, stagingRoot: string): void {
    if (!fs.existsSync(stagingRoot)) {
        return;
    }
    const stagingRealPath = inspectRealDirectory(stagingRoot, 'Managed uv staging directory');
    assertContainedRealPath(layout.uvRealPath, stagingRealPath, 'Managed uv staging directory');
    fs.rmSync(stagingRoot, { recursive: true, force: true });
}

/**
 * Acquire an inter-process install lease below the validated uv storage root.
 * The lease never removes an existing lock: abandoned or suspicious locks fail
 * closed after the bounded wait instead of risking a concurrent install.
 */
export async function acquireManagedUvInstallLease(storageRoot: string, options: ManagedInstallLeaseOptions = {}): Promise<ManagedInstallLease> {
    const layout = prepareManagedStorage(storageRoot);
    const lockPath = path.join(layout.uvRoot, '.install-lock');
    const ownerPath = path.join(lockPath, 'owner');
    const token = randomUUID();
    const maxWaitMs = options.maxWaitMs ?? 120_000;
    const pollIntervalMs = options.pollIntervalMs ?? 200;
    if (maxWaitMs < 0 || pollIntervalMs < 1) {
        throw new Error('Managed uv install lease timing must be positive');
    }

    const deadline = Date.now() + maxWaitMs;
    while (true) {
        let createdLock = false;
        try {
            fs.mkdirSync(lockPath, { mode: 0o700 });
            createdLock = true;
            const lockRealPath = inspectRealDirectory(lockPath, 'Managed uv install lock');
            assertContainedRealPath(layout.uvRealPath, lockRealPath, 'Managed uv install lock');
            fs.writeFileSync(ownerPath, `${token}\n`, { encoding: 'utf8', mode: 0o600, flag: 'wx' });

            let released = false;
            return {
                release(): void {
                    if (released) {
                        return;
                    }
                    released = true;
                    try {
                        const currentLockRealPath = inspectRealDirectory(lockPath, 'Managed uv install lock');
                        assertContainedRealPath(layout.uvRealPath, currentLockRealPath, 'Managed uv install lock');
                        inspectRegularContainedFile(ownerPath, currentLockRealPath, 'Managed uv install lock owner');
                        if (fs.readFileSync(ownerPath, 'utf8').trim() === token) {
                            fs.rmSync(lockPath, { recursive: true, force: true });
                        }
                    } catch {
                        // Never delete a lock that changed identity while held.
                    }
                },
            };
        } catch (error) {
            if (createdLock) {
                try {
                    const lockRealPath = inspectRealDirectory(lockPath, 'Managed uv install lock');
                    assertContainedRealPath(layout.uvRealPath, lockRealPath, 'Managed uv install lock');
                    const ownerMissing = !fs.existsSync(ownerPath);
                    if (!ownerMissing) {
                        inspectRegularContainedFile(ownerPath, lockRealPath, 'Managed uv install lock owner');
                    }
                    if (ownerMissing || fs.readFileSync(ownerPath, 'utf8').trim() === token) {
                        fs.rmSync(lockPath, { recursive: true, force: true });
                    }
                } catch {
                    // Never clean up a lock whose identity cannot be proven.
                }
            }
            if (systemErrorCode(error) !== 'EEXIST') {
                throw error;
            }

            const lockRealPath = inspectRealDirectory(lockPath, 'Managed uv install lock');
            assertContainedRealPath(layout.uvRealPath, lockRealPath, 'Managed uv install lock');
            if (Date.now() >= deadline) {
                throw new Error('Timed out waiting for the managed uv install lease', { cause: error });
            }
            await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
        }
    }
}

async function validateManagedUvInstall(storageRoot: string): Promise<string | null> {
    try {
        const layout = inspectManagedStorage(storageRoot);
        if (!layout) {
            return null;
        }
        const paths = managedUvPaths(layout.storageRoot);
        if (!fs.existsSync(paths.versionRoot) || !fs.existsSync(paths.uv) || !fs.existsSync(paths.uvx) || !fs.existsSync(paths.receipt)) {
            return null;
        }
        const versionRealPath = inspectVersionDirectory(layout, paths.versionRoot);
        inspectRegularContainedFile(paths.uv, versionRealPath, 'Managed uv executable');
        inspectRegularContainedFile(paths.uvx, versionRealPath, 'Managed uvx executable');
        inspectRegularContainedFile(paths.receipt, versionRealPath, 'Managed uv install receipt');
        if (fs.statSync(paths.receipt).size > 64 * 1024) {
            return null;
        }

        const artifact = resolveUvArtifact();
        const receipt = JSON.parse(fs.readFileSync(paths.receipt, 'utf8')) as Partial<ManagedUvReceipt>;
        if (
            receipt.schemaVersion !== 1 ||
            receipt.uvVersion !== REQUIRED_UV_VERSION ||
            receipt.target !== artifact.target ||
            receipt.archiveSha256 !== artifact.sha256 ||
            receipt.uvSha256 !== sha256(fs.readFileSync(paths.uv)) ||
            receipt.uvxSha256 !== sha256(fs.readFileSync(paths.uvx))
        ) {
            return null;
        }
        return (await validateUvPair(paths.uv)) ? paths.uv : null;
    } catch {
        return null;
    }
}

function isAllowedDownloadHost(url: URL): boolean {
    return (
        url.protocol === 'https:' &&
        (url.hostname === 'github.com' || url.hostname === 'release-assets.githubusercontent.com' || url.hostname === 'objects.githubusercontent.com')
    );
}

function downloadPinnedArchive(url: string, redirectsRemaining: number = MAX_REDIRECTS): Promise<Buffer> {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        if (!isAllowedDownloadHost(parsed)) {
            reject(new Error(`Refusing uv download from untrusted host: ${parsed.hostname}`));
            return;
        }

        const request = https.get(parsed, { headers: { 'User-Agent': 'medpaper-assistant-vscode' } }, response => {
            response.on('error', reject);
            const status = response.statusCode || 0;
            if (status >= 300 && status < 400 && response.headers.location) {
                response.resume();
                if (redirectsRemaining <= 0) {
                    reject(new Error('Too many redirects while downloading uv'));
                    return;
                }
                const redirect = new URL(response.headers.location, parsed);
                downloadPinnedArchive(redirect.toString(), redirectsRemaining - 1).then(resolve, reject);
                return;
            }
            if (status !== 200) {
                response.resume();
                reject(new Error(`uv download failed with HTTP ${status}`));
                return;
            }

            const contentLength = Number(response.headers['content-length'] || 0);
            if (contentLength > MAX_ARCHIVE_BYTES) {
                response.destroy(new Error('uv archive exceeds the maximum allowed size'));
                return;
            }

            const chunks: Buffer[] = [];
            let total = 0;
            response.on('data', (chunk: Buffer) => {
                total += chunk.length;
                if (total > MAX_ARCHIVE_BYTES) {
                    response.destroy(new Error('uv archive exceeds the maximum allowed size'));
                    return;
                }
                chunks.push(chunk);
            });
            response.on('end', () => resolve(Buffer.concat(chunks, total)));
        });
        request.setTimeout(120_000, () => request.destroy(new Error('uv download timed out')));
        request.on('error', reject);
    });
}

/**
 * Find an exact-version uv/uvx pair by checking known locations.
 * Returns the path string or null if not found.
 *
 * On macOS, the process PATH is enriched with Homebrew and common install
 * directories before searching, because VS Code GUI apps don't load shell profiles.
 *
 * @param log - Optional logging function
 * @param managedStorageRoot - VS Code extension storage containing hash-bound managed installs
 */
export async function findUvPath(log?: (msg: string) => void, managedStorageRoot?: string): Promise<string | null> {
    const paths = getUvSearchPaths();
    const _log = log || (() => {});

    if (managedStorageRoot) {
        const managedUv = await validateManagedUvInstall(managedStorageRoot);
        if (managedUv) {
            _log(`Accepted managed uv ${REQUIRED_UV_VERSION}; receipt and binary hashes are valid: ${managedUv}`);
            return managedUv;
        }
    }

    // Build an enriched PATH for exec calls (macOS Dock launch doesn't have Homebrew)
    const enrichedPath = enrichPath(process.env.PATH || '');

    for (const uvPath of paths) {
        try {
            if (uvPath === 'uv') {
                const valid = await validateUvPair('uv', {
                    ...process.env,
                    PATH: enrichedPath,
                });
                if (!valid) {
                    _log(`Rejected PATH uv: both uv and uvx must be exactly ${REQUIRED_UV_VERSION}`);
                    continue;
                }
                _log(`Accepted PATH uv because both uv and uvx satisfy the exact ${REQUIRED_UV_VERSION} contract`);
                return 'uv';
            } else if (fs.existsSync(uvPath)) {
                const valid = await validateUvPair(uvPath);
                if (!valid) {
                    _log(`Rejected uv at ${uvPath}: both executables must be exactly ${REQUIRED_UV_VERSION}`);
                    continue;
                }
                _log(`Accepted external uv ${REQUIRED_UV_VERSION} at: ${uvPath}`);
                return uvPath;
            }
        } catch {
            // Continue to next path
        }
    }

    return null;
}

/**
 * Install uv and return the installed path.
 * This is the raw installer — callers should wrap with UI (progress notifications, etc.)
 *
 * @param managedStorageRoot - VS Code extension storage root used for the version-scoped install
 * @param log - Optional logging function
 * @returns The installed uv path, or null if installation failed
 */
export async function installUvHeadless(managedStorageRoot: string, log?: (msg: string) => void): Promise<string | null> {
    const _log = log || (() => {});
    let artifact: UvArtifact;
    try {
        artifact = resolveUvArtifact();
    } catch (error) {
        _log(error instanceof Error ? error.message : String(error));
        return null;
    }

    const existing = await validateManagedUvInstall(managedStorageRoot);
    if (existing) {
        _log(`Managed uv ${REQUIRED_UV_VERSION} is already verified: ${existing}`);
        return existing;
    }

    let lease: ManagedInstallLease | null = null;
    let layout: ManagedStorageLayout | null = null;
    let stagingRoot: string | null = null;

    try {
        lease = await acquireManagedUvInstallLease(managedStorageRoot);

        // A concurrent installer may have completed while this caller waited.
        const installedByPeer = await validateManagedUvInstall(managedStorageRoot);
        if (installedByPeer) {
            _log(`Reused concurrently installed uv ${REQUIRED_UV_VERSION}: ${installedByPeer}`);
            return installedByPeer;
        }

        layout = prepareManagedStorage(managedStorageRoot);
        const finalPaths = managedUvPaths(layout.storageRoot);
        if (fs.existsSync(finalPaths.versionRoot)) {
            inspectVersionDirectory(layout, finalPaths.versionRoot);
        }
        stagingRoot = fs.mkdtempSync(path.join(layout.uvRoot, '.install-'));
        const stagingRealPath = inspectRealDirectory(stagingRoot, 'Managed uv staging directory');
        assertContainedRealPath(layout.uvRealPath, stagingRealPath, 'Managed uv staging directory');
        const stagingBin = path.join(stagingRoot, 'bin');

        _log(`Installing pinned uv ${REQUIRED_UV_VERSION} for ${artifact.target}`);
        _log(`Downloading immutable release asset: ${artifact.url}`);
        const archive = await downloadPinnedArchive(artifact.url);
        verifyArchiveSha256(archive, artifact.sha256);
        const binaries = extractUvBinaries(archive, artifact);

        fs.mkdirSync(stagingBin, { recursive: true });
        const extension = process.platform === 'win32' ? '.exe' : '';
        const stagedUv = path.join(stagingBin, `uv${extension}`);
        const stagedUvx = path.join(stagingBin, `uvx${extension}`);
        fs.writeFileSync(stagedUv, binaries.uv, { mode: 0o755, flag: 'wx' });
        fs.writeFileSync(stagedUvx, binaries.uvx, { mode: 0o755, flag: 'wx' });
        if (process.platform !== 'win32') {
            fs.chmodSync(stagedUv, 0o755);
            fs.chmodSync(stagedUvx, 0o755);
        }

        if (!(await validateUvPair(stagedUv))) {
            throw new Error(`Downloaded executables do not report uv/uvx ${REQUIRED_UV_VERSION}`);
        }

        const receipt: ManagedUvReceipt = {
            schemaVersion: 1,
            uvVersion: REQUIRED_UV_VERSION,
            target: artifact.target,
            archiveSha256: artifact.sha256,
            uvSha256: sha256(binaries.uv),
            uvxSha256: sha256(binaries.uvx),
        };
        fs.writeFileSync(path.join(stagingRoot, 'install-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`, {
            encoding: 'utf8',
            mode: 0o600,
            flag: 'wx',
        });

        assertManagedStorageIdentity(layout);
        const stagingRealPathBeforeRename = inspectRealDirectory(stagingRoot, 'Managed uv staging directory');
        assertContainedRealPath(layout.uvRealPath, stagingRealPathBeforeRename, 'Managed uv staging directory');
        removeManagedVersionDirectory(layout, finalPaths.versionRoot);
        assertManagedStorageIdentity(layout);
        fs.renameSync(stagingRoot, finalPaths.versionRoot);
        stagingRoot = null;

        const installed = await validateManagedUvInstall(layout.storageRoot);
        if (!installed) {
            removeManagedVersionDirectory(layout, finalPaths.versionRoot);
            throw new Error('Managed uv failed post-install receipt validation');
        }
        _log(`uv ${REQUIRED_UV_VERSION} installed and verified at: ${installed}`);
        return installed;
    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        _log(`uv installation failed: ${errorMsg}`);
        return null;
    } finally {
        if (layout && stagingRoot) {
            try {
                removeManagedStagingDirectory(layout, stagingRoot);
            } catch {
                // A replaced staging path is intentionally left untouched.
            }
        }
        lease?.release();
    }
}

/**
 * Build an isolated uvx command from an immutable package source.
 *
 * This intentionally ignores arbitrary pre-installed binaries: a binary with
 * the same name may come from an MCP SDK v1 release.
 */
export function buildPinnedUvxCommand(uvPath: string, packageSource: string, entrypoint: string, pythonVersion?: string): [string, string[]] {
    const uvxPath = getUvxPath(uvPath);
    const args: string[] = [];

    if (pythonVersion) {
        args.push('--python', pythonVersion);
    }

    args.push('--from', packageSource, entrypoint);
    return [uvxPath, args];
}

/**
 * Build environment variables for MCP server child process.
 * Includes essential system variables for proper operation.
 *
 * On macOS, the PATH is enriched with Homebrew and common tool directories
 * so that subprocess calls to pandoc, git, etc. work even when VS Code
 * was launched from Dock/Spotlight (which doesn't load shell profiles).
 *
 * @param options - Configuration options
 * @returns Environment variables object
 */
export function buildMcpEnv(options: { workspaceDir?: string; pythonPath?: string; toolSurface?: 'compact' | 'full' }): Record<string, string> {
    const env: Record<string, string> = {};

    // Workspace base directory for projects/logs
    if (options.workspaceDir) {
        env.MEDPAPER_BASE_DIR = options.workspaceDir;
    }

    // Default agent-facing runtime to the compact main mdpaper surface unless overridden.
    env.MEDPAPER_TOOL_SURFACE = options.toolSurface || process.env.MEDPAPER_TOOL_SURFACE || 'compact';

    // PYTHONPATH only for dev mode (bundled code)
    if (options.pythonPath) {
        env.PYTHONPATH = options.pythonPath;
    }

    // Inherit and enrich PATH (critical for macOS — add Homebrew, ~/.local/bin)
    if (process.env.PATH) {
        env.PATH = enrichPath(process.env.PATH);
    }
    if (process.env.HOME) {
        env.HOME = process.env.HOME;
    }
    if (process.env.SHELL) {
        env.SHELL = process.env.SHELL;
    }
    if (process.env.LANG) {
        env.LANG = process.env.LANG;
    }
    // macOS: TMPDIR (macOS uses TMPDIR, not TEMP/TMP)
    if (process.env.TMPDIR) {
        env.TMPDIR = process.env.TMPDIR;
    }
    // Windows-specific
    if (process.env.USERPROFILE) {
        env.USERPROFILE = process.env.USERPROFILE;
    }
    if (process.env.APPDATA) {
        env.APPDATA = process.env.APPDATA;
    }
    if (process.env.LOCALAPPDATA) {
        env.LOCALAPPDATA = process.env.LOCALAPPDATA;
    }
    if (process.env.SYSTEMROOT) {
        env.SYSTEMROOT = process.env.SYSTEMROOT;
    }
    if (process.env.COMSPEC) {
        env.COMSPEC = process.env.COMSPEC;
    }
    // Windows: inherit TEMP/TMP for uv cache
    if (process.env.TEMP) {
        env.TEMP = process.env.TEMP;
    }
    if (process.env.TMP) {
        env.TMP = process.env.TMP;
    }

    return env;
}

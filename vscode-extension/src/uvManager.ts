/**
 * uv Manager — Auto-detection and installation of uv (Python package manager).
 *
 * Provides zero-config experience:
 * 1. Detect uv in PATH or known install locations
 * 2. Auto-install uv if not found (cross-platform)
 * 3. Derive uvx path from uv path
 *
 * With uv installed, `uvx med-paper-assistant` handles EVERYTHING:
 * - Python auto-download (if no Python on system)
 * - Package installation from PyPI in isolated environment
 * - All dependencies resolved automatically
 * - No interference with user's other packages
 */

import * as path from 'path';
import * as fs from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

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
        path.join(homeDir, '.local', 'bin'),   // uv default install (curl | sh)
        path.join(homeDir, '.cargo', 'bin'),    // uv via cargo / rustup
    ];

    if (process.platform === 'darwin') {
        dirs.push(
            '/opt/homebrew/bin',      // Homebrew on Apple Silicon (M1/M2/M3/M4)
            '/opt/homebrew/sbin',
            '/usr/local/bin',         // Homebrew on Intel Mac / MacPorts
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
    if (toAdd.length === 0) { return basePath; }
    return [...toAdd, basePath].join(path.delimiter);
}

/**
 * Get all PATH directories after enrichment, preserving order and removing duplicates.
 */
function getPathDirectories(basePath: string): string[] {
    const seen = new Set<string>();
    const dirs: string[] = [];

    for (const dir of enrichPath(basePath).split(path.delimiter)) {
        if (!dir || seen.has(dir)) {
            continue;
        }
        seen.add(dir);
        dirs.push(dir);
    }

    return dirs;
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
            'uv',  // In PATH
            path.join(homeDir, 'AppData', 'Local', 'uv', 'bin', 'uv.exe'),
            path.join(homeDir, '.local', 'bin', 'uv.exe'),
            path.join(homeDir, '.cargo', 'bin', 'uv.exe'),
            'C:\\Program Files\\uv\\uv.exe',
        ];
    } else {
        return [
            'uv',  // In PATH (enriched)
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

/**
 * Get the install command for uv based on platform.
 */
export function getUvInstallCommand(): string {
    if (process.platform === 'win32') {
        return 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"';
    }
    return 'curl -LsSf https://astral.sh/uv/install.sh | sh';
}

/**
 * Find the actual uv binary path by checking known locations.
 * Returns the path string or null if not found.
 *
 * On macOS, the process PATH is enriched with Homebrew and common install
 * directories before searching, because VS Code GUI apps don't load shell profiles.
 *
 * @param log - Optional logging function
 */
export async function findUvPath(log?: (msg: string) => void): Promise<string | null> {
    const paths = getUvSearchPaths();
    const _log = log || (() => {});

    // Build an enriched PATH for exec calls (macOS Dock launch doesn't have Homebrew)
    const enrichedPath = enrichPath(process.env.PATH || '');

    for (const uvPath of paths) {
        try {
            if (uvPath === 'uv') {
                await execAsync('uv --version', { env: { ...process.env, PATH: enrichedPath } });
                _log('Found uv in PATH');
                return 'uv';
            } else if (fs.existsSync(uvPath)) {
                await execAsync(`"${uvPath}" --version`);
                _log(`Found uv at: ${uvPath}`);
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
 * @param log - Optional logging function
 * @returns The installed uv path, or null if installation failed
 */
export async function installUvHeadless(log?: (msg: string) => void): Promise<string | null> {
    const _log = log || (() => {});
    const command = getUvInstallCommand();

    _log(`Installing uv on ${process.platform}...`);
    _log(`Running: ${command}`);

    try {
        // Use enriched PATH so the install script can find curl, etc.
        const enrichedPath = enrichPath(process.env.PATH || '');
        await execAsync(command, {
            timeout: 120000,
            env: { ...process.env, PATH: enrichedPath },
        });

        // Wait for filesystem to sync
        await new Promise(resolve => setTimeout(resolve, 2000));

        const uvPath = await findUvPath(log);
        if (uvPath) {
            _log(`uv installed successfully at: ${uvPath}`);
        } else {
            _log('uv installation completed but binary not found');
        }
        return uvPath;
    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        _log(`uv installation failed: ${errorMsg}`);
        return null;
    }
}

/**
 * Find a pre-installed tool binary in known locations.
 * Checks uv tool directories, Homebrew, and common install paths.
 *
 * This avoids re-downloading via uvx when the tool is already persistently
 * installed (via `uv tool install`, `pip install --user`, `brew install`, etc.).
 *
 * @param binaryName - The command name to look for (e.g., 'med-paper-assistant')
 * @returns Absolute path to the binary, or null if not found
 */
export function findInstalledTool(binaryName: string): string | null {
    const homeDir = process.env.HOME || process.env.USERPROFILE || '';
    const ext = process.platform === 'win32' ? '.exe' : '';
    const bin = binaryName + ext;

    const candidates: string[] = getPathDirectories(process.env.PATH || '')
        .map(dir => path.join(dir, bin));

    if (process.platform === 'win32') {
        candidates.push(
            path.join(homeDir, '.local', 'bin', bin),
            path.join(process.env.LOCALAPPDATA || '', 'uv', 'bin', bin),
            path.join(homeDir, 'AppData', 'Local', 'uv', 'bin', bin),
        );
    } else {
        candidates.push(
            path.join(homeDir, '.local', 'bin', bin),       // uv tool install / pip --user
            path.join(homeDir, '.cargo', 'bin', bin),        // cargo install
            '/usr/local/bin/' + bin,                         // Homebrew Intel / manual
        );
        if (process.platform === 'darwin') {
            candidates.push('/opt/homebrew/bin/' + bin);     // Homebrew Apple Silicon
        }
    }

    for (const c of candidates) {
        if (c && fs.existsSync(c)) {
            return c;
        }
    }

    return null;
}

/**
 * Build the install command for a persistent uv tool installation.
 *
 * @param packageName - PyPI package name
 * @param binaryName - Tool binary to install from the package
 * @param pythonVersion - Optional Python version constraint
 * @returns Command string runnable by exec
 */
export function getUvToolInstallCommand(
    packageName: string,
    binaryName?: string,
    pythonVersion?: string,
): string {
    const args = ['tool', 'install'];

    if (pythonVersion) {
        args.push('--python', pythonVersion);
    }

    if (binaryName && binaryName !== packageName) {
        args.push('--from', packageName, binaryName);
    } else {
        args.push(packageName);
    }

    return `uv ${args.join(' ')}`;
}

/**
 * Build the command for upgrading an already installed uv-managed tool.
 *
 * The upgrade target is the installed tool name, which matches the executable
 * name for normal tools and custom entry points such as cgu-server.
 *
 * @param packageName - PyPI package name (used when binaryName is omitted)
 * @param binaryName - Installed tool name when different from package name
 * @param pythonVersion - Optional Python interpreter/version selector
 * @returns Command string runnable by exec
 */
export function getUvToolUpgradeCommand(
    packageName: string,
    binaryName?: string,
    pythonVersion?: string,
): string {
    const args = ['tool', 'upgrade'];

    if (pythonVersion) {
        args.push('--python', pythonVersion);
    }

    args.push(binaryName || packageName);
    return `uv ${args.join(' ')}`;
}

/**
 * Ensure a persistent tool binary is installed for marketplace mode.
 *
 * If the binary already exists, it is reused. Otherwise the package is installed
 * with `uv tool install` so future activations can use the persistent binary
 * directly instead of creating a fresh uvx environment.
 *
 * @param packageName - PyPI package name
 * @param binaryName - Expected installed binary name
 * @param pythonVersion - Optional Python version constraint
 * @param log - Optional logging function
 * @returns Installed binary path, or null if install failed
 */
export async function ensureInstalledTool(
    packageName: string,
    binaryName?: string,
    pythonVersion?: string,
    log?: (msg: string) => void,
): Promise<string | null> {
    const _log = log || (() => {});
    const bin = binaryName || packageName;
    const existing = findInstalledTool(bin);

    if (existing) {
        _log(`Found pre-installed tool: ${bin} -> ${existing}`);

        const upgradeCommand = getUvToolUpgradeCommand(packageName, binaryName, pythonVersion);
        _log(`Checking for tool upgrades: ${upgradeCommand}`);

        try {
            await execAsync(upgradeCommand, {
                timeout: 180000,
                env: { ...process.env, PATH: enrichPath(process.env.PATH || '') },
            });
            const upgraded = findInstalledTool(bin);
            if (upgraded) {
                _log(`Tool is up to date: ${bin} -> ${upgraded}`);
                return upgraded;
            }
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            _log(`Tool upgrade skipped for ${bin}: ${errorMsg}`);
        }

        return existing;
    }

    const command = getUvToolInstallCommand(packageName, binaryName, pythonVersion);
    _log(`Installing persistent tool: ${packageName} (${bin})`);
    _log(`Running: ${command}`);

    try {
        await execAsync(command, {
            timeout: 180000,
            env: { ...process.env, PATH: enrichPath(process.env.PATH || '') },
        });

        const installed = findInstalledTool(bin);
        if (installed) {
            _log(`Installed persistent tool: ${bin} -> ${installed}`);
            return installed;
        }

        _log(`Install reported success but binary not found: ${bin}`);
        return null;
    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        _log(`Persistent tool install failed for ${packageName}: ${errorMsg}`);
        return null;
    }
}

/**
 * Build MCP server command preferring pre-installed tool over uvx.
 *
 * Resolution order:
 * 1. Pre-installed binary (uv tool install / pip --user / brew) → direct execution
 * 2. uvx (ephemeral environment) → downloads if not cached
 *
 * @param uvPath - Path to the uv binary (for uvx fallback)
 * @param packageName - PyPI package name (e.g., 'med-paper-assistant')
 * @param binaryName - Binary/command name (defaults to packageName)
 * @param pythonVersion - Optional Python version constraint
 * @returns [command, args, isPreInstalled] tuple
 */
export function buildMcpCommand(
    uvPath: string,
    packageName: string,
    binaryName?: string,
    pythonVersion?: string,
): [string, string[], boolean] {
    const bin = binaryName || packageName;
    const installed = findInstalledTool(bin);
    if (installed) {
        return [installed, [], true];
    }
    const [cmd, args] = buildUvxCommand(uvPath, packageName, pythonVersion);
    return [cmd, args, false];
}

/**
 * Build the MCP server command and args for marketplace mode.
 * Uses uvx for complete isolation — no PYTHONPATH needed.
 *
 * @param uvPath - Path to the uv binary
 * @param packageName - PyPI package name (e.g., 'med-paper-assistant')
 * @param pythonVersion - Optional Python version constraint (e.g., '>=3.11')
 * @returns [command, args] tuple
 */
export function buildUvxCommand(
    uvPath: string,
    packageName: string,
    pythonVersion?: string,
): [string, string[]] {
    const uvxPath = getUvxPath(uvPath);
    const args: string[] = [];

    if (pythonVersion) {
        args.push('--python', pythonVersion);
    }

    args.push(packageName);

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
export function buildMcpEnv(options: {
    workspaceDir?: string;
    pythonPath?: string;
}): Record<string, string> {
    const env: Record<string, string> = {};

    // Workspace base directory for projects/logs
    if (options.workspaceDir) {
        env.MEDPAPER_BASE_DIR = options.workspaceDir;
    }

    // PYTHONPATH only for dev mode (bundled code)
    if (options.pythonPath) {
        env.PYTHONPATH = options.pythonPath;
    }

    // Inherit and enrich PATH (critical for macOS — add Homebrew, ~/.local/bin)
    if (process.env.PATH) {
        env.PATH = enrichPath(process.env.PATH);
    }
    if (process.env.HOME) { env.HOME = process.env.HOME; }
    if (process.env.SHELL) { env.SHELL = process.env.SHELL; }
    if (process.env.LANG) { env.LANG = process.env.LANG; }
    // macOS: TMPDIR (macOS uses TMPDIR, not TEMP/TMP)
    if (process.env.TMPDIR) { env.TMPDIR = process.env.TMPDIR; }
    // Windows-specific
    if (process.env.USERPROFILE) { env.USERPROFILE = process.env.USERPROFILE; }
    if (process.env.APPDATA) { env.APPDATA = process.env.APPDATA; }
    if (process.env.LOCALAPPDATA) { env.LOCALAPPDATA = process.env.LOCALAPPDATA; }
    if (process.env.SYSTEMROOT) { env.SYSTEMROOT = process.env.SYSTEMROOT; }
    if (process.env.COMSPEC) { env.COMSPEC = process.env.COMSPEC; }
    // Windows: inherit TEMP/TMP for uv cache
    if (process.env.TEMP) { env.TEMP = process.env.TEMP; }
    if (process.env.TMP) { env.TMP = process.env.TMP; }

    return env;
}

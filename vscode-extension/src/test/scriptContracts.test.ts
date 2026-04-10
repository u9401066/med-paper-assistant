import { describe, expect, it } from 'vitest';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

const extensionRoot = path.resolve(__dirname, '..', '..');
const buildScriptPath = path.join(extensionRoot, 'scripts', 'build.sh');
const packageJsonPath = path.join(extensionRoot, 'package.json');
const validateShellPath = path.join(extensionRoot, 'scripts', 'validate-build.sh');
const validatePowerShellPath = path.join(extensionRoot, 'scripts', 'validate-build.ps1');
const validateBuild = require('../../scripts/validate-build.cjs');
const runValidateBuild = require('../../scripts/run-validate-build.cjs');

function createLogCollector() {
    const lines: string[] = [];
    return {
        lines,
        log(message = '') {
            lines.push(String(message));
        },
    };
}

describe('run-validate-build launcher', () => {
    it('builds a PowerShell launch command on Windows', () => {
        const launch = runValidateBuild.buildLaunchArgs(['--skip-tests'], 'win32', '/tmp/scripts');
        expect(launch.command).toBe('powershell.exe');
        expect(launch.args).toEqual([
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            path.join('/tmp/scripts', 'validate-build.ps1'),
            '--skip-tests',
        ]);
    });

    it('builds a bash launch command on unix-like platforms', () => {
        const launch = runValidateBuild.buildLaunchArgs(['--skip-tests'], 'linux', '/tmp/scripts');
        expect(launch.command).toBe('bash');
        expect(launch.args).toEqual([path.join('/tmp/scripts', 'validate-build.sh'), '--skip-tests']);
    });

    it('returns child exit status and forwards argv', () => {
        let seenCommand = '';
        let seenArgs: string[] = [];

        const exitCode = runValidateBuild.runValidateBuild({
            argv: ['--skip-tests'],
            platform: 'win32',
            scriptDir: '/tmp/scripts',
            spawn: (command: string, args: string[]) => {
                seenCommand = command;
                seenArgs = args;
                return { status: 0 };
            },
        });

        expect(exitCode).toBe(0);
        expect(seenCommand).toBe('powershell.exe');
        expect(seenArgs).toEqual([
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            path.join('/tmp/scripts', 'validate-build.ps1'),
            '--skip-tests',
        ]);
    });

    it('returns 1 with a stable error when spawn fails', () => {
        const errors: string[] = [];
        const exitCode = runValidateBuild.runValidateBuild({
            spawn: () => ({ status: null, error: new Error('spawn failed') }),
            stderr: (message: string) => errors.push(message),
        });

        expect(exitCode).toBe(1);
        expect(errors[0]).toContain('Failed to start validation command');
    });
});

describe('validate-build core', () => {
    it('reports missing package.json with a stable failure message', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-missing-pkg-'));
        const collector = createLogCollector();
        const reporter = validateBuild.createReporter(collector.log);
        const runtime = validateBuild.createValidationRuntime({
            extensionDir: tempDir,
            manifest: { chatCommands: [], paletteCommands: [] },
            log: collector.log,
        });

        const version = validateBuild.validatePackageJson(reporter, runtime);

        expect(version).toBe('');
        expect(reporter.getCounts().failCount).toBe(1);
        expect(collector.lines.some((line) => line.includes('Unable to read package.json'))).toBe(true);

        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('reports invalid package.json with a stable failure message', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-invalid-pkg-'));
        const collector = createLogCollector();
        fs.writeFileSync(path.join(tempDir, 'package.json'), '{invalid json', 'utf-8');

        const reporter = validateBuild.createReporter(collector.log);
        const runtime = validateBuild.createValidationRuntime({
            extensionDir: tempDir,
            manifest: { chatCommands: [], paletteCommands: [] },
            log: collector.log,
        });

        const version = validateBuild.validatePackageJson(reporter, runtime);

        expect(version).toBe('');
        expect(reporter.getCounts().failCount).toBe(1);
        expect(collector.lines.some((line) => line.includes('Invalid package.json JSON'))).toBe(true);

        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('keeps missing VSIX as a warning instead of a failure', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-no-vsix-'));
        const collector = createLogCollector();
        const reporter = validateBuild.createReporter(collector.log);
        const runtime = validateBuild.createValidationRuntime({
            extensionDir: tempDir,
            manifest: { chatCommands: [], paletteCommands: [] },
            log: collector.log,
        });

        validateBuild.validateVsixPackage('0.5.2', reporter, runtime);

        expect(reporter.getCounts().warnCount).toBe(1);
        expect(reporter.getCounts().failCount).toBe(0);
        expect(collector.lines.some((line) => line.includes('No VSIX file found'))).toBe(true);

        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('returns the same verdict on win32 and linux for identical inputs', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-parity-'));
        fs.mkdirSync(path.join(tempDir, 'out'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, 'out', 'extension.js'), '// built', 'utf-8');
        fs.writeFileSync(path.join(tempDir, 'out', 'utils.js'), '// built', 'utf-8');
        fs.writeFileSync(path.join(tempDir, 'package.json'), JSON.stringify({ version: '0.5.2', contributes: {} }), 'utf-8');

        const winLog = createLogCollector();
        const linuxLog = createLogCollector();
        const runtimeOverrides = {
            extensionDir: tempDir,
            manifest: { chatCommands: [], paletteCommands: [] },
            getBundleAssetSpecs: () => [],
            skipTests: true,
        };

        const winExit = validateBuild.main({ ...runtimeOverrides, platform: 'win32', log: winLog.log });
        const linuxExit = validateBuild.main({ ...runtimeOverrides, platform: 'linux', log: linuxLog.log });

        expect(winExit).toBe(linuxExit);
        expect(winLog.lines.at(-1)).toBe(linuxLog.lines.at(-1));

        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('reports missing bundled directories as readable failures instead of throwing', () => {
        const collector = createLogCollector();
        const reporter = validateBuild.createReporter(collector.log);
        const runtime = validateBuild.createValidationRuntime({
            log: collector.log,
            manifest: { chatCommands: [], paletteCommands: [] },
            getBundleAssetSpecs: () => [{ type: 'skill', name: 'literature-review' }],
            evaluateAssetSync: () => ({
                missingSources: [],
                missingDestinations: [{ type: 'skill', name: 'literature-review' }],
                outdated: [],
                synced: [],
            }),
        });

        validateBuild.validateAssetGroup('📖 V2: Skills Sync', 'skill', reporter, runtime);

        expect(reporter.getCounts().failCount).toBe(1);
        expect(collector.lines.some((line) => line.includes('Bundled skill: literature-review missing'))).toBe(true);
    });

    it('shell wrappers delegate to the shared validate-build.cjs entrypoint', () => {
        const shellWrapper = fs.readFileSync(validateShellPath, 'utf-8');
        const powerShellWrapper = fs.readFileSync(validatePowerShellPath, 'utf-8');

        expect(shellWrapper).toContain('validate-build.cjs');
        expect(powerShellWrapper).toContain('validate-build.cjs');
        expect(shellWrapper).not.toContain('\nfi');
    });

    it('package.json validate script routes through the platform launcher', () => {
        const pkg = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
        expect(pkg.scripts.validate).toBe('node ./scripts/run-validate-build.cjs');
    });

    it('build.sh delegates bundling through npm scripts rather than inline asset lists', () => {
        const buildScript = fs.readFileSync(buildScriptPath, 'utf-8');

        expect(buildScript).toContain('npm run bundle:sync');
        expect(buildScript).toContain('npm run bundle:sync-python');
        expect(buildScript).toContain('npm run validate -- --skip-tests');
        expect(buildScript).not.toContain('BUNDLED_SKILLS=(');
        expect(buildScript).not.toContain('BUNDLED_PROMPTS=(');
        expect(buildScript).not.toContain('BUNDLED_AGENTS=(');
        expect(buildScript).not.toContain('for skill in literature-review');
        expect(buildScript).not.toContain('for prompt in mdpaper.write-paper');
    });
});
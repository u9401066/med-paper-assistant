import { describe, expect, it } from 'vitest';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

const extensionRoot = path.resolve(__dirname, '..', '..');
const buildScriptPath = path.join(extensionRoot, 'scripts', 'build.sh');
const packageJsonPath = path.join(extensionRoot, 'package.json');
const validateShellPath = path.join(extensionRoot, 'scripts', 'validate-build.sh');
const validatePowerShellPath = path.join(extensionRoot, 'scripts', 'validate-build.ps1');
const bundleAssets = require('../../scripts/bundle-assets.cjs');
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

    it('prefers the VSIX matching package.json when multiple artifacts exist', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-multi-vsix-'));
        const collector = createLogCollector();
        const reporter = validateBuild.createReporter(collector.log);

        fs.writeFileSync(path.join(tempDir, 'medpaper-assistant-0.7.0.vsix'), 'old', 'utf-8');
        fs.writeFileSync(path.join(tempDir, 'medpaper-assistant-0.7.2.vsix'), 'new', 'utf-8');

        const runtime = validateBuild.createValidationRuntime({
            extensionDir: tempDir,
            manifest: { chatCommands: [], paletteCommands: [] },
            log: collector.log,
        });

        validateBuild.validateVsixPackage('0.7.2', reporter, runtime);

        expect(reporter.getCounts().warnCount).toBe(0);
        expect(collector.lines.some((line) => line.includes('medpaper-assistant-0.7.2.vsix'))).toBe(true);
        expect(collector.lines.some((line) => line.includes('VSIX version matches package.json: 0.7.2'))).toBe(true);

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
            getCheckSpecs: () => [],
            skipTests: true,
            skipToolSurfaceAuthority: true,
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

    it('validate-build checks bundled python sources through check specs', () => {
        const collector = createLogCollector();
        const reporter = validateBuild.createReporter(collector.log);
        const runtime = validateBuild.createValidationRuntime({
            log: collector.log,
            manifest: { chatCommands: [], paletteCommands: [] },
            getBundleAssetSpecs: () => [],
            getCheckSpecs: () => [{ type: 'python-source', name: 'med_paper_assistant' }],
            evaluateAssetSync: (specs: Array<{ type: string; name: string }>) => ({
                missingSources: [],
                missingDestinations: [],
                outdated: specs.filter((spec) => spec.type === 'python-source'),
                synced: [],
            }),
        });

        validateBuild.validateAssetGroup(
            '🐍 V3d: Bundled Python Sync',
            'python-source',
            reporter,
            runtime,
            'check',
        );

        expect(reporter.getCounts().warnCount).toBe(1);
        expect(collector.lines.some((line) => line.includes('python-source: med_paper_assistant outdated'))).toBe(true);
    });

    it('reports tool-surface authority doc drift as a readable failure', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-tool-authority-'));
        const repoRoot = path.join(tempDir, 'repo');
        const extensionDir = path.join(repoRoot, 'vscode-extension');

        fs.mkdirSync(path.join(repoRoot, '.claude', 'skills', 'demo'), { recursive: true });
        fs.mkdirSync(path.join(repoRoot, '.github', 'prompts'), { recursive: true });
        fs.mkdirSync(extensionDir, { recursive: true });

        fs.writeFileSync(path.join(repoRoot, '.claude', 'skills', 'demo', 'SKILL.md'), '# demo', 'utf-8');
        fs.writeFileSync(path.join(repoRoot, '.github', 'prompts', 'demo.prompt.md'), '# demo', 'utf-8');
        fs.writeFileSync(path.join(repoRoot, 'README.md'), 'no authority snippet here', 'utf-8');
        fs.writeFileSync(
            path.join(repoRoot, 'tool-surface-authority.json'),
            JSON.stringify({
                repository: { skills: 1, promptWorkflows: 1 },
                bundle: {
                    skills: 0,
                    promptWorkflows: 0,
                    agents: 0,
                    templates: 0,
                    supportFiles: 0,
                    chatCommands: 0,
                    paletteCommands: 0,
                },
                docs: {
                    'README.md': ['expected authority snippet'],
                },
            }),
            'utf-8',
        );
        fs.writeFileSync(
            path.join(extensionDir, 'package.json'),
            JSON.stringify({ contributes: { chatParticipants: [{ commands: [] }], commands: [] } }),
            'utf-8',
        );

        const collector = createLogCollector();
        const reporter = validateBuild.createReporter(collector.log);
        const runtime = validateBuild.createValidationRuntime({
            extensionDir,
            repoRoot,
            log: collector.log,
            manifest: {
                skills: [],
                prompts: [],
                agents: [],
                templates: [],
                supportFiles: [],
                chatCommands: [],
                paletteCommands: [],
            },
        });

        validateBuild.validateToolSurfaceAuthority(reporter, runtime);

        expect(reporter.getCounts().failCount).toBe(1);
        expect(collector.lines.some((line) => line.includes('README.md missing authority snippet'))).toBe(true);

        fs.rmSync(tempDir, { recursive: true, force: true });
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

    it('bundle drift check covers python source mirrors', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-python-drift-'));
        const repoRoot = path.join(tempDir, 'repo');
        const extensionDir = path.join(repoRoot, 'vscode-extension');
        const sourceDir = path.join(repoRoot, 'src', 'pkg');
        const bundledDir = path.join(extensionDir, 'bundled', 'tool', 'pkg');

        fs.mkdirSync(sourceDir, { recursive: true });
        fs.mkdirSync(bundledDir, { recursive: true });
        fs.writeFileSync(path.join(sourceDir, '__init__.py'), 'VALUE = 1\n', 'utf-8');
        fs.writeFileSync(path.join(bundledDir, '__init__.py'), 'VALUE = 2\n', 'utf-8');

        const context = {
            extensionDir,
            repoRoot,
            manifest: {
                skills: [],
                prompts: [],
                agents: [],
                templates: [],
                supportFiles: [],
                pythonSources: [
                    {
                        name: 'pkg',
                        source: 'src/pkg',
                        destination: 'bundled/tool/pkg',
                        required: true,
                    },
                ],
            },
        };
        const errors: string[] = [];

        const specs = bundleAssets.getCheckSpecs(context);
        const report = bundleAssets.evaluateAssetSync(specs);
        const exitCode = bundleAssets.runCheckCommand(context, {
            log: () => {},
            error: (message: string) => errors.push(message),
        });

        expect(specs).toHaveLength(1);
        expect(specs[0].type).toBe('python-source');
        expect(report.outdated).toHaveLength(1);
        expect(report.outdated[0].type).toBe('python-source');
        expect(exitCode).toBe(1);
        expect(errors.some((line) => line.includes('python-source: pkg'))).toBe(true);

        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('bundle drift check skips missing optional python sources', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-python-optional-'));
        const repoRoot = path.join(tempDir, 'repo');
        const extensionDir = path.join(repoRoot, 'vscode-extension');

        fs.mkdirSync(extensionDir, { recursive: true });

        const context = {
            extensionDir,
            repoRoot,
            manifest: {
                skills: [],
                prompts: [],
                agents: [],
                templates: [],
                supportFiles: [],
                pythonSources: [
                    {
                        name: 'cgu',
                        source: 'integrations/cgu/src/cgu',
                        destination: 'bundled/tool/cgu',
                        required: false,
                    },
                ],
            },
        };

        const specs = bundleAssets.getCheckSpecs(context);
        const report = bundleAssets.evaluateAssetSync(specs);
        const exitCode = bundleAssets.runCheckCommand(context, {
            log: () => {},
            error: () => {},
        });

        expect(specs).toHaveLength(1);
        expect(specs[0].type).toBe('python-source');
        expect(report.missingSources).toHaveLength(0);
        expect(report.missingDestinations).toHaveLength(0);
        expect(report.outdated).toHaveLength(0);
        expect(exitCode).toBe(0);

        fs.rmSync(tempDir, { recursive: true, force: true });
    });
});

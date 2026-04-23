const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const {
    evaluateAssetSync,
    formatSpec,
    getBundleAssetSpecs,
    getCheckSpecs,
    getExtensionDir,
    loadBundleManifest,
} = require('./bundle-assets.cjs');

function createReporter(log = console.log) {
    let passCount = 0;
    let failCount = 0;
    let warnCount = 0;

    return {
        pass(message) {
            log(`  ✅ ${message}`);
            passCount += 1;
        },
        fail(message) {
            log(`  ❌ ${message}`);
            failCount += 1;
        },
        warn(message) {
            log(`  ⚠️  ${message}`);
            warnCount += 1;
        },
        getCounts() {
            return { passCount, failCount, warnCount };
        },
        printSummary() {
            log('');
            log('============================================');
            log('📊 Validation Summary');
            log(`  ✅ Passed: ${passCount}`);
            log(`  ⚠️  Warnings: ${warnCount}`);
            log(`  ❌ Failed: ${failCount}`);
            log('');

            if (failCount > 0) {
                log('❌ BUILD VALIDATION FAILED');
                return 1;
            }

            if (warnCount > 0) {
                log('⚠️  BUILD OK with warnings');
                return 0;
            }

            log('✅ BUILD VALIDATION PASSED');
            return 0;
        },
    };
}

function createValidationRuntime(overrides = {}) {
    const extensionDir = overrides.extensionDir ?? getExtensionDir();
    return {
        extensionDir,
        repoRoot: overrides.repoRoot ?? path.resolve(extensionDir, '..'),
        manifest: overrides.manifest ?? loadBundleManifest(extensionDir),
        skipTests: overrides.skipTests ?? process.argv.includes('--skip-tests'),
        skipToolSurfaceAuthority: overrides.skipToolSurfaceAuthority ?? false,
        fs: overrides.fs ?? fs,
        log: overrides.log ?? console.log,
        spawnSync: overrides.spawnSync ?? spawnSync,
        platform: overrides.platform ?? process.platform,
        evaluateAssetSync: overrides.evaluateAssetSync ?? evaluateAssetSync,
        getBundleAssetSpecs: overrides.getBundleAssetSpecs ?? getBundleAssetSpecs,
        getCheckSpecs: overrides.getCheckSpecs ?? getCheckSpecs,
    };
}

function formatFileSize(bytes) {
    if (bytes >= 1024 * 1024) {
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    if (bytes >= 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${bytes} B`;
}

function validateAssetGroup(title, type, reporter, runtime, specSet = 'bundle') {
    runtime.log('');
    runtime.log(title);

    const getSpecs = specSet === 'check'
        ? runtime.getCheckSpecs
        : runtime.getBundleAssetSpecs;

    const report = runtime.evaluateAssetSync(
        getSpecs({
            extensionDir: runtime.extensionDir,
            repoRoot: runtime.repoRoot,
            manifest: runtime.manifest,
        }).filter((spec) => spec.type === type),
    );

    for (const spec of report.missingSources) {
        reporter.fail(`Source ${formatSpec(spec)} missing`);
    }

    for (const spec of report.missingDestinations) {
        reporter.fail(`Bundled ${formatSpec(spec)} missing`);
    }

    for (const spec of report.outdated) {
        reporter.warn(`${formatSpec(spec)} outdated`);
    }

    for (const spec of report.synced) {
        reporter.pass(`${formatSpec(spec)} synced`);
    }
}

function validateCompilation(reporter, runtime) {
    runtime.log('🔍 MedPaper VSX Extension Build Validation');
    runtime.log('============================================');
    runtime.log('');
    runtime.log('📦 V1: TypeScript Compilation');

    const expectedOutputs = ['out/extension.js', 'out/utils.js'];
    for (const relativePath of expectedOutputs) {
        const fullPath = path.join(runtime.extensionDir, relativePath);
        if (runtime.fs.existsSync(fullPath)) {
            reporter.pass(`${path.basename(relativePath)} exists`);
        } else {
            reporter.fail(`${path.basename(relativePath)} missing — run 'npm run compile'`);
        }
    }
}

function readPackageJson(runtime) {
    const packageJsonPath = path.join(runtime.extensionDir, 'package.json');
    try {
        return {
            packageJson: JSON.parse(runtime.fs.readFileSync(packageJsonPath, 'utf-8')),
            error: null,
        };
    } catch (error) {
        if (error instanceof SyntaxError) {
            return {
                packageJson: null,
                error: `Invalid package.json JSON: ${error.message}`,
            };
        }

        const message = error instanceof Error ? error.message : String(error);
        return {
            packageJson: null,
            error: `Unable to read package.json: ${message}`,
        };
    }
}

function loadToolSurfaceAuthority(runtime) {
    const authorityPath = path.join(runtime.repoRoot, 'tool-surface-authority.json');
    try {
        return {
            authority: JSON.parse(runtime.fs.readFileSync(authorityPath, 'utf-8')),
            error: null,
        };
    } catch (error) {
        if (error instanceof SyntaxError) {
            return {
                authority: null,
                error: `Invalid tool-surface-authority.json JSON: ${error.message}`,
            };
        }

        const message = error instanceof Error ? error.message : String(error);
        return {
            authority: null,
            error: `Unable to read tool-surface-authority.json: ${message}`,
        };
    }
}

function countRepositorySkills(runtime) {
    const skillsDir = path.join(runtime.repoRoot, '.claude', 'skills');
    return runtime.fs.readdirSync(skillsDir, { withFileTypes: true })
        .filter((entry) => entry.isDirectory())
        .filter((entry) => runtime.fs.existsSync(path.join(skillsDir, entry.name, 'SKILL.md')))
        .length;
}

function countRepositoryPromptWorkflows(runtime) {
    const promptsDir = path.join(runtime.repoRoot, '.github', 'prompts');
    return runtime.fs.readdirSync(promptsDir)
        .filter((entry) => entry.endsWith('.prompt.md'))
        .length;
}

function validateToolSurfaceAuthority(reporter, runtime) {
    runtime.log('');
    runtime.log('🧭 V3e: Tool Surface Authority');

    const { authority, error } = loadToolSurfaceAuthority(runtime);
    if (!authority || error) {
        reporter.fail(error ?? 'Unable to load tool-surface authority');
        return;
    }

    const authorityChecks = [
        ['Repository skills', countRepositorySkills(runtime), authority.repository?.skills],
        ['Repository prompt workflows', countRepositoryPromptWorkflows(runtime), authority.repository?.promptWorkflows],
        ['Bundled skills', runtime.manifest.skills?.length ?? 0, authority.bundle?.skills],
        ['Bundled prompt workflows', runtime.manifest.prompts?.length ?? 0, authority.bundle?.promptWorkflows],
        ['Bundled agents', runtime.manifest.agents?.length ?? 0, authority.bundle?.agents],
        ['Bundled templates', runtime.manifest.templates?.length ?? 0, authority.bundle?.templates],
        ['Bundled support files', runtime.manifest.supportFiles?.length ?? 0, authority.bundle?.supportFiles],
        ['Bundled chat commands', runtime.manifest.chatCommands?.length ?? 0, authority.bundle?.chatCommands],
        ['Bundled palette commands', runtime.manifest.paletteCommands?.length ?? 0, authority.bundle?.paletteCommands],
    ];

    for (const [label, actual, expected] of authorityChecks) {
        if (actual === expected) {
            reporter.pass(`${label}: ${actual}`);
        } else {
            reporter.fail(`${label}: expected ${expected}, got ${actual}`);
        }
    }

    const { packageJson, error: packageError } = readPackageJson(runtime);
    if (!packageJson || packageError) {
        reporter.warn(`Tool surface authority skipped package.json checks (${packageError ?? 'package.json unavailable'})`);
    } else {
        const packageChatCommands = packageJson.contributes?.chatParticipants?.[0]?.commands?.length ?? 0;
        const packagePaletteCommands = packageJson.contributes?.commands?.length ?? 0;

        if (packageChatCommands === authority.bundle?.chatCommands) {
            reporter.pass(`package.json chat commands: ${packageChatCommands}`);
        } else {
            reporter.fail(`package.json chat commands: expected ${authority.bundle?.chatCommands}, got ${packageChatCommands}`);
        }

        if (packagePaletteCommands === authority.bundle?.paletteCommands) {
            reporter.pass(`package.json palette commands: ${packagePaletteCommands}`);
        } else {
            reporter.fail(`package.json palette commands: expected ${authority.bundle?.paletteCommands}, got ${packagePaletteCommands}`);
        }
    }

    for (const [relativePath, snippets] of Object.entries(authority.docs ?? {})) {
        const fullPath = path.join(runtime.repoRoot, relativePath);

        if (!runtime.fs.existsSync(fullPath)) {
            reporter.fail(`Authority doc missing: ${relativePath}`);
            continue;
        }

        const content = runtime.fs.readFileSync(fullPath, 'utf-8');
        const missingSnippets = snippets.filter((snippet) => !content.includes(snippet));
        if (missingSnippets.length > 0) {
            for (const snippet of missingSnippets) {
                reporter.fail(`${relativePath} missing authority snippet: ${snippet}`);
            }
            continue;
        }

        reporter.pass(`Docs authority synced: ${relativePath}`);
    }
}

function validatePackageJson(reporter, runtime) {
    runtime.log('');
    runtime.log('📄 V4: Package.json Consistency');

    const { packageJson, error } = readPackageJson(runtime);
    if (!packageJson || error) {
        reporter.fail(error ?? 'Unable to read package.json');
        return '';
    }

    const version = String(packageJson.version ?? '');

    if (/^\d+\.\d+\.\d+$/.test(version)) {
        reporter.pass(`Version format valid: ${version}`);
    } else {
        reporter.fail(`Invalid version format: ${version}`);
    }

    const chatCommands = packageJson.contributes?.chatParticipants?.[0]?.commands?.map((command) => command.name) ?? [];
    for (const commandName of runtime.manifest.chatCommands ?? []) {
        if (chatCommands.includes(commandName)) {
            reporter.pass(`Chat command: /${commandName}`);
        } else {
            reporter.fail(`Missing chat command: /${commandName}`);
        }
    }

    const paletteCommands = packageJson.contributes?.commands?.map((command) => command.command) ?? [];
    for (const commandId of runtime.manifest.paletteCommands ?? []) {
        if (paletteCommands.includes(commandId)) {
            reporter.pass(`Palette command: ${commandId}`);
        } else {
            reporter.fail(`Missing palette command: ${commandId}`);
        }
    }

    return version;
}

function validateVsixPackage(version, reporter, runtime) {
    runtime.log('');
    runtime.log('📦 V5: VSIX Package');

    const vsixFiles = runtime.fs.readdirSync(runtime.extensionDir)
        .filter((entry) => entry.endsWith('.vsix'))
        .map((entry) => path.join(runtime.extensionDir, entry));

    if (vsixFiles.length === 0) {
        reporter.warn("No VSIX file found (run 'npm run package')");
        return;
    }

    const versionNeedle = `-${version}.vsix`;
    const vsixFile = vsixFiles.find((filePath) => path.basename(filePath).includes(versionNeedle))
        ?? vsixFiles[0];
    const stats = runtime.fs.statSync(vsixFile);
    reporter.pass(`VSIX exists: ${path.basename(vsixFile)} (${formatFileSize(stats.size)})`);

    const match = path.basename(vsixFile).match(/(\d+\.\d+\.\d+)/);
    if (!match) {
        reporter.warn('Unable to parse VSIX version from file name');
        return;
    }

    if (match[1] === version) {
        reporter.pass(`VSIX version matches package.json: ${match[1]}`);
    } else {
        reporter.warn(`VSIX version (${match[1]}) != package.json (${version})`);
    }
}

function validateTests(reporter, runtime) {
    runtime.log('');
    runtime.log('🧪 V6: Unit Tests');

    if (runtime.skipTests) {
        reporter.pass('Unit tests skipped by flag');
        return;
    }

    const vitestBin = runtime.platform === 'win32'
        ? path.join(runtime.extensionDir, 'node_modules', '.bin', 'vitest.cmd')
        : path.join(runtime.extensionDir, 'node_modules', '.bin', 'vitest');

    if (!runtime.fs.existsSync(vitestBin)) {
        reporter.warn("vitest not installed — run 'npm install'");
        return;
    }

    const result = runtime.spawnSync('npx', ['vitest', 'run', '--reporter=dot'], {
        cwd: runtime.extensionDir,
        encoding: 'utf-8',
        shell: runtime.platform === 'win32',
    });

    const output = `${result.stdout ?? ''}\n${result.stderr ?? ''}`;
    if (result.status === 0 && /Tests/i.test(output)) {
        const testLine = output.split(/\r?\n/).find((line) => /Tests/i.test(line));
        if (testLine) {
            reporter.pass(`Unit tests: ${testLine.trim()}`);
        } else {
            reporter.pass('Unit tests passed');
        }
        return;
    }

    reporter.fail('Unit tests failed');
    if (output.trim()) {
        runtime.log(output.trim());
    }
}

function main(overrides = {}) {
    const runtime = createValidationRuntime(overrides);
    const reporter = createReporter(runtime.log);

    validateCompilation(reporter, runtime);
    validateAssetGroup('📖 V2: Skills Sync', 'skill', reporter, runtime);
    validateAssetGroup('📋 V3: Prompts Sync', 'prompt', reporter, runtime);
    validateAssetGroup('📋 V3a: Support Files Sync', 'support-file', reporter, runtime);
    validateAssetGroup('📄 V3b: Templates Sync', 'template', reporter, runtime);
    validateAssetGroup('🤖 V3c: Agents Sync', 'agent', reporter, runtime);
    validateAssetGroup('🐍 V3d: Bundled Python Sync', 'python-source', reporter, runtime, 'check');
    if (!runtime.skipToolSurfaceAuthority) {
        validateToolSurfaceAuthority(reporter, runtime);
    }
    const version = validatePackageJson(reporter, runtime);
    validateVsixPackage(version, reporter, runtime);
    validateTests(reporter, runtime);
    return reporter.printSummary();
}

if (require.main === module) {
    process.exit(main());
}

module.exports = {
    createReporter,
    createValidationRuntime,
    formatFileSize,
    loadToolSurfaceAuthority,
    main,
    readPackageJson,
    validateAssetGroup,
    validateCompilation,
    validatePackageJson,
    validateToolSurfaceAuthority,
    validateTests,
    validateVsixPackage,
};

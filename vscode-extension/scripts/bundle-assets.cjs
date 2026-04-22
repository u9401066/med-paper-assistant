const fs = require('node:fs');
const path = require('node:path');

function getExtensionDir() {
    return path.resolve(__dirname, '..');
}

function getRepoRoot(extensionDir = getExtensionDir()) {
    return path.resolve(extensionDir, '..');
}

function loadBundleManifest(extensionDir = getExtensionDir()) {
    const manifestPath = path.join(extensionDir, 'bundle-manifest.json');
    return JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
}

function createContext() {
    const extensionDir = getExtensionDir();
    return {
        extensionDir,
        repoRoot: getRepoRoot(extensionDir),
        manifest: loadBundleManifest(extensionDir),
    };
}

function createAssetSpec(type, name, source, destination) {
    return { type, name, source, destination };
}

function getBundleAssetSpecs(context = createContext()) {
    const { extensionDir, repoRoot, manifest } = context;

    const skills = manifest.skills.map((skill) => createAssetSpec(
        'skill',
        skill,
        path.join(repoRoot, '.claude', 'skills', skill, 'SKILL.md'),
        path.join(extensionDir, 'skills', skill, 'SKILL.md'),
    ));

    const prompts = manifest.prompts.map((prompt) => createAssetSpec(
        'prompt',
        prompt,
        path.join(repoRoot, '.github', 'prompts', `${prompt}.prompt.md`),
        path.join(extensionDir, 'prompts', `${prompt}.prompt.md`),
    ));

    const agents = manifest.agents.map((agent) => createAssetSpec(
        'agent',
        agent,
        path.join(repoRoot, '.github', 'agents', `${agent}.agent.md`),
        path.join(extensionDir, 'agents', `${agent}.agent.md`),
    ));

    const templates = manifest.templates.map((template) => createAssetSpec(
        'template',
        template,
        path.join(repoRoot, 'templates', template),
        path.join(extensionDir, 'templates', template),
    ));

    const supportFiles = manifest.supportFiles.map((file) => createAssetSpec(
        'support-file',
        file.name,
        path.join(repoRoot, file.source),
        path.join(extensionDir, file.destination),
    ));

    return [...skills, ...prompts, ...agents, ...templates, ...supportFiles];
}

function getPythonSourceSpecs(context = createContext()) {
    const { extensionDir, repoRoot, manifest } = context;
    return manifest.pythonSources.map((entry) => ({
        type: 'python-source',
        name: entry.name,
        source: path.join(repoRoot, entry.source),
        destination: path.join(extensionDir, entry.destination),
        required: entry.required !== false,
    }));
}

function getCheckSpecs(context = createContext()) {
    return [...getBundleAssetSpecs(context), ...getPythonSourceSpecs(context)];
}

function compareFileContents(leftPath, rightPath) {
    return fs.readFileSync(leftPath).equals(fs.readFileSync(rightPath));
}

function shouldIgnoreDirectoryEntry(dirEntry) {
    return dirEntry.name === '__pycache__' || dirEntry.name.endsWith('.pyc');
}

function collectDirectoryEntries(rootDir, relativePath = '') {
    const currentDir = relativePath ? path.join(rootDir, relativePath) : rootDir;
    const dirEntries = fs.readdirSync(currentDir, { withFileTypes: true })
        .filter((dirEntry) => !shouldIgnoreDirectoryEntry(dirEntry))
        .sort((left, right) => left.name.localeCompare(right.name));
    const entries = [];

    for (const dirEntry of dirEntries) {
        const entryPath = relativePath ? path.join(relativePath, dirEntry.name) : dirEntry.name;
        const normalizedPath = entryPath.split(path.sep).join('/');

        if (dirEntry.isDirectory()) {
            entries.push({ path: normalizedPath, type: 'dir' });
            entries.push(...collectDirectoryEntries(rootDir, entryPath));
            continue;
        }

        entries.push({ path: normalizedPath, type: 'file' });
    }

    return entries;
}

function compareDirectoryContents(leftDir, rightDir) {
    const leftEntries = collectDirectoryEntries(leftDir);
    const rightEntries = collectDirectoryEntries(rightDir);

    if (leftEntries.length !== rightEntries.length) {
        return false;
    }

    for (let index = 0; index < leftEntries.length; index += 1) {
        const leftEntry = leftEntries[index];
        const rightEntry = rightEntries[index];

        if (leftEntry.path !== rightEntry.path || leftEntry.type !== rightEntry.type) {
            return false;
        }

        if (leftEntry.type === 'file') {
            if (!compareFileContents(path.join(leftDir, leftEntry.path), path.join(rightDir, rightEntry.path))) {
                return false;
            }
        }
    }

    return true;
}

function compareSpecContents(spec) {
    const sourceStats = fs.statSync(spec.source);
    const destinationStats = fs.statSync(spec.destination);

    if (sourceStats.isDirectory() && destinationStats.isDirectory()) {
        return compareDirectoryContents(spec.source, spec.destination);
    }

    if (sourceStats.isFile() && destinationStats.isFile()) {
        return compareFileContents(spec.source, spec.destination);
    }

    return false;
}

function ensureParentDirectory(filePath) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function formatSpec(spec) {
    return `${spec.type}: ${spec.name}`;
}

function evaluateAssetSync(specs) {
    const report = {
        missingSources: [],
        missingDestinations: [],
        outdated: [],
        synced: [],
    };

    for (const spec of specs) {
        if (!fs.existsSync(spec.source)) {
            if (spec.required === false) {
                continue;
            }
            report.missingSources.push(spec);
            continue;
        }

        if (!fs.existsSync(spec.destination)) {
            report.missingDestinations.push(spec);
            continue;
        }

        if (compareSpecContents(spec)) {
            report.synced.push(spec);
            continue;
        }

        report.outdated.push(spec);
    }

    return report;
}

function syncAssetSpecs(specs) {
    const copied = [];
    const missingSources = [];

    for (const spec of specs) {
        if (!fs.existsSync(spec.source)) {
            missingSources.push(spec);
            continue;
        }

        ensureParentDirectory(spec.destination);
        fs.copyFileSync(spec.source, spec.destination);
        copied.push(spec);
    }

    return { copied, missingSources };
}

function syncPythonSourceSpecs(specs) {
    const copied = [];
    const missingSources = [];
    const skippedOptional = [];

    for (const spec of specs) {
        if (!fs.existsSync(spec.source)) {
            if (spec.required === false) {
                skippedOptional.push(spec);
                continue;
            }
            missingSources.push(spec);
            continue;
        }

        fs.rmSync(spec.destination, { recursive: true, force: true });
        ensureParentDirectory(spec.destination);
        fs.cpSync(spec.source, spec.destination, { recursive: true });
        copied.push(spec);
    }

    return { copied, missingSources, skippedOptional };
}

function printProblemList(header, specs, log = console.error) {
    if (specs.length === 0) {
        return;
    }

    log(header);
    for (const spec of specs) {
        log(`  - ${formatSpec(spec)}`);
    }
}

function runCheckCommand(context = createContext(), output = console) {
    const specs = getCheckSpecs(context);
    const report = evaluateAssetSync(specs);
    const hasProblems = report.missingSources.length > 0 || report.missingDestinations.length > 0 || report.outdated.length > 0;

    if (!hasProblems) {
        output.log(`✅ Committed bundle is in sync (${report.synced.length} assets).`);
        return 0;
    }

    printProblemList('❌ Missing source assets:', report.missingSources, output.error ?? console.error);
    printProblemList('❌ Missing bundled assets:', report.missingDestinations, output.error ?? console.error);
    printProblemList('❌ Outdated bundled assets:', report.outdated, output.error ?? console.error);
    return 1;
}

function runSyncCommand() {
    const specs = getBundleAssetSpecs();
    const { copied, missingSources } = syncAssetSpecs(specs);

    if (missingSources.length > 0) {
        printProblemList('❌ Unable to sync missing source assets:', missingSources);
        return 1;
    }

    console.log(`✅ Synced ${copied.length} bundled assets from manifest.`);
    return 0;
}

function runSyncPythonCommand() {
    const specs = getPythonSourceSpecs();
    const { copied, missingSources, skippedOptional } = syncPythonSourceSpecs(specs);

    if (missingSources.length > 0) {
        printProblemList('❌ Unable to sync missing Python sources:', missingSources);
        return 1;
    }

    if (skippedOptional.length > 0) {
        printProblemList('⚠️ Skipping optional Python sources:', skippedOptional);
    }

    console.log(`✅ Synced ${copied.length} Python source bundles from manifest.`);
    return 0;
}

function main() {
    const command = process.argv[2];
    switch (command) {
        case 'check':
            return runCheckCommand();
        case 'sync':
            return runSyncCommand();
        case 'sync-python':
            return runSyncPythonCommand();
        default:
            console.error('Usage: node ./scripts/bundle-assets.cjs <check|sync|sync-python>');
            return 1;
    }
}

if (require.main === module) {
    process.exit(main());
}

module.exports = {
    collectDirectoryEntries,
    compareDirectoryContents,
    compareFileContents,
    compareSpecContents,
    createContext,
    evaluateAssetSync,
    formatSpec,
    getBundleAssetSpecs,
    getCheckSpecs,
    getExtensionDir,
    getPythonSourceSpecs,
    getRepoRoot,
    loadBundleManifest,
    runCheckCommand,
    syncAssetSpecs,
    syncPythonSourceSpecs,
};

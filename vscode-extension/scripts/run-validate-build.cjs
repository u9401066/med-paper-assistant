const { spawnSync } = require('node:child_process');
const path = require('node:path');

function getValidateScriptPath(platform = process.platform, scriptDir = __dirname) {
    const scriptName = platform === 'win32' ? 'validate-build.ps1' : 'validate-build.sh';
    return path.join(scriptDir, scriptName);
}

function buildLaunchArgs(argv = process.argv.slice(2), platform = process.platform, scriptDir = __dirname) {
    const validateScriptPath = getValidateScriptPath(platform, scriptDir);

    if (platform === 'win32') {
        return {
            command: 'powershell.exe',
            args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', validateScriptPath, ...argv],
        };
    }

    return {
        command: 'bash',
        args: [validateScriptPath, ...argv],
    };
}

function runValidateBuild({
    argv = process.argv.slice(2),
    platform = process.platform,
    scriptDir = __dirname,
    spawn = spawnSync,
    stderr = console.error,
} = {}) {
    const launch = buildLaunchArgs(argv, platform, scriptDir);
    const result = spawn(launch.command, launch.args, {
        stdio: 'inherit',
    });

    if (result.error) {
        stderr(`Failed to start validation command '${launch.command}': ${result.error.message}`);
        return 1;
    }

    return result.status ?? 1;
}

if (require.main === module) {
    process.exit(runValidateBuild());
}

module.exports = {
    buildLaunchArgs,
    getValidateScriptPath,
    runValidateBuild,
};
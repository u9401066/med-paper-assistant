#!/usr/bin/env node
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const expected = `${pkg.name}-${pkg.version}.vsix`;
const extensionId = `${pkg.publisher}.${pkg.name}`;
const vsixPath = path.join(root, expected);

function localCliEnvironment() {
  const remoteShellKeys = new Set([
    'REMOTE_CONTAINERS_IPC',
    'SSH_CLIENT',
    'SSH_CONNECTION',
    'SSH_TTY',
  ]);
  return Object.fromEntries(
    Object.entries(process.env).filter(
      ([key]) => !key.startsWith('VSCODE_') && !remoteShellKeys.has(key),
    ),
  );
}

if (!fs.existsSync(vsixPath)) {
  const candidates = fs.readdirSync(root).filter((name) => name.endsWith('.vsix')).sort();
  console.error(`Missing expected VSIX ${expected}. Found: ${candidates.join(', ') || 'none'}`);
  process.exit(1);
}
if (fs.statSync(vsixPath).size <= 0) {
  console.error(`VSIX ${expected} is empty.`);
  process.exit(1);
}

function usableCli(candidate, prefixArgs = []) {
  if (!candidate) return false;
  const rootProbeFlags = typeof process.getuid === 'function' && process.getuid() === 0
    ? ['--no-sandbox', '--user-data-dir', path.join(os.tmpdir(), 'medpaper-vscode-cli-probe')]
    : [];
  const result = spawnSync(candidate, [...prefixArgs, '--version', ...rootProbeFlags], {
    encoding: 'utf8',
    env: localCliEnvironment(),
  });
  return result.status === 0;
}

const cliCommand = process.env.VSCODE_CLI;
const cliPrefixArgs = [];
if (!cliCommand) {
  console.error(
    'VSCODE_CLI is required and must point to the pinned VS Code CLI download.',
  );
  process.exit(1);
}
if (!usableCli(cliCommand)) {
  console.error(`Pinned VS Code CLI is not executable: ${cliCommand}`);
  process.exit(1);
}

const smokeRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'medpaper-vsix-install-'));
const extensionsDir = path.join(smokeRoot, 'extensions');
const userDataDir = path.join(smokeRoot, 'user-data');
const rootFlags = typeof process.getuid === 'function' && process.getuid() === 0
  ? ['--no-sandbox']
  : [];
const profileFlags = [
  ...rootFlags,
  '--extensions-dir', extensionsDir,
  '--user-data-dir', userDataDir,
];

function runCli(args, capture = false) {
  const result = spawnSync(cliCommand, [...cliPrefixArgs, ...args, ...profileFlags], {
    encoding: 'utf8',
    stdio: capture ? 'pipe' : 'inherit',
    env: localCliEnvironment(),
  });
  if (result.status !== 0) {
    if (capture) {
      process.stderr.write(result.stdout || '');
      process.stderr.write(result.stderr || '');
    }
    throw new Error(`VS Code CLI failed (${result.status}): ${args.join(' ')}`);
  }
  return result.stdout || '';
}

try {
  runCli(['--install-extension', vsixPath, '--force']);
  const installed = runCli(['--list-extensions', '--show-versions'], true)
    .split(/\r?\n/)
    .map((line) => line.trim().toLowerCase())
    .filter(Boolean);
  const expectedListing = `${extensionId}@${pkg.version}`.toLowerCase();
  if (!installed.includes(expectedListing)) {
    throw new Error(`Installed extension list does not contain ${expectedListing}: ${installed.join(', ')}`);
  }

  const installedPackage = fs.readdirSync(extensionsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(extensionsDir, entry.name, 'package.json'))
    .find((candidate) => {
      if (!fs.existsSync(candidate)) return false;
      const metadata = JSON.parse(fs.readFileSync(candidate, 'utf8'));
      return metadata.publisher === pkg.publisher
        && metadata.name === pkg.name
        && metadata.version === pkg.version;
    });
  if (!installedPackage) {
    throw new Error(`Could not find installed ${expectedListing} package metadata.`);
  }
  const installedRoot = path.dirname(installedPackage);
  for (const relative of [
    'out/extension.js',
    'bundled/tool/med_paper_assistant/__init__.py',
    'bundled/tool/cgu/server.py',
  ]) {
    if (!fs.existsSync(path.join(installedRoot, relative))) {
      throw new Error(`Installed VSIX is missing ${relative}`);
    }
  }

  console.log(`VSIX install smoke passed: ${expectedListing}`);
} finally {
  fs.rmSync(smokeRoot, { recursive: true, force: true });
}

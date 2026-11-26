import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

import { buildFoamMcpCommand, findExecutableOnPath, FOAM_MCP_PACKAGE } from '../foamMcp';

const repositoryRoot = path.resolve(__dirname, '..', '..', '..');
const lock = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, 'mcp-integration-lock.json'), 'utf-8'),
);

const tempDirs: string[] = [];

afterEach(() => {
    while (tempDirs.length > 0) {
        const dir = tempDirs.pop();
        if (dir) {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    }
});

describe('Foam read-only MCP helper', () => {
    it('stays in sync with node_integrations.foam in mcp-integration-lock.json', () => {
        const canonical = lock.node_integrations.foam;
        expect(FOAM_MCP_PACKAGE.repository).toBe(canonical.repository);
        expect(FOAM_MCP_PACKAGE.package).toBe(canonical.package);
        expect(FOAM_MCP_PACKAGE.version).toBe(canonical.version);
        expect(FOAM_MCP_PACKAGE.env).toEqual(canonical.env);
    });

    it('builds the pinned npx foam-cli mcp workspace command', () => {
        const [command, args] = buildFoamMcpCommand('/tmp/research');
        expect(command).toBe('npx');
        expect(args).toEqual([
            '-y',
            `${FOAM_MCP_PACKAGE.package}@${FOAM_MCP_PACKAGE.version}`,
            'mcp',
            '--workspace',
            '/tmp/research',
        ]);
    });

    it('finds executables on POSIX and Windows PATHs and returns null when absent', () => {
        const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'foam-mcp-path-'));
        tempDirs.push(tmpDir);

        const posixBin = path.join(tmpDir, 'npx');
        fs.writeFileSync(posixBin, '#!/bin/sh\n', 'utf-8');
        expect(findExecutableOnPath('npx', tmpDir, 'linux', '')).toBe(posixBin);

        const winCmd = path.join(tmpDir, 'npx.CMD');
        fs.writeFileSync(winCmd, '@echo off\n', 'utf-8');
        expect(findExecutableOnPath('npx', tmpDir, 'win32', '.EXE;.CMD')).toBe(winCmd);

        expect(findExecutableOnPath('missing-tool', tmpDir, 'linux', '')).toBeNull();
        expect(findExecutableOnPath('npx', undefined, 'linux', '')).toBeNull();
    });
});

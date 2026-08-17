import { describe, expect, it } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';

import { MCP_INTEGRATION_PACKAGES } from '../mcpIntegrationPackages';

const repositoryRoot = path.resolve(__dirname, '..', '..', '..');
const lock = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, 'mcp-integration-lock.json'), 'utf-8'),
);

describe('VSIX MCP integration lock snapshot', () => {
    it('matches every canonical integration commit, version, SDK major, and entrypoint', () => {
        expect(Object.keys(MCP_INTEGRATION_PACKAGES).sort()).toEqual(
            Object.keys(lock.integrations).sort(),
        );

        for (const [name, packaged] of Object.entries(MCP_INTEGRATION_PACKAGES)) {
            const canonical = lock.integrations[name];
            expect(packaged.repository).toBe(canonical.repository);
            expect(packaged.commit).toBe(canonical.commit);
            expect(packaged.version).toBe(canonical.version);
            expect(packaged.sdkMajor).toBe(canonical.mcp_sdk_major);
            expect(packaged.entrypoint).toBe(canonical.entrypoint);
            expect(packaged.packageSource).toBe(canonical.package_source);
            if (canonical.package_subdirectory) {
                expect(packaged.packageSource).toContain(
                    `#subdirectory=${canonical.package_subdirectory}`,
                );
            }
        }
    });

    it('contains no SDK1 package snapshot', () => {
        expect(lock.policy.allow_mcp_v1_fallback).toBe(false);
        for (const packaged of Object.values(MCP_INTEGRATION_PACKAGES)) {
            expect(packaged.sdkMajor).toBe(2);
            expect(packaged.commit).toMatch(/^[0-9a-f]{40}$/);
        }
    });
});

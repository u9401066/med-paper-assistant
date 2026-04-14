import { describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const ciWorkflow = fs.readFileSync(path.join(repoRoot, '.github', 'workflows', 'ci.yml'), 'utf-8');
const releaseWorkflow = fs.readFileSync(path.join(repoRoot, '.github', 'workflows', 'release.yml'), 'utf-8');

describe('CI workflow bundle contract', () => {
    it('checks committed bundle drift before build-time sync', () => {
        const checkIndex = ciWorkflow.indexOf('npm run bundle:check');
        const syncIndex = ciWorkflow.indexOf('npm run bundle:sync');
        const validateIndex = ciWorkflow.indexOf('npm run validate');

        expect(checkIndex).toBeGreaterThan(-1);
        expect(syncIndex).toBeGreaterThan(-1);
        expect(validateIndex).toBeGreaterThan(-1);
        expect(checkIndex).toBeLessThan(syncIndex);
        expect(syncIndex).toBeLessThan(validateIndex);
    });

    it('uses shared bundle commands instead of inline copy loops', () => {
        expect(ciWorkflow).not.toContain('for skill in literature-review');
        expect(ciWorkflow).not.toContain('for prompt in mdpaper.write-paper');
    });
});

describe('Release workflow artifact contract', () => {
    it('builds artifacts once before publishing', () => {
        const driftIndex = releaseWorkflow.indexOf('vsx-bundle-drift:');
        const buildIndex = releaseWorkflow.indexOf('build-artifacts:');
        const pypiIndex = releaseWorkflow.indexOf('publish-pypi:');
        const vsxIndex = releaseWorkflow.indexOf('publish-vsx:');

        expect(releaseWorkflow).toContain('build-artifacts:');
        expect(releaseWorkflow).toMatch(/publish-pypi:[\s\S]*?needs:\s*\[validate,\s*build-artifacts\]/);
        expect(releaseWorkflow).toMatch(/publish-vsx:[\s\S]*?needs:\s*\[validate,\s*build-artifacts,\s*publish-pypi\]/);
        expect(driftIndex).toBeGreaterThan(-1);
        expect(buildIndex).toBeGreaterThan(driftIndex);
        expect(pypiIndex).toBeGreaterThan(buildIndex);
        expect(vsxIndex).toBeGreaterThan(pypiIndex);
    });

    it('uses shared bundle commands in drift and artifact jobs', () => {
        expect(releaseWorkflow).toContain('npm run bundle:check');
        expect(releaseWorkflow).toContain('npm run bundle:sync');
        expect(releaseWorkflow).toContain('npm run bundle:sync-python');
        expect(releaseWorkflow).not.toContain('for skill in literature-review');
        expect(releaseWorkflow).not.toContain('for prompt in mdpaper.write-paper');
    });
});

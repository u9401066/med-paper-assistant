import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import {
    copyMissingSkillReferences,
    hasMissingSkillReferences,
    listSkillReferenceFiles,
    loadSkillWithReferences,
} from '../skillReferences';
import { countMissingBundledItems } from '../extensionHelpers';
import { BUNDLED_SKILLS, validateBundledSkills } from '../utils';

const bundleAssets = require('../../scripts/bundle-assets.cjs');

function write(filePath: string, content: string): void {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content);
}

describe('skill references (progressive disclosure)', () => {
    let tmpDir: string;

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsx-skill-refs-'));
    });

    afterEach(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('lists only sorted markdown files under references/', () => {
        const skillDir = path.join(tmpDir, 'skill');
        write(path.join(skillDir, 'references', 'b.md'), 'b');
        write(path.join(skillDir, 'references', 'a.md'), 'a');
        write(path.join(skillDir, 'references', 'notes.txt'), 'ignored');
        write(path.join(skillDir, 'references', 'nested', 'c.md'), 'ignored');

        expect(listSkillReferenceFiles(skillDir)).toEqual(['a.md', 'b.md']);
        expect(listSkillReferenceFiles(path.join(tmpDir, 'missing'))).toEqual([]);
    });

    it('copies only missing reference files and never overwrites workspace edits', () => {
        const src = path.join(tmpDir, 'ext', 'skill');
        const dst = path.join(tmpDir, 'ws', 'skill');
        write(path.join(src, 'references', 'a.md'), 'bundled a');
        write(path.join(src, 'references', 'b.md'), 'bundled b');
        write(path.join(dst, 'references', 'a.md'), 'user edited a');

        expect(hasMissingSkillReferences(src, dst)).toBe(true);
        expect(copyMissingSkillReferences(src, dst)).toBe(1);
        expect(fs.readFileSync(path.join(dst, 'references', 'a.md'), 'utf-8')).toBe('user edited a');
        expect(fs.readFileSync(path.join(dst, 'references', 'b.md'), 'utf-8')).toBe('bundled b');
        expect(hasMissingSkillReferences(src, dst)).toBe(false);
        expect(copyMissingSkillReferences(src, dst)).toBe(0);
    });

    it('loads SKILL.md alone when a skill has no references', () => {
        write(path.join(tmpDir, 'plain', 'SKILL.md'), '# Plain');

        expect(loadSkillWithReferences(tmpDir, 'plain')).toBe('# Plain');
        expect(loadSkillWithReferences(tmpDir, 'absent')).toBeNull();
    });

    it('appends references in SKILL.md link order, then unlinked files alphabetically', () => {
        const skillDir = path.join(tmpDir, 'big');
        write(
            path.join(skillDir, 'SKILL.md'),
            '# Big\n\n[z](references/z.md) [m](references/m.md#anchor)\n',
        );
        write(path.join(skillDir, 'references', 'a.md'), 'AAA');
        write(path.join(skillDir, 'references', 'm.md'), 'MMM');
        write(path.join(skillDir, 'references', 'z.md'), 'ZZZ');

        const content = loadSkillWithReferences(tmpDir, 'big') as string;

        expect(content.startsWith('# Big')).toBe(true);
        expect(content.indexOf('ZZZ')).toBeLessThan(content.indexOf('MMM'));
        expect(content.indexOf('MMM')).toBeLessThan(content.indexOf('AAA'));
        expect(content).toContain('## Reference: references/a.md');
    });

    it('counts a skill as missing when only its references are absent in the workspace', () => {
        const extDir = path.join(tmpDir, 'ext');
        const wsDir = path.join(tmpDir, 'ws');
        write(path.join(extDir, 'skills', 'big', 'SKILL.md'), '# Big');
        write(path.join(extDir, 'skills', 'big', 'references', 'a.md'), 'A');
        write(path.join(wsDir, '.claude', 'skills', 'big', 'SKILL.md'), '# Big');

        expect(countMissingBundledItems(wsDir, extDir, ['big'], [], [], []).missingSkills).toBe(1);

        write(path.join(wsDir, '.claude', 'skills', 'big', 'references', 'a.md'), 'A');
        expect(countMissingBundledItems(wsDir, extDir, ['big'], [], [], []).missingSkills).toBe(0);
    });

    it('validateBundledSkills reports missing and outdated reference files', () => {
        const srcDir = path.join(tmpDir, 'src-skills');
        const dstDir = path.join(tmpDir, 'dst-skills');
        const skill = BUNDLED_SKILLS[0];
        write(path.join(srcDir, skill, 'SKILL.md'), `# ${skill}`);
        write(path.join(srcDir, skill, 'references', 'a.md'), 'A');
        write(path.join(srcDir, skill, 'references', 'b.md'), 'B');
        write(path.join(dstDir, skill, 'SKILL.md'), `# ${skill}`);
        write(path.join(dstDir, skill, 'references', 'b.md'), 'stale');

        const result = validateBundledSkills(dstDir, srcDir);

        expect(result.missing).toContain(`${skill}/references/a.md`);
        expect(result.missing).toContain(`${skill}/references/b.md (outdated)`);
    });

    it('bundle-assets mirrors references/ directories as skill-references specs', () => {
        const repoRoot = path.join(tmpDir, 'repo');
        const extensionDir = path.join(repoRoot, 'vscode-extension');
        write(path.join(repoRoot, '.claude', 'skills', 'big', 'SKILL.md'), '# Big');
        write(path.join(repoRoot, '.claude', 'skills', 'big', 'references', 'a.md'), 'A');
        write(path.join(repoRoot, '.claude', 'skills', 'plain', 'SKILL.md'), '# Plain');
        const context = {
            extensionDir,
            repoRoot,
            manifest: {
                skills: ['big', 'plain'],
                prompts: [],
                agents: [],
                templates: [],
                supportFiles: [],
                pythonSources: [],
            },
        };

        const specs = bundleAssets.getBundleAssetSpecs(context);
        const referenceSpecs = specs.filter((spec: { type: string }) => spec.type === 'skill-references');

        expect(referenceSpecs).toHaveLength(1);
        expect(referenceSpecs[0].name).toBe('big/references');

        const initial = bundleAssets.evaluateAssetSync(referenceSpecs);
        expect(initial.missingDestinations).toHaveLength(1);

        const { copied } = bundleAssets.syncAssetSpecs(specs);
        expect(copied).toHaveLength(3);
        expect(fs.readFileSync(path.join(extensionDir, 'skills', 'big', 'references', 'a.md'), 'utf-8')).toBe('A');
        expect(bundleAssets.evaluateAssetSync(specs).outdated).toHaveLength(0);

        // Stale files in the mirror are removed on the next sync.
        write(path.join(extensionDir, 'skills', 'big', 'references', 'stale.md'), 'old');
        expect(bundleAssets.evaluateAssetSync(referenceSpecs).outdated).toHaveLength(1);
        bundleAssets.syncAssetSpecs(specs);
        expect(fs.existsSync(path.join(extensionDir, 'skills', 'big', 'references', 'stale.md'))).toBe(false);
    });
});

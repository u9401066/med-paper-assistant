/**
 * Skill references — helpers for progressive-disclosure skills.
 *
 * A skill may keep SKILL.md as a concise entry point and ship detailed procedures
 * in a sibling `references/*.md` directory. These helpers carry that directory
 * alongside SKILL.md. They have NO dependency on the `vscode` API.
 */

import * as path from 'path';
import * as fs from 'fs';

const REFERENCE_LINK_PATTERN = /\]\(references\/([^)#\s]+\.md)/g;

/**
 * List the reference file names (references/*.md) shipped with a skill directory.
 */
export function listSkillReferenceFiles(skillDir: string): string[] {
    const referencesDir = path.join(skillDir, 'references');
    if (!fs.existsSync(referencesDir)) {
        return [];
    }

    return fs.readdirSync(referencesDir, { withFileTypes: true })
        .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
        .map((entry) => entry.name)
        .sort();
}

/**
 * Check whether the destination skill directory lacks any reference file of the source skill.
 */
export function hasMissingSkillReferences(srcSkillDir: string, dstSkillDir: string): boolean {
    return listSkillReferenceFiles(srcSkillDir).some(
        (name) => !fs.existsSync(path.join(dstSkillDir, 'references', name)),
    );
}

/**
 * Copy reference files that do not exist yet in the destination skill directory.
 *
 * @returns Number of reference files copied
 */
export function copyMissingSkillReferences(srcSkillDir: string, dstSkillDir: string): number {
    let copied = 0;
    for (const name of listSkillReferenceFiles(srcSkillDir)) {
        const dst = path.join(dstSkillDir, 'references', name);
        if (!fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(path.join(srcSkillDir, 'references', name), dst);
            copied++;
        }
    }
    return copied;
}

/**
 * Load a skill's SKILL.md followed by all of its references/*.md files.
 *
 * Use this where the consumer cannot follow relative links on demand (for example
 * a prompt injected into a tool-calling loop without file access). References are
 * ordered by their first link in SKILL.md, then any unlinked files alphabetically.
 */
export function loadSkillWithReferences(skillsPath: string, skillName: string): string | null {
    const skillDir = path.join(skillsPath, skillName);
    const skillFile = path.join(skillDir, 'SKILL.md');
    if (!fs.existsSync(skillFile)) {
        return null;
    }

    const skillContent = fs.readFileSync(skillFile, 'utf-8');
    const available = listSkillReferenceFiles(skillDir);
    if (available.length === 0) {
        return skillContent;
    }

    const linked = Array.from(skillContent.matchAll(REFERENCE_LINK_PATTERN), (match) => match[1])
        .filter((name) => available.includes(name));
    const ordered = Array.from(new Set([...linked, ...available]));
    const sections = ordered.map((name) => {
        const content = fs.readFileSync(path.join(skillDir, 'references', name), 'utf-8');
        return `## Reference: references/${name}\n\n${content}`;
    });

    return [skillContent, ...sections].join('\n\n---\n\n');
}

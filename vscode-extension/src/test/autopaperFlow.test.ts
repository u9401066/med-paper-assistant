import { describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const extDir = path.resolve(__dirname, '..', '..');
const extensionSource = fs.readFileSync(path.join(extDir, 'src', 'extension.ts'), 'utf-8');

describe('autopaper execution flow', () => {
    it('registers autopaper in the tool filters', () => {
        expect(extensionSource).toContain('autopaper: t =>');
    });

    it('routes /autopaper through runWithTools', () => {
        const autopaperCaseStart = extensionSource.indexOf("case 'autopaper': {");
        const helpCaseStart = extensionSource.indexOf("case 'help':");

        expect(autopaperCaseStart).toBeGreaterThan(-1);
        expect(helpCaseStart).toBeGreaterThan(autopaperCaseStart);

        const autopaperCase = extensionSource.slice(autopaperCaseStart, helpCaseStart);
        expect(autopaperCase).toContain('await runWithTools(');
        expect(autopaperCase).toContain('TOOL_FILTERS.autopaper');
    });

    it('builds an execution prompt for autopaper instead of doc-only output', () => {
        expect(extensionSource).toContain('function buildAutopaperExecutionPrompt');
        expect(extensionSource).toContain('This is an execution request, not a documentation request.');
        expect(extensionSource).toContain('pipeline_action(action="validate_phase", phase=...)');
        expect(extensionSource).toContain('pipeline_action(action="heartbeat")');
    });
});

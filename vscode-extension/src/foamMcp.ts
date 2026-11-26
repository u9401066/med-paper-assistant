import * as fs from 'fs';
import * as path from 'path';

/**
 * Official Foam MCP server (`foam-cli mcp`), registered read-only.
 *
 * MedPaper stays the canonical writer of library/wiki notes; Foam answers
 * live graph questions (backlinks, orphans, unresolved links, saved queries).
 * Keep in sync with `node_integrations.foam` in `mcp-integration-lock.json`.
 */
export const FOAM_MCP_PACKAGE = {
    repository: 'https://github.com/foambubble/foam',
    package: 'foam-cli',
    version: '0.47.0',
    env: { FOAM_TELEMETRY: '0' },
} as const;

export function findExecutableOnPath(
    name: string,
    envPath: string | undefined,
    platform: string = process.platform,
    pathExt: string | undefined = process.env.PATHEXT,
): string | null {
    if (!envPath) {
        return null;
    }
    const extensions = platform === 'win32' ? (pathExt || '.COM;.EXE;.BAT;.CMD').split(';').filter(Boolean) : [''];
    for (const dir of envPath.split(path.delimiter)) {
        if (!dir) {
            continue;
        }
        for (const extension of extensions) {
            const candidate = path.join(dir, name + extension);
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        }
    }
    return null;
}

/** VS Code resolves `npx` (including `npx.cmd` on Windows) like any mcp.json entry. */
export function buildFoamMcpCommand(workspaceDir: string): [string, string[]] {
    return ['npx', ['-y', `${FOAM_MCP_PACKAGE.package}@${FOAM_MCP_PACKAGE.version}`, 'mcp', '--workspace', workspaceDir]];
}

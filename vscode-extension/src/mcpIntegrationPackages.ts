/**
 * Packaged copy of the external MCP runtime lock used by the VSIX.
 *
 * `tests/test_mcp_integration_lock.py` and the extension unit tests compare
 * these values with the repository-level `mcp-integration-lock.json`. Keep the
 * JSON file authoritative and update this snapshot in the same change.
 */
export interface PinnedMcpPackage {
    repository: string;
    commit: string;
    version: string;
    sdkMajor: 2;
    pythonVersion: string;
    packageSource: string;
    entrypoint: string;
}

function githubArchiveSource(
    repository: string,
    commit: string,
    packageSubdirectory?: string,
): string {
    const suffix = packageSubdirectory
        ? `#subdirectory=${packageSubdirectory}`
        : '';
    return `${repository}/archive/${commit}.tar.gz${suffix}`;
}

const assetAwareRepository = 'https://github.com/u9401066/asset-aware-mcp';
const pubmedRepository = 'https://github.com/u9401066/pubmed-search-mcp';
const cguRepository = 'https://github.com/u9401066/creativity-generation-unit';
const drawioRepository = 'https://github.com/u9401066/next-ai-draw-io';
const zoteroRepository = 'https://github.com/u9401066/zotero-keeper';

export const MCP_INTEGRATION_PACKAGES = {
    'asset-aware': {
        repository: assetAwareRepository,
        commit: 'fa0e3489f83ea5922f06cb6b26bf0726872690c1',
        version: '1.4.1',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            assetAwareRepository,
            'fa0e3489f83ea5922f06cb6b26bf0726872690c1',
        ),
        entrypoint: 'asset-aware-mcp',
    },
    'pubmed-search': {
        repository: pubmedRepository,
        commit: 'd8ddc6a0fa9e87a5c9bbc25fa5a496223192eec3',
        version: '0.8.0',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            pubmedRepository,
            'd8ddc6a0fa9e87a5c9bbc25fa5a496223192eec3',
        ),
        entrypoint: 'pubmed-search-mcp',
    },
    cgu: {
        repository: cguRepository,
        commit: 'bb32a8f42123223a1cc54a41f7baed93b0c90d50',
        version: '0.9.0',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            cguRepository,
            'bb32a8f42123223a1cc54a41f7baed93b0c90d50',
        ),
        entrypoint: 'cgu-server',
    },
    drawio: {
        repository: drawioRepository,
        commit: '9bde25bac9ec160b912ddfebcb5ac037ce565e2f',
        version: '2.0.0',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            drawioRepository,
            '9bde25bac9ec160b912ddfebcb5ac037ce565e2f',
            'mcp-server',
        ),
        entrypoint: 'drawio-mcp-server',
    },
    'zotero-keeper': {
        repository: zoteroRepository,
        commit: '68a9a1a914cbf3ca8737b8f467cb505e6e445092',
        version: '2.4.0',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            zoteroRepository,
            '68a9a1a914cbf3ca8737b8f467cb505e6e445092',
            'mcp-server',
        ),
        entrypoint: 'zotero-keeper',
    },
} as const satisfies Record<string, PinnedMcpPackage>;

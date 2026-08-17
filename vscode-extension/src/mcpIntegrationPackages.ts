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
        commit: 'da8c7b99cbe512b1d51d7ab47698c9154f801ed4',
        version: '1.0.1',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            assetAwareRepository,
            'da8c7b99cbe512b1d51d7ab47698c9154f801ed4',
        ),
        entrypoint: 'asset-aware-mcp',
    },
    'pubmed-search': {
        repository: pubmedRepository,
        commit: 'b12a55022f29ffe4d71e65c7de9f8aadba46cf73',
        version: '0.6.3',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            pubmedRepository,
            'b12a55022f29ffe4d71e65c7de9f8aadba46cf73',
        ),
        entrypoint: 'pubmed-search-mcp',
    },
    cgu: {
        repository: cguRepository,
        commit: 'f293e190c2e8018729d9dcb78d6f5f39d209a87d',
        version: '0.6.0',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            cguRepository,
            'f293e190c2e8018729d9dcb78d6f5f39d209a87d',
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
        commit: '1faf5733dc7bbc05d0fac8ffe16c51f4585b5ce5',
        version: '2.1.0',
        sdkMajor: 2,
        pythonVersion: '3.12',
        packageSource: githubArchiveSource(
            zoteroRepository,
            '1faf5733dc7bbc05d0fac8ffe16c51f4585b5ce5',
            'mcp-server',
        ),
        entrypoint: 'zotero-keeper',
    },
} as const satisfies Record<string, PinnedMcpPackage>;

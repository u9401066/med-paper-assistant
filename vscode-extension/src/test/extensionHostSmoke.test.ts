import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as os from 'os';
import * as path from 'path';

type CommandHandler = (...args: unknown[]) => unknown;

class TestEventEmitter {
    public readonly event = vi.fn();

    public fire = vi.fn();

    public dispose = vi.fn();
}

class TestMcpStdioServerDefinition {
    public constructor(
        public readonly label: string,
        public readonly command: string,
        public readonly args: string[],
        public readonly env?: Record<string, string>,
    ) {}
}

const commandHandlers = new Map<string, CommandHandler>();
const executedCommands: Array<{ command: string; args: unknown[] }> = [];
const outputLines: string[] = [];
const outputShow = vi.fn();

let registeredProviderId: string | undefined;
let registeredProvider: {
    provideMcpServerDefinitions: (token: unknown) => unknown;
} | undefined;

const mockOutputChannel = {
    appendLine: vi.fn((line: string) => {
        outputLines.push(line);
    }),
    show: outputShow,
    dispose: vi.fn(),
};

const mockVscode = {
    window: {
        createOutputChannel: vi.fn(() => mockOutputChannel),
        showInformationMessage: vi.fn(async () => undefined),
        showWarningMessage: vi.fn(async () => undefined),
        showErrorMessage: vi.fn(async () => undefined),
        withProgress: vi.fn(async (_options: unknown, task: (progress: { report: (value: unknown) => void }) => Promise<unknown>) => task({ report: vi.fn() })),
    },
    workspace: {
        workspaceFolders: [{ uri: { fsPath: path.join(os.tmpdir(), 'medpaper-vsx-smoke-workspace') } }],
        getConfiguration: vi.fn(() => ({
            get: vi.fn(() => ''),
        })),
    },
    commands: {
        registerCommand: vi.fn((command: string, handler: CommandHandler) => {
            commandHandlers.set(command, handler);
            return { dispose: vi.fn() };
        }),
        executeCommand: vi.fn(async (command: string, ...args: unknown[]) => {
            executedCommands.push({ command, args });
            const handler = commandHandlers.get(command);
            if (handler) {
                return handler(...args);
            }
            return undefined;
        }),
    },
    lm: {
        tools: [],
        registerMcpServerDefinitionProvider: vi.fn((providerId: string, provider: unknown) => {
            registeredProviderId = providerId;
            registeredProvider = provider as { provideMcpServerDefinitions: (token: unknown) => unknown };
            return { dispose: vi.fn() };
        }),
        invokeTool: vi.fn(),
    },
    chat: {
        createChatParticipant: vi.fn(() => ({
            iconPath: undefined,
            followupProvider: undefined,
            dispose: vi.fn(),
        })),
    },
    extensions: {
        all: [],
    },
    env: {
        openExternal: vi.fn(async () => true),
    },
    Uri: {
        parse: vi.fn((value: string) => ({ value, fsPath: value })),
        joinPath: vi.fn((base: { fsPath?: string }, ...parts: string[]) => ({
            fsPath: path.join(base.fsPath || '', ...parts),
        })),
    },
    EventEmitter: TestEventEmitter,
    McpStdioServerDefinition: TestMcpStdioServerDefinition,
    ProgressLocation: {
        Notification: 15,
    },
};

vi.mock('vscode', () => mockVscode);

vi.mock('../uvManager', () => ({
    findUvPath: vi.fn(async () => 'uv'),
    installUvHeadless: vi.fn(async () => 'uv'),
    getUvxPath: vi.fn(() => 'uvx'),
    buildUvxCommand: vi.fn(() => ['uvx', []]),
    buildMcpCommand: vi.fn((_uvPath: string, packageName: string, binaryName?: string) => ['uvx', [binaryName || packageName], false]),
    buildMcpEnv: vi.fn(({ workspaceDir, pythonPath }: { workspaceDir?: string; pythonPath?: string }) => ({
        MEDPAPER_BASE_DIR: workspaceDir || '',
        PYTHONPATH: pythonPath || '',
    })),
    ensureInstalledTool: vi.fn(async () => undefined),
    findInstalledTool: vi.fn(() => null),
}));

vi.mock('../extensionHelpers', () => ({
    shouldSkipMcpRegistration: vi.fn(() => false),
    isDevWorkspace: vi.fn(() => true),
    determinePythonPath: vi.fn(() => 'uv'),
    countMissingBundledItems: vi.fn(() => ({ missingSkills: 0, missingAgents: 0, missingPrompts: 0, total: 0 })),
    buildDevPythonPath: vi.fn(() => path.join(os.tmpdir(), 'medpaper-dev-pythonpath')),
    detectExternallyProvidedMcpServers: vi.fn(() => ({ pubmed: false, zotero: false })),
}));

vi.mock('../utils', () => ({
    getPythonArgs: vi.fn((pythonPath: string, moduleName: string) => {
        if (pythonPath === 'uv') {
            return ['run', 'python', '-m', moduleName];
        }
        return ['-m', moduleName];
    }),
    loadSkillsAsInstructions: vi.fn(() => ''),
    loadSkillContent: vi.fn(() => null),
    BUNDLED_SKILLS: [],
    BUNDLED_PROMPTS: [],
    BUNDLED_TEMPLATES: [],
    BUNDLED_AGENTS: [],
}));

vi.mock('../drawioPanel', () => ({
    DrawioPanel: class {
        public static createOrShow(): void {}
    },
}));

function createExtensionContext() {
    const state = new Map<string, unknown>();
    const extensionPath = path.resolve(__dirname, '..', '..');

    return {
        subscriptions: [] as Array<{ dispose: () => void }>,
        extensionPath,
        extensionUri: { fsPath: extensionPath },
        extension: { id: 'u9401066.medpaper-assistant' },
        globalState: {
            get: <T>(key: string): T | undefined => state.get(key) as T | undefined,
            update: async (key: string, value: unknown) => {
                state.set(key, value);
            },
        },
    };
}

describe('extension host smoke', () => {
    beforeEach(() => {
        vi.resetModules();
        vi.clearAllMocks();
        commandHandlers.clear();
        executedCommands.length = 0;
        outputLines.length = 0;
        registeredProviderId = undefined;
        registeredProvider = undefined;
        mockVscode.workspace.workspaceFolders = [{ uri: { fsPath: path.join(os.tmpdir(), 'medpaper-vsx-smoke-workspace') } }];
    });

    afterEach(() => {
        commandHandlers.clear();
    });

    it('activates, registers MCP provider, and runs showStatus command', async () => {
        const extension = await import('../extension');
        const context = createExtensionContext();

        await extension.activate(context as never);

        expect(registeredProviderId).toBe('mdpaper');
        expect(registeredProvider).toBeDefined();
        expect(commandHandlers.has('mdpaper.showStatus')).toBe(true);

        const definitions = registeredProvider?.provideMcpServerDefinitions({}) as TestMcpStdioServerDefinition[];
        expect(Array.isArray(definitions)).toBe(true);
        expect(definitions.map(definition => definition.label)).toContain('MedPaper Assistant');

        const medpaperDefinition = definitions.find(definition => definition.label === 'MedPaper Assistant');
        expect(medpaperDefinition?.command).toBe('uv');
        expect(medpaperDefinition?.args).toEqual(['run', 'python', '-m', 'med_paper_assistant.interfaces.mcp']);

        await mockVscode.commands.executeCommand('mdpaper.showStatus');

        expect(outputShow).toHaveBeenCalledOnce();
        expect(outputLines.some(line => line.includes('MedPaper Assistant Status: Active'))).toBe(true);
    });
});
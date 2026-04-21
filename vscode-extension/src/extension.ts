import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getPythonArgs, loadSkillsAsInstructions, loadSkillContent, BUNDLED_SKILLS, BUNDLED_PROMPTS, BUNDLED_TEMPLATES, BUNDLED_AGENTS, BUNDLED_SUPPORT_FILES } from './utils';
import { findUvPath, installUvHeadless, getUvxPath, buildUvxCommand, buildMcpCommand, buildMcpEnv, ensureInstalledTool, findInstalledTool } from './uvManager';
import { shouldSkipMcpRegistration, isDevWorkspace as checkIsDevWorkspace, determinePythonPath, countMissingBundledItems, buildDevPythonPath, detectExternallyProvidedMcpServers } from './extensionHelpers';
import { DrawioPanel } from './drawioPanel';

let outputChannel: vscode.OutputChannel;
let resolvedUvPath: string | null = null;
const LLM_WIKI_GUIDE_RELATIVE_PATH = 'docs/how-to/llm-wiki.md';

function getBundledWorkspaceDocs(): string[] {
    return BUNDLED_SUPPORT_FILES
        .map(file => file.workspaceDestination)
        .filter(destination => destination.startsWith('docs/'));
}

async function openWorkspaceOrBundledDocument(
    context: vscode.ExtensionContext,
    relativePath: string,
): Promise<void> {
    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const candidates = [
        wsRoot ? path.join(wsRoot, relativePath) : null,
        path.join(context.extensionPath, relativePath),
    ].filter((candidate): candidate is string => Boolean(candidate));

    const targetPath = candidates.find(candidate => fs.existsSync(candidate));
    if (!targetPath) {
        vscode.window.showErrorMessage(`MedPaper: 找不到 ${relativePath}。請先執行 Setup Workspace 或重新安裝擴充功能。`);
        return;
    }

    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(targetPath));
    await vscode.window.showTextDocument(document, { preview: false });
}

function getExternallyProvidedManagedServers(context: vscode.ExtensionContext): { pubmed: boolean; zotero: boolean } {
    return detectExternallyProvidedMcpServers(vscode.extensions.all, context.extension.id);
}

export async function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('MedPaper Assistant');
    outputChannel.appendLine('MedPaper Assistant is activating...');

    // Step 1: Ensure uv is installed (needed for MCP server)
    await ensureUvReady(context);

    // Step 1.5: Marketplace mode auto-installs required persistent tool binaries.
    await ensureMarketplaceToolsReady(context);

    // Step 2: Register MCP Server Definition Provider
    const mcpProvider = registerMcpServerProvider(context);
    context.subscriptions.push(mcpProvider);

    // Register Chat Participant Handler (optional enhancement)
    const chatHandler = registerChatParticipant(context);
    if (chatHandler) {
        context.subscriptions.push(chatHandler);
    }

    // Register Commands
    context.subscriptions.push(
        vscode.commands.registerCommand('mdpaper.startServer', () => {
            vscode.window.showInformationMessage('MedPaper MCP Server is managed automatically by VS Code.');
        }),
        vscode.commands.registerCommand('mdpaper.stopServer', () => {
            vscode.window.showInformationMessage('MedPaper MCP Server will stop when VS Code closes.');
        }),
        vscode.commands.registerCommand('mdpaper.showStatus', () => {
            outputChannel.show();
            outputChannel.appendLine(`[${new Date().toISOString()}] MedPaper Assistant Status: Active`);
        }),
        vscode.commands.registerCommand('mdpaper.autoPaper', () => {
            // Check if journal-profile template exists in workspace
            const wsFolder = vscode.workspace.workspaceFolders?.[0];
            if (wsFolder) {
                const templatePath = path.join(wsFolder.uri.fsPath, 'templates', 'journal-profile.template.yaml');
                if (!fs.existsSync(templatePath)) {
                    const bundledTemplate = path.join(context.extensionPath, 'templates', 'journal-profile.template.yaml');
                    if (fs.existsSync(bundledTemplate)) {
                        vscode.window.showWarningMessage(
                            'MedPaper: journal-profile.template.yaml 尚未存在於 workspace。Auto Paper Phase 0 需要此模板。要複製嗎？',
                            '複製模板', '稍後再說'
                        ).then(selection => {
                            if (selection === '複製模板') {
                                fs.mkdirSync(path.dirname(templatePath), { recursive: true });
                                fs.copyFileSync(bundledTemplate, templatePath);
                                vscode.window.showInformationMessage('MedPaper: journal-profile.template.yaml 已複製到 templates/');
                            }
                        });
                    }
                }
            }
            // Open Copilot chat with autopaper command
            vscode.commands.executeCommand('workbench.action.chat.open', {
                query: '@mdpaper /autopaper 全自動寫論文'
            });
        }),
        vscode.commands.registerCommand('mdpaper.setupWorkspace', () => {
            setupWorkspace(context);
        }),
        vscode.commands.registerCommand('mdpaper.openLlmWikiGuide', async () => {
            await openWorkspaceOrBundledDocument(context, LLM_WIKI_GUIDE_RELATIVE_PATH);
        })
    );

    // Auto-scaffold: check if workspace is missing skills/agents/prompts
    // Only prompt once per workspace (use globalState to track)
    autoScaffoldIfNeeded(context);

    outputChannel.appendLine('MedPaper Assistant activated successfully!');
}

/**
 * Ensure uv is installed. If not, offer to auto-install.
 * Stores the resolved uv path in module-level variable and globalState.
 */
async function ensureUvReady(context: vscode.ExtensionContext): Promise<void> {
    const log = (msg: string) => outputChannel.appendLine(`[uv] ${msg}`);

    log('Checking uv installation...');
    resolvedUvPath = await findUvPath(log);

    if (resolvedUvPath) {
        log(`uv is ready: ${resolvedUvPath}`);
        context.globalState.update('uvPath', resolvedUvPath);
        return;
    }

    // uv not found — offer auto-install
    log('uv not found, prompting user...');
    const choice = await vscode.window.showInformationMessage(
        'MedPaper Assistant 需要 "uv" (Python 套件管理器) 才能運行。要自動安裝嗎？\n安裝後會自動處理 Python 和所有相依套件。',
        '自動安裝 uv',
        '手動安裝',
        '取消'
    );

    if (choice === '自動安裝 uv') {
        resolvedUvPath = await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'MedPaper: 正在安裝 uv...',
                cancellable: false
            },
            async (progress) => {
                progress.report({ message: '下載並安裝 uv (Python 套件管理器)...' });
                const installed = await installUvHeadless(log);

                if (installed) {
                    progress.report({ message: '安裝完成！' });
                    context.globalState.update('uvPath', installed);

                    const reload = await vscode.window.showInformationMessage(
                        '✅ uv 安裝成功！請重新載入 VS Code 以完成設定。',
                        '重新載入'
                    );
                    if (reload === '重新載入') {
                        vscode.commands.executeCommand('workbench.action.reloadWindow');
                    }
                } else {
                    vscode.window.showErrorMessage(
                        'uv 安裝失敗。請手動安裝: https://docs.astral.sh/uv/',
                        '開啟安裝頁面'
                    ).then(c => {
                        if (c === '開啟安裝頁面') {
                            vscode.env.openExternal(vscode.Uri.parse('https://docs.astral.sh/uv/getting-started/installation/'));
                        }
                    });
                }
                return installed;
            }
        );
    } else if (choice === '手動安裝') {
        vscode.env.openExternal(vscode.Uri.parse('https://docs.astral.sh/uv/getting-started/installation/'));
    }
    // choice === '取消' → resolvedUvPath stays null
}

async function ensureMarketplaceToolsReady(context: vscode.ExtensionContext): Promise<void> {
    if (!resolvedUvPath) {
        outputChannel.appendLine('[Install] Skipping tool auto-install because uv is not ready.');
        return;
    }

    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const isDevWorkspace = wsRoot ? checkIsDevWorkspace(wsRoot) : false;
    if (isDevWorkspace) {
        outputChannel.appendLine('[Install] Development workspace detected - skipping marketplace tool auto-install.');
        return;
    }

    if (wsRoot) {
        const mcpJsonPath = path.join(wsRoot, '.vscode', 'mcp.json');
        if (fs.existsSync(mcpJsonPath)) {
            try {
                const content = fs.readFileSync(mcpJsonPath, 'utf-8');
                if (shouldSkipMcpRegistration(content)) {
                    outputChannel.appendLine('[Install] User-managed mcp.json detected - skipping marketplace tool auto-install.');
                    return;
                }
            } catch {
                outputChannel.appendLine('[Install] Could not inspect .vscode/mcp.json - continuing with marketplace tool checks.');
            }
        }
    }

    const bundledToolPath = path.join(context.extensionPath, 'bundled', 'tool');
    const hasCguBundled = fs.existsSync(path.join(bundledToolPath, 'cgu'));
    const cguInWorkspace = wsRoot
        ? fs.existsSync(path.join(wsRoot, 'integrations', 'cgu', 'src', 'cgu'))
        : false;
    const externalServers = getExternallyProvidedManagedServers(context);

    const toolSpecs: Array<{ packageName: string; binaryName?: string }> = [
        { packageName: 'med-paper-assistant' },
    ];

    if (!externalServers.pubmed) {
        toolSpecs.push({ packageName: 'pubmed-search-mcp' });
    } else {
        outputChannel.appendLine('[Install] PubMed Search is already provided by another installed VS Code extension - skipping persistent tool install.');
    }

    if (!externalServers.zotero) {
        toolSpecs.push({ packageName: 'zotero-keeper' });
    } else {
        outputChannel.appendLine('[Install] Zotero Keeper is already provided by another installed VS Code extension - skipping persistent tool install.');
    }

    if (hasCguBundled || cguInWorkspace) {
        toolSpecs.push({ packageName: 'creativity-generation-unit', binaryName: 'cgu-server' });
    }

    const log = (msg: string) => outputChannel.appendLine(`[Install] ${msg}`);

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'MedPaper: 正在檢查並安裝 MCP 相依套件...',
            cancellable: false,
        },
        async (progress) => {
            const total = toolSpecs.length;
            for (let i = 0; i < total; i++) {
                const spec = toolSpecs[i];
                progress.report({
                    message: `檢查 ${spec.binaryName || spec.packageName} (${i + 1}/${total})`,
                    increment: 100 / total,
                });
                await ensureInstalledTool(spec.packageName, spec.binaryName, undefined, log);
            }
        }
    );
}

function registerMcpServerProvider(context: vscode.ExtensionContext): vscode.Disposable {
    // Check if user has their own mcp.json WITH mdpaper already defined
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        const mcpJsonPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'mcp.json');
        if (fs.existsSync(mcpJsonPath)) {
            try {
                const content = fs.readFileSync(mcpJsonPath, 'utf-8');
                if (shouldSkipMcpRegistration(content)) {
                    outputChannel.appendLine('[MCP] Found mdpaper in .vscode/mcp.json - skipping auto-registration');
                    return { dispose: () => {} };
                }
                outputChannel.appendLine('[MCP] Found .vscode/mcp.json but no mdpaper defined - proceeding with auto-registration');
            } catch {
                outputChannel.appendLine('[MCP] Could not read .vscode/mcp.json - proceeding with auto-registration');
            }
        }
    }

    // Skills are loaded from the extension's bundled directory
    // and used by the chat participant for /autopaper command

    const provider: vscode.McpServerDefinitionProvider = {
        onDidChangeMcpServerDefinitions: new vscode.EventEmitter<void>().event,

        provideMcpServerDefinitions(token: vscode.CancellationToken): vscode.ProviderResult<vscode.McpServerDefinition[]> {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            const wsRoot = workspaceFolders?.[0]?.uri.fsPath;
            const externalServers = getExternallyProvidedManagedServers(context);
            const toolSurface = getToolSurface();

            // Detect development workspace (has src/med_paper_assistant/ source code)
            const isDevWorkspace = wsRoot ? checkIsDevWorkspace(wsRoot) : false;

            // Use stored uv path, or fallback
            const uvPath = resolvedUvPath || (context.globalState.get<string>('uvPath')) || 'uv';
            const uvxPath = getUvxPath(uvPath);

            outputChannel.appendLine(`[MCP] Mode: ${isDevWorkspace ? 'development' : 'marketplace'}, uv: ${uvPath}, uvx: ${uvxPath}`);
            outputChannel.appendLine(`[MCP] MedPaper tool surface: ${toolSurface}`);

            const definitions: vscode.McpServerDefinition[] = [];

            // --- 1. MedPaper Assistant ---
            let mdpaperCommand: string;
            let mdpaperArgs: string[];
            let mcpEnv: Record<string, string>;

            const bundledToolPath = path.join(context.extensionPath, 'bundled', 'tool');

            if (isDevWorkspace && wsRoot) {
                // Development: use workspace source via uv run
                const pythonPath = getPythonPath(context);
                mdpaperCommand = pythonPath;
                mdpaperArgs = getPythonArgs(pythonPath, 'med_paper_assistant.interfaces.mcp');

                // Dev PYTHONPATH: workspace src + integrations + bundled
                const pythonPathEnv = buildDevPythonPath(wsRoot, bundledToolPath);

                mcpEnv = buildMcpEnv({ workspaceDir: wsRoot, pythonPath: pythonPathEnv, toolSurface });
            } else {
                // Marketplace: prefer pre-installed tool, fallback to uvx
                const [cmd, args, preInstalled] = buildMcpCommand(uvPath, 'med-paper-assistant');
                mdpaperCommand = cmd;
                mdpaperArgs = args;
                mcpEnv = buildMcpEnv({ workspaceDir: wsRoot, toolSurface });
                if (preInstalled) {
                    outputChannel.appendLine(`[MCP] MedPaper: using pre-installed binary (skipping uvx)`);
                }
            }

            outputChannel.appendLine(`[MCP] MedPaper: ${mdpaperCommand} ${mdpaperArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'MedPaper Assistant',
                mdpaperCommand,
                mdpaperArgs,
                mcpEnv
            ));

            // --- 2. CGU ---
            const hasCguBundled = fs.existsSync(path.join(bundledToolPath, 'cgu'));
            const cguInWorkspace = wsRoot
                ? fs.existsSync(path.join(wsRoot, 'integrations', 'cgu', 'src', 'cgu'))
                : false;

            if (hasCguBundled || cguInWorkspace) {
                let cguCommand: string;
                let cguArgs: string[];

                if (isDevWorkspace || cguInWorkspace) {
                    const pythonPath = getPythonPath(context);
                    cguCommand = pythonPath;
                    cguArgs = getPythonArgs(pythonPath, 'cgu.server');
                } else {
                    // Marketplace: prefer pre-installed, fallback to uvx
                    const [cmd, args, preInstalled] = buildMcpCommand(uvPath, 'creativity-generation-unit', 'cgu-server');
                    cguCommand = cmd;
                    cguArgs = args;
                    if (preInstalled) {
                        outputChannel.appendLine(`[MCP] CGU: using pre-installed binary (skipping uvx)`);
                    }
                }

                outputChannel.appendLine(`[MCP] CGU: ${cguCommand} ${cguArgs.join(' ')}`);
                definitions.push(new vscode.McpStdioServerDefinition(
                    'CGU Creativity',
                    cguCommand,
                    cguArgs,
                    mcpEnv
                ));
            } else {
                outputChannel.appendLine('[MCP] CGU not found — skipping registration');
            }

            // --- 3. PubMed Search ---
            if (externalServers.pubmed) {
                outputChannel.appendLine('[MCP] PubMed Search is already provided by another installed VS Code extension - skipping duplicate registration.');
            } else {
                const pubmedInWorkspace = wsRoot
                    ? fs.existsSync(path.join(wsRoot, 'integrations', 'pubmed-search-mcp', 'src', 'pubmed_search'))
                    : false;

                let pubmedCommand: string;
                let pubmedArgs: string[];

                if (pubmedInWorkspace) {
                    pubmedCommand = uvPath;
                    pubmedArgs = [
                        'run',
                        '--directory', path.join(wsRoot!, 'integrations', 'pubmed-search-mcp'),
                        'pubmed-search-mcp'
                    ];
                    outputChannel.appendLine('[MCP] PubMed Search: using workspace integration');
                } else {
                    const [cmd, args, preInstalled] = buildMcpCommand(uvPath, 'pubmed-search-mcp');
                    pubmedCommand = cmd;
                    pubmedArgs = args;
                    if (preInstalled) {
                        outputChannel.appendLine('[MCP] PubMed Search: using pre-installed binary (skipping uvx)');
                    }
                }

                outputChannel.appendLine(`[MCP] PubMed Search: ${pubmedCommand} ${pubmedArgs.join(' ')}`);
                definitions.push(new vscode.McpStdioServerDefinition(
                    'PubMed Search',
                    pubmedCommand,
                    pubmedArgs,
                    {
                        ...mcpEnv,
                        ENTREZ_EMAIL: process.env.ENTREZ_EMAIL || 'medpaper@example.com'
                    }
                ));
            }

            // --- 4. Zotero Keeper ---
            if (externalServers.zotero) {
                outputChannel.appendLine('[MCP] Zotero Keeper is already provided by another installed VS Code extension - skipping duplicate registration.');
            } else {
                const [zoteroCommand, zoteroArgs, zoteroPreInstalled] = buildMcpCommand(uvPath, 'zotero-keeper');
                if (zoteroPreInstalled) {
                    outputChannel.appendLine('[MCP] Zotero Keeper: using pre-installed binary (skipping uvx)');
                }
                outputChannel.appendLine(`[MCP] Zotero Keeper: ${zoteroCommand} ${zoteroArgs.join(' ')}`);
                definitions.push(new vscode.McpStdioServerDefinition(
                    'Zotero Keeper',
                    zoteroCommand,
                    zoteroArgs,
                    mcpEnv
                ));
            }

            // --- 5. Draw.io ---
            const drawioForkDir = wsRoot
                ? path.join(wsRoot, 'integrations', 'next-ai-draw-io', 'mcp-server')
                : null;
            const drawioForkEntry = drawioForkDir
                ? path.join(drawioForkDir, 'src', 'drawio_mcp_server')
                : null;
            const drawioWorkspaceDir = wsRoot
                ? path.join(wsRoot, 'integrations', 'drawio-mcp')
                : null;
            const drawioWorkspaceEntry = drawioWorkspaceDir
                ? path.join(drawioWorkspaceDir, 'src', 'index.js')
                : null;
            const drawioNode = findInstalledTool('node') || 'node';
            const drawioBinary = findInstalledTool('drawio-mcp');
            const drawioNpx = findInstalledTool('npx') || 'npx';
            let drawioCommand: string;
            let drawioArgs: string[];

            if (drawioForkEntry && fs.existsSync(drawioForkEntry)) {
                drawioCommand = uvPath;
                drawioArgs = [
                    'run',
                    '--directory', drawioForkDir!,
                    'python',
                    '-m',
                    'drawio_mcp_server',
                ];
                outputChannel.appendLine('[MCP] Draw.io: using forked workspace integration from integrations/next-ai-draw-io/mcp-server');
            } else if (drawioWorkspaceEntry && fs.existsSync(drawioWorkspaceEntry)) {
                drawioCommand = drawioNode;
                drawioArgs = [drawioWorkspaceEntry];
                outputChannel.appendLine('[MCP] Draw.io: using official workspace integration from integrations/drawio-mcp');
            } else if (drawioBinary) {
                drawioCommand = drawioBinary;
                drawioArgs = [];
                outputChannel.appendLine('[MCP] Draw.io: using pre-installed drawio-mcp binary');
            } else {
                drawioCommand = drawioNpx;
                drawioArgs = ['-y', '@drawio/mcp'];
                outputChannel.appendLine('[MCP] Draw.io: using npx fallback for official @drawio/mcp package');
            }

            outputChannel.appendLine(`[MCP] Draw.io: ${drawioCommand} ${drawioArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'Draw.io Diagrams',
                drawioCommand,
                drawioArgs,
                mcpEnv
            ));

            return definitions;
        },

        resolveMcpServerDefinition(
            definition: vscode.McpServerDefinition,
            token: vscode.CancellationToken
        ): vscode.ProviderResult<vscode.McpServerDefinition> {
            outputChannel.appendLine(`Resolving MCP server: ${definition.label}`);
            return definition;
        }
    };

    // Use VS Code API to register the provider
    return vscode.lm.registerMcpServerDefinitionProvider('mdpaper', provider);
}



/**
 * Run a tool-calling loop: sends the user prompt + available MCP tools to the
 * language model and iterates up to `maxRounds` when the model requests tool
 * invocations.  Text parts are streamed straight to the chat UI.
 */
async function runWithTools(
    request: vscode.ChatRequest,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
    toolFilter?: (tool: vscode.LanguageModelToolInformation) => boolean,
    options?: {
        maxRounds?: number;
        promptOverride?: string;
    },
): Promise<void> {
    const maxRounds = options?.maxRounds ?? 5;

    // Gather available MCP tools, applying an optional filter
    const allTools = vscode.lm.tools;
    const filtered = toolFilter ? allTools.filter(toolFilter) : Array.from(allTools);

    // Convert LanguageModelToolInformation → LanguageModelChatTool (plain objects)
    const chatTools: vscode.LanguageModelChatTool[] = filtered.map(t => ({
        name: t.name,
        description: t.description,
        inputSchema: t.inputSchema,
    }));

    const messages: vscode.LanguageModelChatMessage[] = [
        vscode.LanguageModelChatMessage.User(options?.promptOverride ?? request.prompt),
    ];

    for (let round = 0; round < maxRounds; round++) {
        const response = await request.model.sendRequest(
            messages,
            { tools: chatTools },
            token,
        );

        // Collect parts from the stream – text goes to UI, tool calls are batched
        const toolCalls: vscode.LanguageModelToolCallPart[] = [];
        const assistantParts: (vscode.LanguageModelTextPart | vscode.LanguageModelToolCallPart)[] = [];

        for await (const chunk of response.stream) {
            if (chunk instanceof vscode.LanguageModelTextPart) {
                stream.markdown(chunk.value);
                assistantParts.push(chunk);
            } else if (chunk instanceof vscode.LanguageModelToolCallPart) {
                toolCalls.push(chunk);
                assistantParts.push(chunk);
            }
        }

        // If the model didn't request any tool calls we're done
        if (toolCalls.length === 0) {
            return;
        }

        // Record assistant turn then invoke each requested tool
        messages.push(vscode.LanguageModelChatMessage.Assistant(assistantParts));

        const toolResults: (vscode.LanguageModelToolResultPart | vscode.LanguageModelTextPart)[] = [];
        for (const call of toolCalls) {
            try {
                const result = await vscode.lm.invokeTool(call.name, {
                    input: call.input,
                    toolInvocationToken: request.toolInvocationToken,
                }, token);

                // Extract text from tool result
                const texts = result.content
                    .filter((p): p is vscode.LanguageModelTextPart => p instanceof vscode.LanguageModelTextPart)
                    .map(p => p.value);
                toolResults.push(new vscode.LanguageModelToolResultPart(call.callId, [new vscode.LanguageModelTextPart(texts.join('\n'))]));
            } catch (err) {
                toolResults.push(new vscode.LanguageModelToolResultPart(
                    call.callId,
                    [new vscode.LanguageModelTextPart(`Tool error: ${err instanceof Error ? err.message : String(err)}`)],
                ));
            }
        }

        messages.push(vscode.LanguageModelChatMessage.User(toolResults));
    }
}

function buildAutopaperExecutionPrompt(userPrompt: string, autoPaperSkill: string | null): string {
    const preamble = [
        'You are executing the MedPaper Auto Paper pipeline through MCP tools.',
        'This is an execution request, not a documentation request.',
        'Operate phase-by-phase and use code-enforced gates instead of skipping ahead.',
        '',
        'Mandatory execution rules:',
        '1. Start by understanding current project state and pipeline status.',
        '2. Before advancing from a phase, call pipeline_action(action="validate_phase", phase=...).',
        '3. If a phase gate fails, inspect the reported missing artifacts and fix them before retrying.',
        '4. During writing, use pipeline_action(action="approve_section", section=..., decision="approve") after each section is completed and audited.',
        '5. During review, use pipeline_action(action="start_review") and pipeline_action(action="submit_review", scores=...) correctly; if verdict is rewrite_needed, call pipeline_action(action="rewrite_section", ...).',
        '6. Before claiming completion, call pipeline_action(action="heartbeat") and only report done if the pipeline is actually complete.',
        '7. Prefer project_action/workspace_state_action/run_quality_checks/export_document/inspect_export over legacy compatibility verbs.',
        '8. Prefer MCP tools over describing what should happen.',
        '',
        'User request:',
        userPrompt,
    ].join('\n');

    if (!autoPaperSkill) {
        return preamble;
    }

    return [
        preamble,
        '',
        'Reference workflow instructions:',
        autoPaperSkill,
    ].join('\n');
}

/** Tool name filter helpers */
const TOOL_FILTERS: Record<string, (t: vscode.LanguageModelToolInformation) => boolean> = {
    search: t => /search|literature|pubmed|reference|citation/i.test(t.name + ' ' + t.description),
    draft: t => /draft|write|section|citation|wikilink|word|count/i.test(t.name + ' ' + t.description),
    concept: t => /concept|novelty|valid|idea/i.test(t.name + ' ' + t.description),
    project: t => /project|exploration|workspace/i.test(t.name + ' ' + t.description),
    format: t => /template|document|export|docx|section|insert/i.test(t.name + ' ' + t.description),
    analysis: t => /analy|statistic|plot|table|dataset|figure/i.test(t.name + ' ' + t.description),
    strategy: t => /search|strategy|query|mesh/i.test(t.name + ' ' + t.description),
    drawio: t => /diagram|drawio|draw|figure/i.test(t.name + ' ' + t.description),
    autopaper: t => /project|workspace|exploration|search|reference|citation|concept|novelty|draft|write|section|word|analysis|statistic|table|figure|diagram|review|pipeline|approve|rewrite|pause|resume|format|export|document|sync/i.test(t.name + ' ' + t.description),
};

function registerChatParticipant(context: vscode.ExtensionContext): vscode.Disposable | null {
    try {
        // Pre-load skill summaries for chat context
        const skillsPath = path.join(context.extensionPath, 'skills');

        const handler: vscode.ChatRequestHandler = async (
            request: vscode.ChatRequest,
            chatContext: vscode.ChatContext,
            stream: vscode.ChatResponseStream,
            token: vscode.CancellationToken
        ) => {
            // Commands that use the tool-calling loop
            const toolCommand = request.command;
            if (toolCommand && toolCommand in TOOL_FILTERS) {
                const icons: Record<string, string> = {
                    search: '🔍', draft: '✍️', concept: '💡',
                    project: '📁', format: '📄', analysis: '📊',
                    strategy: '🎯', drawio: '📐',
                };
                stream.markdown(`${icons[toolCommand] || '🔧'} **正在使用 MCP 工具處理您的請求…**\n\n`);
                await runWithTools(request, stream, token, TOOL_FILTERS[toolCommand]);
                return { metadata: { command: toolCommand } };
            }

            // Commands that stay static
            switch (request.command) {
                case 'autopaper': {
                    const autoPaperSkill = loadSkillContent(skillsPath, 'auto-paper');
                    stream.markdown('🚀 **正在啟動 Auto Paper pipeline...**\n\n');
                    await runWithTools(
                        request,
                        stream,
                        token,
                        TOOL_FILTERS.autopaper,
                        {
                            maxRounds: 12,
                            promptOverride: buildAutopaperExecutionPrompt(request.prompt, autoPaperSkill),
                        },
                    );
                    return { metadata: { command: request.command } };
                }

                case 'help':
                    stream.markdown('## 📚 MedPaper Assistant 完整指令列表\n\n');
                    stream.markdown('### 💬 Chat 指令 (@mdpaper)\n\n');
                    stream.markdown('| 指令 | 說明 |\n');
                    stream.markdown('|------|------|\n');
                    stream.markdown('| `/search` | 🔍 搜尋 PubMed 文獻（MCP 工具） |\n');
                    stream.markdown('| `/draft` | ✍️ 撰寫論文章節（MCP 工具） |\n');
                    stream.markdown('| `/concept` | 💡 發展研究概念（MCP 工具） |\n');
                    stream.markdown('| `/project` | 📁 管理研究專案（MCP 工具） |\n');
                    stream.markdown('| `/format` | 📄 匯出 Word 文件（MCP 工具） |\n');
                    stream.markdown('| `/analysis` | 📊 資料分析與統計（MCP 工具） |\n');
                    stream.markdown('| `/strategy` | 🎯 搜尋策略設定（MCP 工具） |\n');
                    stream.markdown('| `/drawio` | 📐 Draw.io 圖表繪製（MCP 工具） |\n');
                    stream.markdown('| `/autopaper` | 🚀 全自動寫論文 |\n');
                    stream.markdown('| `/help` | 顯示本說明 |\n\n');
                    stream.markdown('### 🗂️ Command Palette 快捷功能\n\n');
                    stream.markdown('- `MedPaper: Setup Workspace` → 複製 bundled skills、prompts、docs、agents、templates 到 workspace\n');
                    stream.markdown('- `MedPaper: Open LLM Wiki Guide` → 直接開啟 `docs/how-to/llm-wiki.md`\n\n');
                    stream.markdown('### 🔧 Agent Mode 自然語言\n\n');
                    stream.markdown('直接在 Agent Mode 輸入：\n');
                    stream.markdown('- 「全自動寫論文」「一鍵寫論文」→ Auto Paper Pipeline\n');
                    stream.markdown('- 「找論文」「搜尋 PubMed」→ 文獻搜尋\n');
                    stream.markdown('- 「寫 Introduction」→ 草稿撰寫\n');
                    stream.markdown('- 「驗證 novelty」→ 概念驗證\n');
                    stream.markdown('- 「畫流程圖」→ Draw.io 圖表\n');
                    break;

                default:
                    // General query — use full tool set
                    stream.markdown('🔧 **正在使用 MCP 工具處理您的請求…**\n\n');
                    await runWithTools(request, stream, token);
            }

            return { metadata: { command: request.command } };
        };

        const participant = vscode.chat.createChatParticipant('medpaper.assistant', handler);
        participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'media', 'icon.png');

        // Follow-up provider
        participant.followupProvider = {
            provideFollowups(result, context, token) {
                return [
                    { prompt: '全自動寫論文', label: '🚀 Auto Paper', command: 'autopaper' },
                    { prompt: '搜尋相關文獻', label: '🔍 Search Literature', command: 'search' },
                    { prompt: '開始撰寫草稿', label: '✍️ Start Drafting', command: 'draft' },
                    { prompt: '驗證研究概念', label: '💡 Validate Concept', command: 'concept' },
                    { prompt: '畫流程圖', label: '📐 Draw.io', command: 'drawio' }
                ];
            }
        };

        return participant;
    } catch (error) {
        outputChannel.appendLine(`Chat participant registration skipped: ${error}`);
        return null;
    }
}

function getPythonPath(context: vscode.ExtensionContext): string {
    const config = vscode.workspace.getConfiguration('mdpaper');
    const configuredPath = config.get<string>('pythonPath');
    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

    return determinePythonPath({
        configuredPath: configuredPath || undefined,
        wsRoot,
        extensionPath: context.extensionPath,
    });
}

function getToolSurface(): 'compact' | 'full' {
    const config = vscode.workspace.getConfiguration('mdpaper');
    return config.get<'compact' | 'full'>('toolSurface') || 'compact';
}



async function autoScaffoldIfNeeded(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        return;
    }

    const wsRoot = workspaceFolders[0].uri.fsPath;
    const extPath = context.extensionPath;

    const {
        missingSkills,
        missingAgents,
        missingPrompts,
        missingSupportFiles,
        total: totalMissing,
    } = countMissingBundledItems(
        wsRoot,
        extPath,
        BUNDLED_SKILLS,
        BUNDLED_AGENTS,
        BUNDLED_PROMPTS,
        BUNDLED_SUPPORT_FILES,
    );

    if (totalMissing === 0) {
        outputChannel.appendLine('[AutoScaffold] Workspace already has all bundled skills, prompts, agents, and support docs/files.');
        return;
    }

    // Use workspace-specific state key to avoid re-prompting
    const stateKey = `mdpaper.scaffolded.${wsRoot}`;
    const alreadyPrompted = context.globalState.get<boolean>(stateKey);

    if (alreadyPrompted) {
        outputChannel.appendLine(`[AutoScaffold] Already prompted for this workspace (${totalMissing} items missing). Run "MedPaper: Setup Workspace" to update.`);
        return;
    }

    const detail = [];
    if (missingSkills > 0) { detail.push(`${missingSkills} skills`); }
    if (missingAgents > 0) { detail.push(`${missingAgents} agents`); }
    if (missingPrompts > 0) { detail.push(`${missingPrompts} prompts`); }
    if (missingSupportFiles > 0) { detail.push(`${missingSupportFiles} support docs/files`); }

    const selection = await vscode.window.showInformationMessage(
        `MedPaper: 偵測到 workspace 缺少 ${detail.join('、')}。要設定嗎？`,
        '設定 Workspace',
        '稍後再說',
        '不再提醒'
    );

    if (selection === '設定 Workspace') {
        await setupWorkspace(context);
    } else if (selection === '不再提醒') {
        await context.globalState.update(stateKey, true);
    }
    // '稍後再說' → do nothing, will prompt again next activation
}

async function setupWorkspace(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('請先開啟一個 workspace 資料夾。');
        return;
    }

    const wsRoot = workspaceFolders[0].uri.fsPath;
    const extPath = context.extensionPath;
    let copied = 0;
    const copiedDocs: string[] = [];

    // 1. Copy skills → .claude/skills/
    for (const skill of BUNDLED_SKILLS) {
        const src = path.join(extPath, 'skills', skill, 'SKILL.md');
        const dst = path.join(wsRoot, '.claude', 'skills', skill, 'SKILL.md');
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            copied++;
        }
    }

    // 2. Copy prompts → .github/prompts/
    for (const prompt of BUNDLED_PROMPTS) {
        const src = path.join(extPath, 'prompts', `${prompt}.prompt.md`);
        const dst = path.join(wsRoot, '.github', 'prompts', `${prompt}.prompt.md`);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            copied++;
        }
    }

    // 3. Copy support files such as prompt indexes, instructions, and copilot mode.
    for (const file of BUNDLED_SUPPORT_FILES) {
        const src = path.join(extPath, file.destination);
        const dst = path.join(wsRoot, file.workspaceDestination);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            if (file.workspaceDestination.startsWith('docs/')) {
                copiedDocs.push(file.workspaceDestination);
            }
            copied++;
        }
    }

    // 4. Copy templates → templates/ (overwrite if outdated)
    for (const tmpl of BUNDLED_TEMPLATES) {
        const src = path.join(extPath, 'templates', tmpl);
        const dst = path.join(wsRoot, 'templates', tmpl);
        if (fs.existsSync(src)) {
            const needsCopy = !fs.existsSync(dst) ||
                fs.readFileSync(src, 'utf-8') !== fs.readFileSync(dst, 'utf-8');
            if (needsCopy) {
                fs.mkdirSync(path.dirname(dst), { recursive: true });
                fs.copyFileSync(src, dst);
                copied++;
            }
        } else {
            outputChannel.appendLine(`[Setup] ⚠️ Bundled template missing: ${tmpl}`);
        }
    }

    // 5. Copy agents → .github/agents/
    for (const agent of BUNDLED_AGENTS) {
        const src = path.join(extPath, 'agents', `${agent}.agent.md`);
        const dst = path.join(wsRoot, '.github', 'agents', `${agent}.agent.md`);
        if (fs.existsSync(src) && !fs.existsSync(dst)) {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            copied++;
        }
    }

    if (copied > 0) {
        if (copiedDocs.length > 0) {
            const docsSelection = await vscode.window.showInformationMessage(
                `MedPaper: 已新增 docs/ 內容：${copiedDocs.join('、')}。`,
                '開啟 LLM Wiki Guide'
            );
            if (docsSelection === '開啟 LLM Wiki Guide') {
                await openWorkspaceOrBundledDocument(context, LLM_WIKI_GUIDE_RELATIVE_PATH);
            }
        }

        const selection = await vscode.window.showInformationMessage(
            `MedPaper: 已設定 ${copied} 個檔案（skills、prompts、agents、support docs/files、templates）到 workspace。重新載入視窗以啟用全部功能。`,
            '重新載入'
        );
        if (selection === '重新載入') {
            vscode.commands.executeCommand('workbench.action.reloadWindow');
        }
    } else {
        const docs = getBundledWorkspaceDocs();
        const message = docs.length > 0
            ? `MedPaper: Workspace 已是最新，無需更新。可用「MedPaper: Open LLM Wiki Guide」直接開啟 ${LLM_WIKI_GUIDE_RELATIVE_PATH}。`
            : 'MedPaper: Workspace 已是最新，無需更新。';
        vscode.window.showInformationMessage(message);
    }

    outputChannel.appendLine(`[Setup] Copied ${copied} files to workspace`);
}

export function deactivate() {
    outputChannel?.appendLine('MedPaper Assistant deactivated.');
}

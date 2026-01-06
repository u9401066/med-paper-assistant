import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

let outputChannel: vscode.OutputChannel;

export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('MedPaper Assistant');
    outputChannel.appendLine('MedPaper Assistant is activating...');

    // Register MCP Server Definition Provider
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
        })
    );

    outputChannel.appendLine('MedPaper Assistant activated successfully!');
}

function registerMcpServerProvider(context: vscode.ExtensionContext): vscode.Disposable {
    // Check if user has their own mcp.json - if so, skip auto-registration
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        const mcpJsonPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'mcp.json');
        if (fs.existsSync(mcpJsonPath)) {
            outputChannel.appendLine('[MCP] Found .vscode/mcp.json - skipping auto-registration (use local config instead)');
            // Return a no-op disposable
            return { dispose: () => {} };
        }
    }

    // Load skills for server instructions
    const skillsPath = path.join(context.extensionPath, 'skills');
    const instructions = loadSkillsAsInstructions(skillsPath);

    const provider: vscode.McpServerDefinitionProvider = {
        onDidChangeMcpServerDefinitions: new vscode.EventEmitter<void>().event,
        
        provideMcpServerDefinitions(token: vscode.CancellationToken): vscode.ProviderResult<vscode.McpServerDefinition[]> {
            const pythonPath = getPythonPath(context);
            const workspaceFolders = vscode.workspace.workspaceFolders;
            
            outputChannel.appendLine(`[MCP] Using Python Path: ${pythonPath}`);
            
            // Determine PYTHONPATH
            // Include bundled tools and workspace src (for development)
            let pythonPathEnv = path.join(context.extensionPath, 'bundled', 'tool');
            if (workspaceFolders) {
                const srcPath = path.join(workspaceFolders[0].uri.fsPath, 'src');
                const integrationsPath = path.join(workspaceFolders[0].uri.fsPath, 'integrations');
                
                if (fs.existsSync(srcPath)) {
                    pythonPathEnv = `${srcPath}${path.delimiter}${pythonPathEnv}`;
                }
                
                // Add integration src paths for development
                const cguSrc = path.join(integrationsPath, 'cgu', 'src');
                if (fs.existsSync(cguSrc)) {
                    pythonPathEnv = `${cguSrc}${path.delimiter}${pythonPathEnv}`;
                }
            }

            const definitions: vscode.McpServerDefinition[] = [];

            // 1. MedPaper Assistant
            const mdpaperArgs = getPythonArgs(pythonPath, 'med_paper_assistant.interfaces.mcp');
            outputChannel.appendLine(`[MCP] MedPaper Args: ${mdpaperArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'MedPaper Assistant',
                pythonPath,
                mdpaperArgs,
                {
                    PYTHONPATH: pythonPathEnv,
                    MDPAPER_INSTRUCTIONS: instructions,
                    MDPAPER_EXTENSION_PATH: context.extensionPath
                }
            ));

            // 2. CGU (if bundled or in workspace)
            const cguArgs = getPythonArgs(pythonPath, 'cgu.server');
            outputChannel.appendLine(`[MCP] CGU Args: ${cguArgs.join(' ')}`);
            definitions.push(new vscode.McpStdioServerDefinition(
                'CGU Creativity',
                pythonPath,
                cguArgs,
                {
                    PYTHONPATH: pythonPathEnv
                }
            ));

            // 3. Draw.io (External uvx)
            definitions.push(new vscode.McpStdioServerDefinition(
                'Draw.io Diagrams',
                'uvx',
                ['--from', 'drawio-mcp', 'drawio-mcp-server'],
                {
                    DRAWIO_NEXTJS_URL: 'http://localhost:3000'
                }
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

function getPythonArgs(command: string, module: string): string[] {
    const baseCommand = path.basename(command).toLowerCase();
    const commandName = baseCommand.replace(/\.exe$/, '');

    // Case 1: uv run python -m ...
    if (commandName === 'uv') {
        return ['run', 'python', '-m', module];
    } 
    
    // Case 2: uvx package (NO -m)
    if (commandName === 'uvx') {
        const packageMap: Record<string, string> = {
            'med_paper_assistant.interfaces.mcp': 'med-paper-assistant',
            'pubmed_search.mcp': 'pubmed-search-mcp',
            'cgu.server': 'creativity-generation-unit'
        };
        const pkg = packageMap[module];
        if (pkg) {
            return [pkg];
        }
        // If not in map, just return the module name but NO -m
        return [module];
    }

    // Case 3: Standard python -m ...
    // Be very specific: only add -m if it's actually a python executable
    if (commandName === 'python' || commandName === 'python3' || commandName === 'py' || commandName === 'python.exe') {
        return ['-m', module];
    }

    // Default: If it's a path to something else, don't assume -m
    // But if it's a venv python, it might be named 'python'
    if (command.includes('.venv') || command.includes('venv')) {
        return ['-m', module];
    }

    return [module];
}

function registerChatParticipant(context: vscode.ExtensionContext): vscode.Disposable | null {
    try {
        const handler: vscode.ChatRequestHandler = async (
            request: vscode.ChatRequest,
            chatContext: vscode.ChatContext,
            stream: vscode.ChatResponseStream,
            token: vscode.CancellationToken
        ) => {
            // Handle different commands
            switch (request.command) {
                case 'search':
                    stream.markdown('🔍 使用 MCP 工具搜尋 PubMed...\n\n');
                    stream.markdown('請在 Agent Mode 中使用此功能，MCP 工具會自動被調用。');
                    break;
                
                case 'draft':
                    stream.markdown('✍️ 準備撰寫論文章節...\n\n');
                    stream.markdown('請提供章節類型和主題，我會協助您撰寫。');
                    break;
                
                case 'concept':
                    stream.markdown('💡 發展研究概念...\n\n');
                    stream.markdown('請描述您的研究想法，我會幫您驗證 novelty。');
                    break;
                
                case 'project':
                    stream.markdown('📁 專案管理...\n\n');
                    stream.markdown('使用 `/mdpaper.project` 來建立或管理研究專案。');
                    break;
                
                case 'format':
                    stream.markdown('📄 匯出 Word 文件...\n\n');
                    stream.markdown('請確保已完成所有章節的撰寫。');
                    break;
                
                default:
                    // General query - provide guidance
                    stream.markdown(`## MedPaper Assistant\n\n`);
                    stream.markdown(`您好！我是 MedPaper Assistant，專門協助醫學論文撰寫。\n\n`);
                    stream.markdown(`### 可用指令\n`);
                    stream.markdown(`- \`/search\` - 搜尋 PubMed 文獻\n`);
                    stream.markdown(`- \`/draft\` - 撰寫論文章節\n`);
                    stream.markdown(`- \`/concept\` - 發展研究概念\n`);
                    stream.markdown(`- \`/project\` - 管理研究專案\n`);
                    stream.markdown(`- \`/format\` - 匯出 Word 文件\n\n`);
                    stream.markdown(`💡 **建議**：在 Agent Mode 中使用以獲得完整的 MCP 工具支援。`);
            }

            return { metadata: { command: request.command } };
        };

        const participant = vscode.chat.createChatParticipant('medpaper.assistant', handler);
        participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'media', 'icon.png');
        
        // Follow-up provider
        participant.followupProvider = {
            provideFollowups(result, context, token) {
                return [
                    { prompt: '搜尋相關文獻', label: '🔍 Search Literature' },
                    { prompt: '開始撰寫草稿', label: '✍️ Start Drafting' },
                    { prompt: '驗證研究概念', label: '💡 Validate Concept' }
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
    // 1. Check user configuration
    const config = vscode.workspace.getConfiguration('mdpaper');
    const configuredPath = config.get<string>('pythonPath');
    if (configuredPath) {
        // If it's just "uv" or "uvx", return it as is
        if (configuredPath === 'uv' || configuredPath === 'uvx') {
            return configuredPath;
        }
        if (fs.existsSync(configuredPath)) {
            return configuredPath;
        }
    }

    // 2. Prefer 'uv' if workspace has pyproject.toml (uv-managed project)
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        const pyprojectPath = path.join(workspaceFolders[0].uri.fsPath, 'pyproject.toml');
        if (fs.existsSync(pyprojectPath)) {
            // This is likely a uv-managed project, use 'uv' to ensure proper environment
            return 'uv';
        }
    }

    // 3. Check for virtual environment in workspace (fallback for non-uv projects)
    if (workspaceFolders) {
        for (const folder of workspaceFolders) {
            const venvPaths = [
                path.join(folder.uri.fsPath, '.venv', 'bin', 'python'),
                path.join(folder.uri.fsPath, '.venv', 'bin', 'python3'),
                path.join(folder.uri.fsPath, '.venv', 'Scripts', 'python.exe'),
                path.join(folder.uri.fsPath, 'venv', 'bin', 'python'),
                path.join(folder.uri.fsPath, 'venv', 'Scripts', 'python.exe'),
            ];
            for (const venvPath of venvPaths) {
                if (fs.existsSync(venvPath)) {
                    return venvPath;
                }
            }
        }
    }

    // 4. Check bundled Python (for standalone distribution)
    const bundledPython = path.join(context.extensionPath, 'bundled', 'python', 'bin', 'python3');
    if (fs.existsSync(bundledPython)) {
        return bundledPython;
    }

    // 5. Try system Python
    return 'python3';
}

function loadSkillsAsInstructions(skillsPath: string): string {
    const instructions: string[] = [];
    
    if (!fs.existsSync(skillsPath)) {
        return '';
    }

    const skillDirs = fs.readdirSync(skillsPath, { withFileTypes: true })
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name);

    for (const skillDir of skillDirs) {
        const skillFile = path.join(skillsPath, skillDir, 'SKILL.md');
        if (fs.existsSync(skillFile)) {
            const content = fs.readFileSync(skillFile, 'utf-8');
            instructions.push(`## Skill: ${skillDir}\n\n${content}`);
        }
    }

    return instructions.join('\n\n---\n\n');
}

export function deactivate() {
    outputChannel?.appendLine('MedPaper Assistant deactivated.');
}

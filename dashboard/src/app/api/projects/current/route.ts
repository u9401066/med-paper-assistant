import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

const CURRENT_PROJECT_FILE = path.join(process.cwd(), '..', '.current_project');
const PROJECTS_DIR = path.join(process.cwd(), '..', 'projects');

// 取得專案的核心文件路徑
function getProjectFiles(projectPath: string): string[] {
  return [
    path.join(projectPath, 'concept.md'),
    path.join(projectPath, 'drafts', 'draft.md'),
  ];
}

export async function POST(request: NextRequest) {
  try {
    const { slug, openFiles = true } = await request.json();
    
    if (!slug) {
      return NextResponse.json(
        { error: 'Project slug is required' },
        { status: 400 }
      );
    }

    // 驗證專案存在
    const projectPath = path.join(PROJECTS_DIR, slug);
    const projectJsonPath = path.join(projectPath, 'project.json');
    
    try {
      await fs.access(projectJsonPath);
    } catch {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }

    // 寫入當前專案
    await fs.writeFile(CURRENT_PROJECT_FILE, slug);

    // 讀取專案資訊
    const content = await fs.readFile(projectJsonPath, 'utf-8');
    const data = JSON.parse(content);

    // 收集要開啟的文件路徑
    const filesToOpen: string[] = [];
    if (openFiles) {
      const candidateFiles = getProjectFiles(projectPath);
      for (const filePath of candidateFiles) {
        try {
          await fs.access(filePath);
          filesToOpen.push(filePath);
        } catch {
          // 文件不存在，跳過
        }
      }
    }

    return NextResponse.json({
      success: true,
      project: {
        name: data.name,
        slug: data.slug || slug,
        description: data.description || '',
        paperType: data.paper_type || '',
        targetJournal: data.target_journal || '',
        status: data.status || 'concept',
        focus: data.focus,
        createdAt: data.created_at,
        updatedAt: data.updated_at,
        memo: data.memo,
      },
      filesToOpen,  // 返回要開啟的文件路徑
      projectPath,  // 返回專案路徑
    });
  } catch (error) {
    console.error('Error switching project:', error);
    return NextResponse.json(
      { error: 'Failed to switch project' },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

const CURRENT_PROJECT_FILE = path.join(process.cwd(), '..', '.current_project');
const PROJECTS_DIR = path.join(process.cwd(), '..', 'projects');

export async function POST(request: NextRequest) {
  try {
    const { slug } = await request.json();
    
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
    });
  } catch (error) {
    console.error('Error switching project:', error);
    return NextResponse.json(
      { error: 'Failed to switch project' },
      { status: 500 }
    );
  }
}

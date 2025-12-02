import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

// 專案根目錄 (相對於 dashboard)
const PROJECTS_DIR = path.join(process.cwd(), '..', 'projects');
const CURRENT_PROJECT_FILE = path.join(process.cwd(), '..', '.current_project');

interface ProjectData {
  name: string;
  slug: string;
  description?: string;
  paper_type?: string;
  target_journal?: string;
  status?: string;
  focus?: {
    type: string;
    section?: string;
    lastUpdated: string;
  };
  created_at?: string;
  updated_at?: string;
  memo?: string;
}

async function readProjectJson(projectPath: string): Promise<ProjectData | null> {
  try {
    const jsonPath = path.join(projectPath, 'project.json');
    const content = await fs.readFile(jsonPath, 'utf-8');
    return JSON.parse(content);
  } catch {
    return null;
  }
}

async function getCurrentProjectSlug(): Promise<string | null> {
  try {
    const content = await fs.readFile(CURRENT_PROJECT_FILE, 'utf-8');
    return content.trim();
  } catch {
    return null;
  }
}

export async function GET() {
  try {
    // 確保 projects 目錄存在
    try {
      await fs.access(PROJECTS_DIR);
    } catch {
      return NextResponse.json({ projects: [], current: null });
    }

    // 讀取所有專案
    const entries = await fs.readdir(PROJECTS_DIR, { withFileTypes: true });
    const projectDirs = entries.filter(e => e.isDirectory() && !e.name.startsWith('.'));
    
    const projects = await Promise.all(
      projectDirs.map(async (dir) => {
        const projectPath = path.join(PROJECTS_DIR, dir.name);
        const data = await readProjectJson(projectPath);
        
        if (!data) return null;
        
        return {
          name: data.name,
          slug: data.slug || dir.name,
          description: data.description || '',
          paperType: data.paper_type || '',
          targetJournal: data.target_journal || '',
          status: data.status || 'concept',
          focus: data.focus,
          createdAt: data.created_at || new Date().toISOString(),
          updatedAt: data.updated_at || new Date().toISOString(),
          memo: data.memo,
        };
      })
    );

    const validProjects = projects.filter(p => p !== null);
    
    // 獲取當前專案
    const currentSlug = await getCurrentProjectSlug();
    const currentProject = currentSlug 
      ? validProjects.find(p => p.slug === currentSlug) || null
      : null;

    return NextResponse.json({
      projects: validProjects,
      current: currentProject,
    });
  } catch (error) {
    console.error('Error reading projects:', error);
    return NextResponse.json(
      { error: 'Failed to read projects' },
      { status: 500 }
    );
  }
}

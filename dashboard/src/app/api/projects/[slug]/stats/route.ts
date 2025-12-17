import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

// 專案根目錄
const PROJECTS_DIR = path.join(process.cwd(), '..', 'projects');

interface ProjectStats {
  references: number;
  drafts: number;
  diagrams: number;
  concept: {
    exists: boolean;
    validated: boolean;
    noveltyScore: number | null;
    lastValidated: string | null;
  };
  preAnalysis: {
    ready: boolean;
    score: number;
    checkedAt: string | null;
  };
  wordCounts: {
    intro: number;
    methods: number;
    results: number;
    discussion: number;
  };
}

async function countFilesInDir(dirPath: string, extension?: string): Promise<number> {
  try {
    const entries = await fs.readdir(dirPath, { withFileTypes: true });
    if (extension) {
      return entries.filter(e => e.isFile() && e.name.endsWith(extension)).length;
    }
    // Count directories (for references)
    return entries.filter(e => e.isDirectory() && !e.name.startsWith('.')).length;
  } catch {
    return 0;
  }
}

async function countWordsInFile(filePath: string): Promise<number> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    // Remove markdown syntax and count words
    const text = content
      .replace(/```[\s\S]*?```/g, '') // Remove code blocks
      .replace(/\[.*?\]\(.*?\)/g, '') // Remove links
      .replace(/[#*_~`]/g, '')        // Remove markdown symbols
      .replace(/\s+/g, ' ')           // Normalize whitespace
      .trim();
    return text.split(/\s+/).filter(w => w.length > 0).length;
  } catch {
    return 0;
  }
}

async function getConceptStatus(projectPath: string): Promise<ProjectStats['concept']> {
  const conceptPath = path.join(projectPath, 'concept.md');
  
  try {
    await fs.access(conceptPath);
    const content = await fs.readFile(conceptPath, 'utf-8');
    
    // Check for validation markers in concept.md or cache
    const cacheDir = path.join(projectPath, '.cache');
    const validationCache = path.join(cacheDir, 'concept_validation.json');
    
    let validated = false;
    let noveltyScore: number | null = null;
    let lastValidated: string | null = null;
    
    try {
      const cacheContent = await fs.readFile(validationCache, 'utf-8');
      const cache = JSON.parse(cacheContent);
      validated = cache.overall_passed === true;
      noveltyScore = cache.novelty_average || null;
      lastValidated = cache.validated_at || null;
    } catch {
      // No cache, check content for indicators
      validated = content.includes('🔒 NOVELTY STATEMENT') && 
                  content.includes('🔒 KEY SELLING POINTS');
    }
    
    return {
      exists: true,
      validated,
      noveltyScore,
      lastValidated,
    };
  } catch {
    return {
      exists: false,
      validated: false,
      noveltyScore: null,
      lastValidated: null,
    };
  }
}

async function getWordCounts(projectPath: string): Promise<ProjectStats['wordCounts']> {
  const draftsDir = path.join(projectPath, 'drafts');
  
  const sections = ['intro', 'methods', 'results', 'discussion'] as const;
  const counts: ProjectStats['wordCounts'] = {
    intro: 0,
    methods: 0,
    results: 0,
    discussion: 0,
  };
  
  for (const section of sections) {
    // Try different naming conventions
    const possibleNames = [
      `${section}.md`,
      `${section}duction.md`,  // intro -> introduction
      `${section}s.md`,        // method -> methods
    ];
    
    for (const name of possibleNames) {
      const filePath = path.join(draftsDir, name);
      const wordCount = await countWordsInFile(filePath);
      if (wordCount > 0) {
        counts[section] = wordCount;
        break;
      }
    }
  }
  
  return counts;
}

async function getPreAnalysisStatus(projectPath: string): Promise<ProjectStats['preAnalysis']> {
  const conceptPath = path.join(projectPath, 'concept.md');
  
  try {
    const content = await fs.readFile(conceptPath, 'utf-8');
    
    // Check for required sections
    const requiredSections = [
      /##\s*📝?\s*Study Design/i,
      /##\s*📝?\s*Participants/i,
      /Sample Size/i,
      /##\s*📝?\s*Outcomes/i,
    ];
    
    const passedCount = requiredSections.filter(regex => regex.test(content)).length;
    const score = Math.round((passedCount / requiredSections.length) * 100);
    
    return {
      ready: passedCount === requiredSections.length,
      score,
      checkedAt: new Date().toISOString(),
    };
  } catch {
    return {
      ready: false,
      score: 0,
      checkedAt: null,
    };
  }
}

export async function GET(
  request: Request,
  { params }: { params: { slug: string } }
) {
  try {
    const { slug } = params;
    const projectPath = path.join(PROJECTS_DIR, slug);
    
    // Check if project exists
    try {
      await fs.access(projectPath);
    } catch {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }
    
    // Gather stats in parallel
    const [references, drafts, diagrams, concept, wordCounts, preAnalysis] = await Promise.all([
      countFilesInDir(path.join(projectPath, 'references')),
      countFilesInDir(path.join(projectPath, 'drafts'), '.md'),
      countFilesInDir(path.join(projectPath, 'results', 'figures')),
      getConceptStatus(projectPath),
      getWordCounts(projectPath),
      getPreAnalysisStatus(projectPath),
    ]);
    
    const stats: ProjectStats = {
      references,
      drafts,
      diagrams,
      concept,
      preAnalysis,
      wordCounts,
    };
    
    return NextResponse.json(stats);
  } catch (error) {
    console.error('Error getting project stats:', error);
    return NextResponse.json(
      { error: 'Failed to get project stats' },
      { status: 500 }
    );
  }
}

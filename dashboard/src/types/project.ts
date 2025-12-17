/**
 * Project and Focus types for MedPaper Dashboard
 */

export type FocusType = 
  | 'exploration'
  | 'concept'
  | 'drafting'
  | 'revision'
  | 'formatting';

export type DraftingSection = 
  | 'intro'
  | 'methods'
  | 'results'
  | 'discussion';

export type ProjectStatus = 
  | 'concept'
  | 'drafting'
  | 'review'
  | 'submitted'
  | 'published';

export interface ProjectFocus {
  type: FocusType;
  section?: DraftingSection;  // Only for drafting
  lastUpdated: string;        // ISO timestamp
}

export interface Project {
  name: string;
  slug: string;
  description: string;
  paperType: string;
  targetJournal: string;
  status: ProjectStatus;
  focus?: ProjectFocus;
  createdAt: string;
  updatedAt: string;
  memo?: string;
}

export interface ProjectProgress {
  concept: {
    validated: boolean;
    noveltyScore?: number;
  };
  sections: {
    intro: { wordCount: number; status: 'not-started' | 'drafting' | 'complete' };
    methods: { wordCount: number; status: 'not-started' | 'drafting' | 'complete' };
    results: { wordCount: number; status: 'not-started' | 'drafting' | 'complete' };
    discussion: { wordCount: number; status: 'not-started' | 'drafting' | 'complete' };
  };
  references: number;
  diagrams: number;
}

export interface ProjectStats {
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

export const FOCUS_OPTIONS: { value: FocusType; label: string; icon: string }[] = [
  { value: 'exploration', label: 'Literature Exploration', icon: '🔍' },
  { value: 'concept', label: 'Concept Development', icon: '💡' },
  { value: 'drafting', label: 'Drafting', icon: '✍️' },
  { value: 'revision', label: 'Revision', icon: '🔄' },
  { value: 'formatting', label: 'Formatting & Export', icon: '📄' },
];

export const SECTION_OPTIONS: { value: DraftingSection; label: string }[] = [
  { value: 'intro', label: 'Introduction' },
  { value: 'methods', label: 'Methods' },
  { value: 'results', label: 'Results' },
  { value: 'discussion', label: 'Discussion' },
];

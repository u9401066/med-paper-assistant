'use client';

import { Project } from '@/types/project';

interface ProjectSelectorProps {
  projects: Project[];
  currentProject: Project | null;
  onSelect: (slug: string) => void;
  isLoading?: boolean;
}

export function ProjectSelector({ 
  projects, 
  currentProject, 
  onSelect,
  isLoading 
}: ProjectSelectorProps) {
  return (
    <div className="relative">
      <label className="block text-xs text-gray-500 mb-1">Current Project</label>
      <select
        value={currentProject?.slug || ''}
        onChange={(e) => onSelect(e.target.value)}
        disabled={isLoading}
        className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg 
                   text-sm font-medium text-gray-900
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed
                   appearance-none cursor-pointer"
      >
        <option value="">Select a project...</option>
        {projects.map((project) => (
          <option key={project.slug} value={project.slug}>
            {project.name}
          </option>
        ))}
      </select>
      <div className="absolute right-3 top-7 pointer-events-none">
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}

'use client';

import { Project, FOCUS_OPTIONS } from '@/types/project';

interface ProjectCardProps {
  project: Project;
  isActive: boolean;
  onClick: () => void;
}

export function ProjectCard({ project, isActive, onClick }: ProjectCardProps) {
  const focusInfo = FOCUS_OPTIONS.find(f => f.value === project.focus?.type);
  
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border cursor-pointer transition-all duration-150
                 ${isActive 
                   ? 'border-blue-300 bg-blue-50 shadow-sm' 
                   : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                 }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 truncate">{project.name}</h3>
          {project.description && (
            <p className="text-sm text-gray-500 mt-0.5 truncate">{project.description}</p>
          )}
        </div>
        {isActive && (
          <span className="flex-shrink-0 w-2 h-2 mt-2 ml-2 bg-blue-500 rounded-full"></span>
        )}
      </div>
      
      <div className="mt-3 flex items-center gap-2 text-xs">
        {project.focus && focusInfo && (
          <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
            {focusInfo.icon} {focusInfo.label}
            {project.focus.section && ` → ${project.focus.section}`}
          </span>
        )}
        {project.paperType && (
          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
            {project.paperType}
          </span>
        )}
      </div>
      
      {project.targetJournal && (
        <div className="mt-2 text-xs text-gray-400">
          Target: {project.targetJournal}
        </div>
      )}
    </div>
  );
}

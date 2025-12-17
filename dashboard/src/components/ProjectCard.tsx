'use client';

import { useEffect, useState } from 'react';
import { Project, ProjectStats, FOCUS_OPTIONS } from '@/types/project';

interface ProjectCardProps {
  project: Project;
  isActive: boolean;
  onClick: () => void;
}

export function ProjectCard({ project, isActive, onClick }: ProjectCardProps) {
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const focusInfo = FOCUS_OPTIONS.find(f => f.value === project.focus?.type);
  
  // Fetch stats when card becomes visible or active
  useEffect(() => {
    const fetchStats = async () => {
      setIsLoadingStats(true);
      try {
        const res = await fetch(`/api/projects/${project.slug}/stats`);
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      } finally {
        setIsLoadingStats(false);
      }
    };
    
    fetchStats();
  }, [project.slug]);
  
  const totalWords = stats ? 
    stats.wordCounts.intro + stats.wordCounts.methods + 
    stats.wordCounts.results + stats.wordCounts.discussion : 0;
  
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border cursor-pointer transition-all duration-150
                 ${isActive 
                   ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/30 shadow-sm' 
                   : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm'
                 }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">{project.name}</h3>
          {project.description && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate">{project.description}</p>
          )}
        </div>
        {isActive && (
          <span className="flex-shrink-0 w-2 h-2 mt-2 ml-2 bg-blue-500 rounded-full"></span>
        )}
      </div>
      
      {/* Stats Row */}
      {stats && (
        <div className="mt-2 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          {/* References */}
          <span className="flex items-center gap-1" title="References">
            📚 {stats.references}
          </span>
          
          {/* Concept Status */}
          {stats.concept.exists && (
            <span 
              className={`flex items-center gap-1 ${
                stats.concept.validated ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
              }`}
              title={stats.concept.validated 
                ? `Novelty: ${stats.concept.noveltyScore || '?'}/100` 
                : 'Concept not validated'}
            >
              {stats.concept.validated ? '✅' : '⚠️'}
              {stats.concept.noveltyScore ? `${stats.concept.noveltyScore}` : 'concept'}
            </span>
          )}
          
          {/* Pre-Analysis Checklist */}
          {stats.concept.exists && (
            <span 
              className={`flex items-center gap-1 ${
                stats.preAnalysis.ready ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'
              }`}
              title={`Pre-Analysis: ${stats.preAnalysis.score}%`}
            >
              📋 {stats.preAnalysis.score}%
            </span>
          )}
          
          {/* Word Count */}
          {totalWords > 0 && (
            <span className="flex items-center gap-1" title="Total words">
              📝 {totalWords.toLocaleString()}
            </span>
          )}
          
          {/* Diagrams */}
          {stats.diagrams > 0 && (
            <span className="flex items-center gap-1" title="Diagrams">
              🎨 {stats.diagrams}
            </span>
          )}
        </div>
      )}
      
      {isLoadingStats && (
        <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">Loading stats...</div>
      )}
      
      <div className="mt-3 flex items-center gap-2 text-xs">
        {project.focus && focusInfo && (
          <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
            {focusInfo.icon} {focusInfo.label}
            {project.focus.section && ` → ${project.focus.section}`}
          </span>
        )}
        {project.paperType && (
          <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
            {project.paperType}
          </span>
        )}
      </div>
      
      {project.targetJournal && (
        <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Target: {project.targetJournal}
        </div>
      )}
    </div>
  );
}

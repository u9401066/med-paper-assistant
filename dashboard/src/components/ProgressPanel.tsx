'use client';

import { useEffect, useState } from 'react';
import { ProjectStats } from '@/types/project';

interface ProgressPanelProps {
  projectSlug: string | null;
}

export function ProgressPanel({ projectSlug }: ProgressPanelProps) {
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectSlug) {
      setStats(null);
      return;
    }

    const fetchStats = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/projects/${projectSlug}/stats`);
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, [projectSlug]);

  if (!projectSlug) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 dark:text-gray-400">Select a project to view progress</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        Loading progress...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
        {error}
      </div>
    );
  }

  if (!stats) return null;

  const totalWords =
    stats.wordCounts.intro + stats.wordCounts.methods +
    stats.wordCounts.results + stats.wordCounts.discussion;

  const sections = [
    { key: 'intro', label: 'Introduction', words: stats.wordCounts.intro },
    { key: 'methods', label: 'Methods', words: stats.wordCounts.methods },
    { key: 'results', label: 'Results', words: stats.wordCounts.results },
    { key: 'discussion', label: 'Discussion', words: stats.wordCounts.discussion },
  ];

  return (
    <div className="space-y-4">
      {/* Concept Status Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          💡 Concept Status
        </h3>

        {stats.concept.exists ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Validation</span>
              <span className={`text-sm font-medium ${
                stats.concept.validated ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
              }`}>
                {stats.concept.validated ? '✅ Passed' : '⚠️ Not validated'}
              </span>
            </div>

            {stats.concept.noveltyScore !== null && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Novelty Score</span>
                <span className={`text-sm font-medium ${
                  stats.concept.noveltyScore >= 75 ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
                }`}>
                  {stats.concept.noveltyScore}/100
                </span>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No concept.md found</p>
        )}
      </div>

      {/* Pre-Analysis Checklist Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          📋 Pre-Analysis Checklist
        </h3>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
            <span className={`text-sm font-medium ${
              stats.preAnalysis.ready ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
            }`}>
              {stats.preAnalysis.ready ? '✅ Ready' : '⚠️ Incomplete'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Completion</span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {stats.preAnalysis.score}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                stats.preAnalysis.ready ? 'bg-green-500' : 'bg-amber-500'
              }`}
              style={{ width: `${stats.preAnalysis.score}%` }}
            />
          </div>

          {!stats.preAnalysis.ready && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Missing: Study Design, Participants, Sample Size, or Outcomes
            </p>
          )}
        </div>
      </div>

      {/* References & Assets Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          📚 References & Assets
        </h3>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.references}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">References</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.drafts}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Drafts</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{stats.diagrams}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Diagrams</div>
          </div>
        </div>
      </div>

      {/* Word Counts Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          📝 Draft Progress
          <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
            ({totalWords.toLocaleString()} words total)
          </span>
        </h3>

        <div className="space-y-3">
          {sections.map((section) => {
            const percentage = totalWords > 0
              ? Math.round((section.words / totalWords) * 100)
              : 0;

            return (
              <div key={section.key}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">{section.label}</span>
                  <span className="text-gray-900 dark:text-gray-100 font-medium">
                    {section.words.toLocaleString()} words
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      section.words > 0 ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                    style={{ width: `${Math.min(percentage * 2, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800 rounded-lg p-3">
        <p className="text-sm text-blue-700 dark:text-blue-300">
          💡 <strong>Tip:</strong> Use Copilot Chat to work on sections
        </p>
        <div className="mt-2 space-y-1 text-xs text-blue-600 dark:text-blue-400">
          <p>• &quot;Help me write the Introduction&quot;</p>
          <p>• &quot;Validate my concept&quot;</p>
          <p>• &quot;Check pre-analysis readiness&quot;</p>
        </div>
      </div>
    </div>
  );
}

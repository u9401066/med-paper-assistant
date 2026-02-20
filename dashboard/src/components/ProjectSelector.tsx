'use client';

import { useState } from 'react';
import { Project } from '@/types/project';

interface ProjectSelectorProps {
  projects: Project[];
  currentProject: Project | null;
  onSelect: (slug: string, options?: { openFiles?: boolean; closeOthers?: boolean }) => void;
  isLoading?: boolean;
}

export function ProjectSelector({
  projects,
  currentProject,
  onSelect,
  isLoading
}: ProjectSelectorProps) {
  const [showOptions, setShowOptions] = useState(false);
  const [pendingSlug, setPendingSlug] = useState<string | null>(null);

  const handleChange = (slug: string) => {
    if (!slug || slug === currentProject?.slug) return;

    // 顯示選項對話框
    setPendingSlug(slug);
    setShowOptions(true);
  };

  const handleConfirm = (closeOthers: boolean) => {
    if (pendingSlug) {
      onSelect(pendingSlug, { openFiles: true, closeOthers });
    }
    setShowOptions(false);
    setPendingSlug(null);
  };

  const handleCancel = () => {
    setShowOptions(false);
    setPendingSlug(null);
  };

  return (
    <div className="relative">
      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Current Project</label>
      <select
        value={currentProject?.slug || ''}
        onChange={(e) => handleChange(e.target.value)}
        disabled={isLoading}
        className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg
                   text-sm font-medium text-gray-900 dark:text-gray-100
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

      {/* 切換選項對話框 */}
      {showOptions && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-4 m-4 max-w-sm w-full">
            <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
              切換專案 / Switch Project
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              要如何處理目前開啟的文件？
              <br />
              <span className="text-gray-400 dark:text-gray-500">How to handle currently open files?</span>
            </p>
            <div className="space-y-2">
              <button
                onClick={() => handleConfirm(true)}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm
                          hover:bg-blue-700 transition-colors"
              >
                🔄 開啟新專案 + 關閉其他文件
                <br />
                <span className="text-xs opacity-75">Open new + Close others</span>
              </button>
              <button
                onClick={() => handleConfirm(false)}
                className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm
                          hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                📂 只開啟新專案文件
                <br />
                <span className="text-xs opacity-75">Only open new project files</span>
              </button>
              <button
                onClick={handleCancel}
                className="w-full px-4 py-2 text-gray-500 dark:text-gray-400 text-sm hover:text-gray-700 dark:hover:text-gray-300"
              >
                取消 / Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

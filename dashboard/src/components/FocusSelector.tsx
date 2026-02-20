'use client';

import { ProjectFocus, FocusType, DraftingSection, FOCUS_OPTIONS, SECTION_OPTIONS } from '@/types/project';

interface FocusSelectorProps {
  currentFocus?: ProjectFocus;
  onFocusChange: (focus: ProjectFocus) => void;
  disabled?: boolean;
}

export function FocusSelector({ currentFocus, onFocusChange, disabled }: FocusSelectorProps) {
  const handleTypeChange = (type: FocusType) => {
    onFocusChange({
      type,
      section: type === 'drafting' ? (currentFocus?.section || 'intro') : undefined,
      lastUpdated: new Date().toISOString(),
    });
  };

  const handleSectionChange = (section: DraftingSection) => {
    onFocusChange({
      type: 'drafting',
      section,
      lastUpdated: new Date().toISOString(),
    });
  };

  return (
    <div className="space-y-3">
      <label className="block text-xs text-gray-500 dark:text-gray-400">Work Focus</label>

      <div className="space-y-1">
        {FOCUS_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => handleTypeChange(option.value)}
            disabled={disabled}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left
                       transition-colors duration-150
                       ${currentFocus?.type === option.value
                         ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                         : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'
                       }
                       disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <span className="text-base">{option.icon}</span>
            <span className="font-medium">{option.label}</span>
            {currentFocus?.type === option.value && (
              <span className="ml-auto text-blue-500 dark:text-blue-400">●</span>
            )}
          </button>
        ))}
      </div>

      {/* Section selector for Drafting */}
      {currentFocus?.type === 'drafting' && (
        <div className="ml-6 mt-2 space-y-1">
          <label className="block text-xs text-gray-400 dark:text-gray-500 mb-1">Section</label>
          {SECTION_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => handleSectionChange(option.value)}
              disabled={disabled}
              className={`w-full px-3 py-1.5 rounded text-sm text-left
                         transition-colors duration-150
                         ${currentFocus?.section === option.value
                           ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                           : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                         }
                         disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

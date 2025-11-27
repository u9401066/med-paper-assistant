"""
Draft Entity - Represents a paper draft or section.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import re


@dataclass
class Draft:
    """
    Paper draft entity.
    
    Represents a markdown draft file with sections and citations.
    """
    filename: str
    content: str
    path: Optional[Path] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def sections(self) -> Dict[str, str]:
        """Parse content into sections."""
        sections = {}
        current_section = "Preamble"
        current_content = []
        
        for line in self.content.split('\n'):
            # Check for section headers (## or #)
            if line.startswith('## '):
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            elif line.startswith('# ') and not sections:
                # Title
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = "Title"
                current_content = [line[2:].strip()]
            else:
                current_content.append(line)
        
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    @property
    def word_count(self) -> int:
        """Get total word count."""
        # Remove markdown formatting and count words
        text = re.sub(r'[#*_\[\]()]', '', self.content)
        return len(text.split())
    
    @property
    def section_word_counts(self) -> Dict[str, int]:
        """Get word count per section."""
        counts = {}
        for section, content in self.sections.items():
            text = re.sub(r'[#*_\[\]()]', '', content)
            counts[section] = len(text.split())
        return counts
    
    @property
    def citations(self) -> List[str]:
        """Extract citation markers from content."""
        # Match [1], [2], [1-3], [1,2,3] patterns
        pattern = r'\[(\d+(?:[-,]\d+)*)\]'
        matches = re.findall(pattern, self.content)
        
        citations = set()
        for match in matches:
            if '-' in match:
                start, end = match.split('-')
                citations.update(range(int(start), int(end) + 1))
            elif ',' in match:
                citations.update(int(n) for n in match.split(','))
            else:
                citations.add(int(match))
        
        return sorted(citations)
    
    @property
    def has_protected_content(self) -> bool:
        """Check if draft has protected content markers."""
        return '🔒' in self.content
    
    @property
    def protected_sections(self) -> List[str]:
        """Get names of protected sections."""
        protected = []
        for line in self.content.split('\n'):
            if '🔒' in line and line.startswith('#'):
                section_name = re.sub(r'[#🔒]', '', line).strip()
                protected.append(section_name)
        return protected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "word_count": self.word_count,
            "sections": list(self.sections.keys()),
            "section_word_counts": self.section_word_counts,
            "citations": self.citations,
            "has_protected_content": self.has_protected_content,
            "protected_sections": self.protected_sections,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

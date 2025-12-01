"""
Skill management tools for MCP.

Skills are workflow definitions that guide the AI agent through complex tasks.
"""

import json
from pathlib import Path
from fastmcp import FastMCP

# Skills directory relative to project root
SKILLS_DIR = Path(__file__).parent.parent.parent.parent.parent.parent.parent / ".skills"


def register_skill_tools(mcp: FastMCP):
    """Register skill management tools."""

    @mcp.tool()
    async def list_skills() -> str:
        """
        列出所有可用的工作流程技能 (Skills)。
        
        Skills 是完整的工作流程定義，告訴你如何組合多個工具來完成複雜任務。
        當用戶要求執行複雜任務（如文獻回顧、撰寫論文）時，應該先列出並載入適合的 Skill。
        
        Returns:
            JSON 格式的 Skills 列表，包含名稱、分類、路徑和簡述
        """
        if not SKILLS_DIR.exists():
            return json.dumps({"error": "Skills directory not found", "path": str(SKILLS_DIR)})
        
        skills = []
        for path in SKILLS_DIR.rglob("*.md"):
            # Skip template and readme
            if path.name.startswith("_") or path.name.upper() == "README.MD" or path.name.upper() == "INTEGRATION.MD":
                continue
            
            # Extract first line as description
            try:
                content = path.read_text(encoding="utf-8")
                first_line = ""
                for line in content.split("\n"):
                    if line.startswith(">"):
                        first_line = line.lstrip("> ").strip()
                        break
            except:
                first_line = ""
            
            skills.append({
                "name": path.stem,
                "category": path.parent.name if path.parent != SKILLS_DIR else "root",
                "path": str(path.relative_to(SKILLS_DIR)),
                "description": first_line
            })
        
        # Sort by category then name
        skills.sort(key=lambda x: (x["category"], x["name"]))
        
        return json.dumps({
            "skills_count": len(skills),
            "skills": skills,
            "usage": "Use load_skill(skill_name) to load a specific skill"
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def load_skill(skill_name: str) -> str:
        """
        載入指定的工作流程技能。
        
        載入後，請遵循 Skill 中定義的：
        - 工作流程 (Phases)
        - 決策點 (何時詢問用戶)
        - 使用的工具
        - 輸出產物
        
        Args:
            skill_name: 技能名稱（不含 .md），如 "literature_review", "concept_development"
                       也可以包含分類，如 "research/literature_review"
        
        Returns:
            Skill 的完整內容
        """
        if not SKILLS_DIR.exists():
            return f"Error: Skills directory not found at {SKILLS_DIR}"
        
        # Try exact path first
        skill_path = SKILLS_DIR / f"{skill_name}.md"
        
        if not skill_path.exists():
            # Try with .md extension
            skill_path = SKILLS_DIR / skill_name
            if not skill_path.suffix:
                skill_path = skill_path.with_suffix(".md")
        
        if not skill_path.exists():
            # Search in subdirectories
            for subdir in SKILLS_DIR.iterdir():
                if subdir.is_dir():
                    candidate = subdir / f"{skill_name}.md"
                    if candidate.exists():
                        skill_path = candidate
                        break
        
        if not skill_path.exists():
            # List available skills
            available = []
            for p in SKILLS_DIR.rglob("*.md"):
                if not p.name.startswith("_") and p.name.upper() not in ["README.MD", "INTEGRATION.MD"]:
                    available.append(p.stem)
            
            return f"Skill '{skill_name}' not found.\n\nAvailable skills:\n" + "\n".join(f"  - {s}" for s in sorted(available))
        
        try:
            content = skill_path.read_text(encoding="utf-8")
            return f"# Skill Loaded: {skill_path.stem}\n\n{content}"
        except Exception as e:
            return f"Error reading skill file: {e}"

    @mcp.tool()
    async def suggest_skill(task_description: str) -> str:
        """
        根據任務描述建議適合的 Skill。
        
        Args:
            task_description: 用戶想要完成的任務描述
        
        Returns:
            建議的 Skill 及理由
        """
        # Simple keyword matching for now
        # Could be enhanced with embeddings or LLM
        
        task_lower = task_description.lower()
        
        suggestions = []
        
        # Literature review keywords
        if any(kw in task_lower for kw in ["文獻", "論文", "搜尋", "review", "literature", "search", "pubmed", "找"]):
            suggestions.append({
                "skill": "literature_review",
                "category": "research",
                "confidence": "high",
                "reason": "任務涉及文獻搜尋或回顧"
            })
        
        # Concept development keywords
        if any(kw in task_lower for kw in ["concept", "概念", "研究設計", "hypothesis", "假說", "novelty"]):
            suggestions.append({
                "skill": "concept_development",
                "category": "research",
                "confidence": "high",
                "reason": "任務涉及研究概念或假說發展"
            })
        
        # Writing keywords
        if any(kw in task_lower for kw in ["寫", "撰寫", "draft", "write", "introduction", "methods", "discussion", "前言", "方法", "討論"]):
            if "introduction" in task_lower or "前言" in task_lower:
                suggestions.append({
                    "skill": "draft_introduction",
                    "category": "writing",
                    "confidence": "high",
                    "reason": "任務涉及撰寫 Introduction"
                })
            elif "method" in task_lower or "方法" in task_lower:
                suggestions.append({
                    "skill": "draft_methods",
                    "category": "writing",
                    "confidence": "high",
                    "reason": "任務涉及撰寫 Methods"
                })
            elif "discussion" in task_lower or "討論" in task_lower:
                suggestions.append({
                    "skill": "draft_discussion",
                    "category": "writing",
                    "confidence": "high",
                    "reason": "任務涉及撰寫 Discussion"
                })
        
        # Analysis keywords
        if any(kw in task_lower for kw in ["統計", "分析", "statistic", "analysis", "t-test", "correlation"]):
            suggestions.append({
                "skill": "statistical_analysis",
                "category": "analysis",
                "confidence": "high",
                "reason": "任務涉及統計分析"
            })
        
        # Figure keywords
        if any(kw in task_lower for kw in ["圖", "figure", "diagram", "plot", "chart", "prisma", "flowchart"]):
            suggestions.append({
                "skill": "figure_generation",
                "category": "analysis",
                "confidence": "high",
                "reason": "任務涉及圖表製作"
            })
        
        if not suggestions:
            return json.dumps({
                "message": "No specific skill matched. Consider describing the task in more detail.",
                "tip": "Use list_skills() to see all available skills",
                "common_triggers": {
                    "literature_review": "文獻回顧、找論文、systematic review",
                    "concept_development": "發展概念、研究設計、hypothesis",
                    "draft_*": "撰寫論文各章節",
                    "statistical_analysis": "統計分析、跑統計",
                    "figure_generation": "製作圖表、畫流程圖"
                }
            }, indent=2, ensure_ascii=False)
        
        return json.dumps({
            "task": task_description,
            "suggestions": suggestions,
            "next_step": f"Use load_skill('{suggestions[0]['skill']}') to load the recommended skill"
        }, indent=2, ensure_ascii=False)

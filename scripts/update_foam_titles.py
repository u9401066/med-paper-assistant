"""Fix title field in existing reference markdown files for Foam."""
import re
from pathlib import Path

refs_dir = Path('projects/airway-device-oral-lip-injury-comparison/references')
for md_file in refs_dir.rglob('*.md'):
    content = md_file.read_text(encoding='utf-8')
    
    # Split by frontmatter delimiter
    parts = content.split('---')
    if len(parts) < 3:
        print(f'Skipped (no frontmatter): {md_file.name}')
        continue
    
    frontmatter = parts[1]
    body = '---'.join(parts[2:])  # Everything after frontmatter
    
    # Get the REAL title from markdown body (first # heading after frontmatter)
    title_match = re.search(r'^# (.+)$', body, re.MULTILINE)
    if not title_match:
        print(f'Warning: No title found in body of {md_file.name}')
        continue
    
    real_title = title_match.group(1).strip().replace('"', '\\"')
    
    # Check if title exists and is wrong
    existing_title = re.search(r'^title: "(.+)"$', frontmatter, re.MULTILINE)
    if existing_title:
        old_title = existing_title.group(1)
        if old_title == real_title:
            print(f'Skipped (title correct): {md_file.name}')
            continue
        # Replace wrong title
        new_frontmatter = re.sub(
            r'^title: ".+"$',
            f'title: "{real_title}"',
            frontmatter,
            flags=re.MULTILINE
        )
    else:
        # Add title at the beginning of frontmatter
        new_frontmatter = f'\ntitle: "{real_title}"' + frontmatter
    
    new_content = '---' + new_frontmatter + '---' + body
    md_file.write_text(new_content, encoding='utf-8')
    print(f'Fixed: {md_file.name} -> "{real_title[:50]}..."')

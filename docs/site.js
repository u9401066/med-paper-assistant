(() => {
  "use strict";

  const manifest = window.MEDPAPER_DOCS;
  const title = document.getElementById("site-title");
  const subtitle = document.getElementById("site-subtitle");
  const root = document.getElementById("documentation-groups");
  const search = document.getElementById("search-input");

  if (!manifest || !root || !search) {
    return;
  }

  title.textContent = manifest.title;
  subtitle.textContent = manifest.subtitle;

  function render(query = "") {
    const needle = query.trim().toLocaleLowerCase();
    root.replaceChildren();
    let visible = 0;

    for (const group of manifest.groups) {
      const matches = group.items.filter((item) => {
        const searchable = `${group.title} ${item.title} ${item.description}`.toLocaleLowerCase();
        return !needle || searchable.includes(needle);
      });
      if (!matches.length) continue;

      const section = document.createElement("section");
      section.className = "doc-group";
      const heading = document.createElement("h2");
      heading.textContent = group.title;
      section.appendChild(heading);

      const grid = document.createElement("div");
      grid.className = "card-grid";
      for (const item of matches) {
        visible += 1;
        const link = document.createElement("a");
        link.className = "doc-card";
        link.href = item.path;
        const cardTitle = document.createElement("h3");
        cardTitle.textContent = item.title;
        const description = document.createElement("p");
        description.textContent = item.description;
        link.append(cardTitle, description);
        grid.appendChild(link);
      }
      section.appendChild(grid);
      root.appendChild(section);
    }

    if (!visible) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No documentation page matches this search.";
      root.appendChild(empty);
    }
  }

  search.addEventListener("input", () => render(search.value));
  render();
})();

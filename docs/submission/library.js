(function () {
  "use strict";

  const progress = document.getElementById("reading-progress");
  const sections = Array.from(document.querySelectorAll("[data-doc-section]"));
  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  const search = document.getElementById("section-search");
  const result = document.getElementById("search-result");
  const collapseAll = document.getElementById("collapse-all");
  const tocToggle = document.getElementById("toc-toggle");
  const pageSwitcher = document.getElementById("page-switcher");

  function updateProgress() {
    const available = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = available > 0 ? window.scrollY / available : 0;
    progress.style.width = Math.min(100, Math.max(0, ratio * 100)) + "%";
  }

  function setSection(section, expanded) {
    const button = section.querySelector(".section-toggle");
    const body = section.querySelector(".section-body");
    button.setAttribute("aria-expanded", String(expanded));
    button.setAttribute("aria-label", (expanded ? "Collapse " : "Expand ") + button.dataset.sectionTitle);
    body.hidden = !expanded;
  }

  document.querySelectorAll(".section-toggle").forEach(function (button) {
    button.addEventListener("click", function () {
      const section = button.closest("[data-doc-section]");
      setSection(section, button.getAttribute("aria-expanded") !== "true");
    });
  });

  let collapsed = false;
  collapseAll.addEventListener("click", function () {
    collapsed = !collapsed;
    sections.forEach(function (section) { setSection(section, !collapsed); });
    collapseAll.textContent = collapsed ? "Expand all" : "Collapse all";
  });

  search.addEventListener("input", function () {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    sections.forEach(function (section) {
      const matches = !query || section.textContent.toLocaleLowerCase().includes(query);
      section.hidden = !matches;
      if (matches) {
        visible += 1;
        if (query) setSection(section, true);
      }
    });
    result.textContent = query ? visible + " of " + sections.length + " sections match" : sections.length + " sections";
  });

  tocToggle.addEventListener("click", function () {
    const open = document.body.classList.toggle("toc-open");
    tocToggle.setAttribute("aria-expanded", String(open));
  });

  pageSwitcher.addEventListener("change", function () {
    if (pageSwitcher.value) window.location.href = pageSwitcher.value;
  });

  window.addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        tocLinks.forEach(function (link) {
          if (link.getAttribute("href") === "#" + entry.target.id) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        });
      });
    }, { rootMargin: "-22% 0px -68% 0px", threshold: 0 });
    sections.forEach(function (section) { observer.observe(section); });
  }
}());

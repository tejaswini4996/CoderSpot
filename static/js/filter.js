// filter.js
//
// Handles everything on the calendar page:
//   - kind filter buttons (All / Women in Tech / Open Source / Hackathon)
//   - the keyword search box
//   - the prize-type dropdown (heuristic: looks for words like "cash",
//     "stipend", "swag" etc. in each event's own text — there's no
//     separate prize-type field in the data, so this searches the
//     summary/window text directly)
//   - the "+ Calendar" dropdown on each event card

document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.querySelectorAll(".filter-btn");
  const fixtures = document.querySelectorAll(".fixture");
  const monthBlocks = document.querySelectorAll(".month-block");
  const searchInput = document.getElementById("search-input");
  const prizeFilter = document.getElementById("prize-filter");
  const noResultsMsg = document.getElementById("no-results-msg");

  let activeKindFilter = "all";

  // Keyword sets used to guess a "prize type" from an event's own text,
  // since the underlying data doesn't have a dedicated prize-type field.
  const PRIZE_KEYWORDS = {
    cash: ["cash", "$", "prize money", "in prizes"],
    stipend: ["stipend", "paid ", "paid,", "paid.", "paid internship"],
    swag: ["swag", "certificate", "t-shirt", "recognition"],
    unpaid: ["unpaid", "volunteer", "no stipend"],
  };

  function matchesPrizeType(searchText, prizeType) {
    if (prizeType === "all") return true;
    const keywords = PRIZE_KEYWORDS[prizeType] || [];
    return keywords.some(function (kw) { return searchText.includes(kw); });
  }

  function applyAllFilters() {
    const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
    const prizeType = prizeFilter ? prizeFilter.value : "all";
    let anyVisible = false;

    fixtures.forEach(function (fixture) {
      const kind = fixture.dataset.kind;
      const searchText = fixture.dataset.search || "";

      const matchesKind = activeKindFilter === "all" || kind === activeKindFilter;
      const matchesQuery = !query || searchText.includes(query);
      const matchesPrize = matchesPrizeType(searchText, prizeType);

      const visible = matchesKind && matchesQuery && matchesPrize;
      fixture.style.display = visible ? "" : "none";
      if (visible) anyVisible = true;
    });

    monthBlocks.forEach(function (block) {
      const visibleFixtures = block.querySelectorAll(
        '.fixture:not([style*="display: none"])'
      );
      block.style.display = visibleFixtures.length ? "" : "none";
    });

    if (noResultsMsg) {
      noResultsMsg.style.display = anyVisible ? "none" : "block";
    }
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      buttons.forEach(function (b) { b.classList.remove("is-active"); });
      button.classList.add("is-active");
      activeKindFilter = button.dataset.filter;
      applyAllFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", applyAllFilters);
  }
  if (prizeFilter) {
    prizeFilter.addEventListener("change", applyAllFilters);
  }

  // Apply whichever kind filter is marked active on page load (e.g. from
  // a "Browse Open Source" link on the home page).
  const preSelected = document.querySelector(".filter-btn.is-active");
  if (preSelected) {
    activeKindFilter = preSelected.dataset.filter;
  }
  applyAllFilters();

  // "+ Calendar" dropdown toggle — click to open, click elsewhere to close.
  document.querySelectorAll(".add-to-cal-toggle").forEach(function (toggle) {
    toggle.addEventListener("click", function (event) {
      event.stopPropagation();
      const menu = toggle.nextElementSibling;
      const isOpen = menu.classList.contains("is-open");
      document.querySelectorAll(".add-to-cal-menu.is-open").forEach(function (m) {
        m.classList.remove("is-open");
      });
      if (!isOpen) menu.classList.add("is-open");
    });
  });

  document.addEventListener("click", function () {
    document.querySelectorAll(".add-to-cal-menu.is-open").forEach(function (m) {
      m.classList.remove("is-open");
    });
  });
});

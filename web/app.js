(() => {
  "use strict";

  const data = window.POLAR_KG_DATA;
  if (!data) return;

  const i18n = data.i18n || {};
  const root = document.documentElement;
  const byId = new Map([...data.concepts, ...data.nodes].map(item => [item.id, item]));
  const sourceById = new Map(data.sources.map(item => [item.id, item]));
  const claimsBySource = new Map();
  data.claims.forEach(claim => {
    if (!claimsBySource.has(claim.source_id)) claimsBySource.set(claim.source_id, []);
    claimsBySource.get(claim.source_id).push(claim);
  });

  const state = {
    selectedSource: null,
    conceptFocus: null,
    commandOpen: false,
    commandIndex: 0,
    commandMatches: [],
    returnFocus: null,
  };

  const ids = [
    "statSources", "statClaims", "statRecent", "statCandidates", "searchInput", "domainFilter",
    "poleFilter", "yearFilter", "evidenceFilter", "resetFilters", "sourceCount", "sourceList",
    "graphSvg", "graphTitle", "graphSubtitle", "graphNote", "overviewButton", "conceptFocus",
    "detailBody", "freshness", "toast", "brandHome", "metaDescription", "activeFilterBar",
    "activeFilterChips", "clearAllFilters", "openCommand", "commandScrim", "commandDialog",
    "commandInput", "commandResults", "commandPreview",
  ];
  const els = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
  const themeButtons = [...document.querySelectorAll("[data-theme-choice]")];
  const languageButtons = [...document.querySelectorAll("[data-language-choice]")];
  const systemPreference = window.matchMedia("(prefers-color-scheme: dark)");

  const escapeHTML = value => String(value ?? "").replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]));
  const uniq = values => [...new Set(values.filter(Boolean))];
  const isChinese = () => root.dataset.language === "zh-CN";
  const locale = () => isChinese() ? "zh-CN" : "en";

  function t(key, values = {}) {
    const language = root.dataset.language || "en";
    let text = i18n.ui?.[language]?.[key] ?? i18n.ui?.en?.[key] ?? key;
    Object.entries(values).forEach(([name, value]) => {
      text = String(text).replaceAll(`{${name}}`, value);
    });
    return text;
  }

  function mappedLabel(group, value) {
    if (!isChinese()) {
      if (["evidence", "confidence"].includes(group)) return String(value).replace(/^./, char => char.toUpperCase());
      if (group === "predicates") return String(value).replaceAll("_", " ");
      return value;
    }
    return i18n.labels?.[group]?.[value] || value;
  }

  const translatedSource = source => i18n.sources?.[source.id] || {};
  const translatedClaim = claim => i18n.claims?.[claim.id] || {};
  const sourceTitle = source => isChinese() ? (translatedSource(source).title || source.title) : source.title;
  const labelFor = id => {
    if (sourceById.has(id)) return sourceTitle(sourceById.get(id));
    if (isChinese() && i18n.concepts?.[id]?.label) return i18n.concepts[id].label;
    return byId.get(id)?.label || id;
  };

  function sourceView(source) {
    const translation = translatedSource(source);
    const profile = source.study_profile || {};
    const translatedProfile = translation.study_profile || {};
    if (!isChinese()) {
      return {
        title: source.title,
        studyType: source.study_type,
        profile,
        findings: source.key_findings || [],
        limitations: source.limitations || [],
        citeFor: source.cite_for || [],
        doNotOvercite: source.do_not_overcite || [],
        curationBasis: source.curation?.basis || "",
      };
    }
    return {
      title: translation.title || source.title,
      studyType: translation.study_type || source.study_type,
      profile: {...profile, ...translatedProfile},
      findings: translation.key_findings || source.key_findings || [],
      limitations: translation.limitations || source.limitations || [],
      citeFor: translation.cite_for || source.cite_for || [],
      doNotOvercite: translation.do_not_overcite || source.do_not_overcite || [],
      curationBasis: translation.curation_basis || source.curation?.basis || "",
    };
  }

  function claimView(claim) {
    const translation = translatedClaim(claim);
    if (!isChinese()) return claim;
    return {
      ...claim,
      statement: translation.statement || claim.statement,
      scope: translation.scope || claim.scope,
      evidence_basis: translation.evidence_basis || claim.evidence_basis,
      locator: translation.locator || claim.locator,
      confidence_note: translation.confidence_note || claim.confidence_note,
    };
  }

  function applyStaticTranslations() {
    root.lang = root.dataset.language;
    document.title = t("site_title");
    els.metaDescription?.setAttribute("content", t("meta_description"));
    document.querySelectorAll("[data-i18n]").forEach(element => {
      element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
      element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(element => {
      element.setAttribute("aria-label", t(element.dataset.i18nAria));
    });
    languageButtons.forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.languageChoice === root.dataset.language));
      button.setAttribute("aria-label", t(button.dataset.languageChoice === "en" ? "english" : "chinese"));
    });
  }

  function applyTheme(mode, {persist = true} = {}) {
    root.dataset.theme = mode;
    root.dataset.scheme = mode === "system" ? (systemPreference.matches ? "dark" : "light") : mode;
    themeButtons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.themeChoice === mode)));
    if (persist) {
      try { localStorage.setItem("polar-atlas-theme", mode); } catch (_) {}
    }
  }

  function setLanguage(language, {persist = true} = {}) {
    if (!["en", "zh-CN"].includes(language)) return;
    root.dataset.language = language;
    root.lang = language;
    if (persist) {
      try { localStorage.setItem("polar-atlas-language", language); } catch (_) {}
      const url = new URL(location.href);
      if (url.searchParams.has("lang")) {
        url.searchParams.set("lang", language);
        history.replaceState(null, "", url);
      }
    }
    applyStaticTranslations();
    populateControls();
    render();
    if (state.commandOpen) renderCommand();
  }

  const allProfileConcepts = source => uniq([
    ...(source.study_profile.habitats || []),
    ...(source.study_profile.methods || []),
    ...(source.study_profile.focal_taxa || []),
    ...(source.study_profile.focal_processes || []),
    ...(source.study_profile.environmental_drivers || []),
  ]);

  const sourceConcepts = source => uniq([
    ...allProfileConcepts(source),
    ...(claimsBySource.get(source.id) || []).flatMap(claim => [claim.subject, claim.object]).filter(id => !id.startsWith("src:")),
  ]);

  const sourceText = source => {
    const translation = translatedSource(source);
    const translatedClaims = (claimsBySource.get(source.id) || []).map(translatedClaim);
    return [
      source.title, source.doi, source.citation_key, source.study_type,
      source.bibliographic.authors.join(" "), source.study_profile.spatial_scope,
      source.study_profile.temporal_scope, source.study_profile.sample_design,
      ...(source.key_findings || []), ...(source.limitations || []), ...(source.cite_for || []),
      ...(source.do_not_overcite || []), ...(source.study_profile.measured_or_derived || []),
      ...sourceConcepts(source).flatMap(id => [byId.get(id)?.label || id, i18n.concepts?.[id]?.label || ""]),
      JSON.stringify(translation), JSON.stringify(translatedClaims),
    ].join(" ").toLowerCase();
  };

  function replaceOptions(select, options) {
    const current = select.value;
    select.replaceChildren(...options.map(([label, value]) => new Option(label, value)));
    if (options.some(([, value]) => String(value) === current)) select.value = current;
  }

  function populateControls() {
    replaceOptions(els.domainFilter, [
      [t("all_areas"), ""],
      ...data.domains.map(domain => [mappedLabel("domains", domain), domain]),
    ]);
    replaceOptions(els.poleFilter, [
      [t("all_poles"), ""],
      ...["Arctic", "Antarctic", "Bipolar", "Global"].map(pole => [mappedLabel("poles", pole), pole]),
    ]);
    replaceOptions(els.yearFilter, [
      [t("all_years"), ""],
      ...uniq(data.sources.map(source => source.year)).sort((a, b) => b - a).map(year => [year, year]),
    ]);
    replaceOptions(els.evidenceFilter, [
      [t("all_evidence"), ""],
      ...["reported", "inferred", "modeled", "synthesized"].map(value => [mappedLabel("evidence", value), value]),
    ]);
  }

  function filteredSources() {
    const query = els.searchInput.value.trim().toLowerCase();
    const domain = els.domainFilter.value;
    const pole = els.poleFilter.value;
    const year = els.yearFilter.value;
    const evidence = els.evidenceFilter.value;
    return data.sources.filter(source => {
      if (query && !sourceText(source).includes(query)) return false;
      if (domain && !source.domains.includes(domain)) return false;
      if (pole && !source.poles.includes(pole)) return false;
      if (year && String(source.year) !== year) return false;
      if (evidence && !(claimsBySource.get(source.id) || []).some(claim => claim.evidence_type === evidence)) return false;
      if (state.conceptFocus && !sourceConcepts(source).includes(state.conceptFocus)) return false;
      return true;
    }).sort((a, b) => b.year - a.year || sourceTitle(a).localeCompare(sourceTitle(b), locale()));
  }

  function renderStats(sources) {
    const sourceIds = new Set(sources.map(source => source.id));
    els.statSources.textContent = sources.length;
    els.statClaims.textContent = data.claims.filter(claim => sourceIds.has(claim.source_id)).length;
    els.statRecent.textContent = sources.filter(source => source.year >= 2024).length;
    els.statCandidates.textContent = `${data.candidate_summary.promotion_counts?.promoted_to_curated_graph || 0} / ${data.candidate_summary.review_counts?.include || 0}`;
  }

  function domainClass(domain) {
    if (domain.includes("virus")) return "virus";
    if (domain.includes("prokaryote")) return "prok";
    if (domain.includes("eukaryote")) return "euk";
    return "earth";
  }

  function renderSourceList(sources) {
    els.sourceCount.textContent = t("matching_papers", {count: sources.length});
    if (!sources.length) {
      els.sourceList.innerHTML = `<div class="empty">${escapeHTML(t("no_sources"))}</div>`;
      return;
    }
    els.sourceList.innerHTML = sources.map((source, index) => {
      const claim = (claimsBySource.get(source.id) || [])[0];
      const original = isChinese() && sourceTitle(source) !== source.title
        ? `<span class="source-original-title" lang="en">${escapeHTML(source.title)}</span>` : "";
      return `<button type="button" class="source-card" style="--source-index:${index}" data-source-id="${escapeHTML(source.id)}" aria-current="${state.selectedSource === source.id}">
        <span class="source-title">${escapeHTML(sourceTitle(source))}</span>${original}
        <span class="source-meta">${escapeHTML(source.bibliographic.author_short || source.citation_key)} · ${source.year}</span>
        <span class="tags">${source.domains.slice(0, 2).map(domain => `<span class="tag ${domainClass(domain)}">${escapeHTML(mappedLabel("domains", domain))}</span>`).join("")}${claim ? `<span class="tag evidence">${escapeHTML(mappedLabel("evidence", claim.evidence_type))}</span>` : ""}</span>
      </button>`;
    }).join("");
    els.sourceList.querySelectorAll("[data-source-id]").forEach(button => button.addEventListener("click", () => {
      state.selectedSource = button.dataset.sourceId;
      render();
      if (window.matchMedia("(max-width: 1260px)").matches) {
        document.querySelector(".detail").scrollIntoView({behavior: "smooth", block: "start"});
      }
    }));
  }

  function renderActiveFilters() {
    const filters = [];
    if (els.searchInput.value.trim()) filters.push({kind: "search", label: `“${els.searchInput.value.trim()}”`});
    if (els.domainFilter.value) filters.push({kind: "domain", label: mappedLabel("domains", els.domainFilter.value)});
    if (els.poleFilter.value) filters.push({kind: "pole", label: mappedLabel("poles", els.poleFilter.value)});
    if (els.yearFilter.value) filters.push({kind: "year", label: els.yearFilter.value});
    if (els.evidenceFilter.value) filters.push({kind: "evidence", label: mappedLabel("evidence", els.evidenceFilter.value)});
    if (state.conceptFocus) filters.push({kind: "concept", label: labelFor(state.conceptFocus)});
    els.activeFilterBar.hidden = filters.length === 0;
    els.activeFilterChips.innerHTML = filters.map(filter => `<button class="filter-chip" type="button" data-filter-kind="${filter.kind}" aria-label="${escapeHTML(t("remove_filter", {label: filter.label}))}">${escapeHTML(filter.label)}</button>`).join("");
    els.activeFilterChips.querySelectorAll("[data-filter-kind]").forEach(button => button.addEventListener("click", () => {
      const kind = button.dataset.filterKind;
      if (kind === "search") els.searchInput.value = "";
      if (kind === "domain") els.domainFilter.value = "";
      if (kind === "pole") els.poleFilter.value = "";
      if (kind === "year") els.yearFilter.value = "";
      if (kind === "evidence") els.evidenceFilter.value = "";
      if (kind === "concept") state.conceptFocus = null;
      state.selectedSource = null;
      render();
    }));
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  const svgEl = name => document.createElementNS(SVG_NS, name);
  function addSvg(parent, name, attrs = {}) {
    const element = svgEl(name);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    parent.appendChild(element);
    return element;
  }

  function wrapLabel(value, maxChars = 22, maxLines = 2) {
    const text = String(value);
    const characterMode = /[\u3400-\u9fff]/.test(text) && !/\s/.test(text);
    const units = characterMode ? [...text] : text.split(/\s+/);
    const joiner = characterMode ? "" : " ";
    const limit = characterMode ? Math.max(5, Math.floor(maxChars * .58)) : maxChars;
    const lines = [];
    let line = "";
    let consumed = 0;
    for (const unit of units) {
      const candidate = line ? `${line}${joiner}${unit}` : unit;
      if (!line || candidate.length <= limit) line = candidate;
      else {
        lines.push(line);
        line = unit;
        if (lines.length === maxLines - 1) break;
      }
      consumed += unit.length;
    }
    if (line && lines.length < maxLines) lines.push(line);
    if (consumed < units.reduce((sum, unit) => sum + unit.length, 0) && lines.length) {
      lines[lines.length - 1] = lines[lines.length - 1].replace(/[.…]*$/, "") + "…";
    }
    return lines;
  }

  function nodeWidth(label, min = 126, max = 220) {
    const visualLength = [...String(label)].reduce((sum, char) => sum + (/\p{Script=Han}/u.test(char) ? 11 : 6.4), 0);
    return Math.max(min, Math.min(max, visualLength + 30));
  }

  function drawNode(svg, node, x, y, options = {}) {
    const label = options.label || labelFor(node.id) || node.label;
    const width = options.width || nodeWidth(label, options.minWidth || 126, options.maxWidth || 220);
    const lines = wrapLabel(label, Math.max(14, Math.floor((width - 20) / 6.4)), options.maxLines || 2);
    const height = options.height || Math.max(42, 19 + lines.length * 15 + (options.count ? 11 : 0));
    const group = addSvg(svg, "g", {
      class: `graph-node ${options.kind || "facet"}`,
      transform: `translate(${x - width / 2} ${y - height / 2})`,
      role: "button", tabindex: "0", "aria-label": label,
    });
    addSvg(group, "rect", {width, height, rx: 8});
    const text = addSvg(group, "text", {x: width / 2, y: lines.length === 1 ? height / 2 + 4 : height / 2 - 3, "text-anchor": "middle"});
    lines.forEach((line, index) => {
      const span = addSvg(text, "tspan", {x: width / 2, dy: index === 0 ? 0 : 15});
      span.textContent = line;
    });
    if (options.count) {
      const count = addSvg(group, "text", {class: "node-count", x: width / 2, y: height - 7, "text-anchor": "middle"});
      count.textContent = t("source_count", {count: options.count});
    }
    const activate = () => options.onSelect?.(node);
    group.addEventListener("click", activate);
    group.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
    const title = addSvg(group, "title");
    title.textContent = options.title || label;
    return {group, width, height, x, y};
  }

  function curve(svg, start, end, className, weight = 1, titleText = "") {
    const path = addSvg(svg, "path", {
      class: `graph-edge ${className}`,
      d: `M ${start.x} ${start.y} C ${(start.x + end.x) / 2} ${start.y}, ${(start.x + end.x) / 2} ${end.y}, ${end.x} ${end.y}`,
      "stroke-width": Math.min(9, .8 + Math.log2(weight + 1) * 1.35),
    });
    if (titleText) {
      const title = addSvg(path, "title");
      title.textContent = titleText;
    }
    return path;
  }

  function renderOverview(sources) {
    const svg = els.graphSvg;
    svg.replaceChildren();
    els.graphTitle.textContent = t("graph_structure");
    els.graphSubtitle.textContent = t("graph_structure_subtitle");
    els.graphNote.textContent = t("graph_note_overview");
    const poleCounts = new Map();
    const domainCounts = new Map();
    const facetCounts = new Map();
    const poleDomain = new Map();
    const domainFacet = new Map();
    sources.forEach(source => {
      source.poles.forEach(pole => poleCounts.set(pole, (poleCounts.get(pole) || 0) + 1));
      source.domains.forEach(domain => domainCounts.set(domain, (domainCounts.get(domain) || 0) + 1));
      const facets = sourceConcepts(source).filter(id => !id.startsWith("pole:"));
      facets.forEach(id => facetCounts.set(id, (facetCounts.get(id) || 0) + 1));
      source.poles.forEach(pole => source.domains.forEach(domain => {
        const key = `${pole}\u0000${domain}`;
        poleDomain.set(key, (poleDomain.get(key) || 0) + 1);
      }));
      source.domains.forEach(domain => facets.forEach(id => {
        const key = `${domain}\u0000${id}`;
        domainFacet.set(key, (domainFacet.get(key) || 0) + 1);
      }));
    });
    const poles = [...poleCounts].sort((a, b) => b[1] - a[1]);
    const domains = [...domainCounts].sort((a, b) => b[1] - a[1]);
    const facets = [...facetCounts].sort((a, b) => b[1] - a[1] || labelFor(a[0]).localeCompare(labelFor(b[0]), locale())).slice(0, 14);
    const height = Math.max(600, 100 + Math.max(poles.length * 90, domains.length * 80, facets.length * 43));
    svg.setAttribute("viewBox", `0 0 1000 ${height}`);
    if (!sources.length) {
      const text = addSvg(svg, "text", {x: 500, y: 280, "text-anchor": "middle", fill: "currentColor"});
      text.textContent = t("graph_no_matches");
      return;
    }
    [[100, t("layer_pole")], [450, t("layer_area")], [840, t("layer_facet")]].forEach(([x, label]) => {
      const text = addSvg(svg, "text", {class: "layer-label", x, y: 30, "text-anchor": "middle"});
      text.textContent = label;
    });
    const positions = {pole: new Map(), domain: new Map(), facet: new Map()};
    poles.forEach(([pole, count], index) => positions.pole.set(pole, {x: 100, y: 78 + index * ((height - 125) / Math.max(1, poles.length - 1 || 1)), count}));
    domains.forEach(([domain, count], index) => positions.domain.set(domain, {x: 450, y: 72 + index * ((height - 110) / Math.max(1, domains.length - 1 || 1)), count}));
    facets.forEach(([id, count], index) => positions.facet.set(id, {x: 840, y: 58 + index * ((height - 82) / Math.max(1, facets.length - 1 || 1)), count}));
    poleDomain.forEach((count, key) => {
      const [pole, domain] = key.split("\u0000");
      if (positions.pole.has(pole) && positions.domain.has(domain)) curve(svg, positions.pole.get(pole), positions.domain.get(domain), "pole-domain", count, t("matching_sources", {count}));
    });
    domainFacet.forEach((count, key) => {
      const [domain, id] = key.split("\u0000");
      if (positions.domain.has(domain) && positions.facet.has(id)) curve(svg, positions.domain.get(domain), positions.facet.get(id), "domain-facet", count, t("matching_sources", {count}));
    });
    poles.forEach(([pole, count]) => drawNode(svg, {id: pole}, positions.pole.get(pole).x, positions.pole.get(pole).y, {
      kind: "pole", count, label: mappedLabel("poles", pole),
      onSelect: () => { els.poleFilter.value = pole; state.selectedSource = null; render(); },
    }));
    domains.forEach(([domain, count]) => drawNode(svg, {id: domain}, positions.domain.get(domain).x, positions.domain.get(domain).y, {
      kind: "domain", count, label: mappedLabel("domains", domain), minWidth: 170, maxWidth: 230,
      onSelect: () => { els.domainFilter.value = domain; state.selectedSource = null; render(); },
    }));
    facets.forEach(([id, count]) => drawNode(svg, byId.get(id) || {id}, positions.facet.get(id).x, positions.facet.get(id).y, {
      count, label: labelFor(id), minWidth: 150, maxWidth: 245,
      onSelect: () => { state.conceptFocus = id; state.selectedSource = null; render(); },
    }));
  }

  function sourceFacetGroups(source) {
    return [
      ["pole", source.poles.map(value => ({id: ({Arctic: "pole:arctic", Antarctic: "pole:antarctic", Bipolar: "pole:bipolar"}[value] || value), value, label: mappedLabel("poles", value), kind: "pole"}))],
      ["area", source.domains.map(value => ({id: `domain:${value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`, value, label: mappedLabel("domains", value), kind: "domain"}))],
      ["habitat", (source.study_profile.habitats || []).map(id => ({...(byId.get(id) || {id}), label: labelFor(id), kind: "concept"}))],
      ["method", (source.study_profile.methods || []).map(id => ({...(byId.get(id) || {id}), label: labelFor(id), kind: "concept"}))],
      ["taxon", (source.study_profile.focal_taxa || []).map(id => ({...(byId.get(id) || {id}), label: labelFor(id), kind: "concept"}))],
      ["process", (source.study_profile.focal_processes || []).map(id => ({...(byId.get(id) || {id}), label: labelFor(id), kind: "concept"}))],
      ["driver", (source.study_profile.environmental_drivers || []).map(id => ({...(byId.get(id) || {id}), label: labelFor(id), kind: "concept"}))],
    ].map(([name, items]) => [name, items.filter(Boolean)]).filter(([, items]) => items.length);
  }

  function renderSourceGraph(source) {
    const svg = els.graphSvg;
    svg.replaceChildren();
    const groups = sourceFacetGroups(source);
    const leftGroups = groups.filter(([name]) => ["pole", "area", "habitat", "method"].includes(name));
    const rightGroups = groups.filter(([name]) => !["pole", "area", "habitat", "method"].includes(name));
    const leftItems = leftGroups.flatMap(([group, items]) => items.map(item => ({...item, group})));
    const rightItems = rightGroups.flatMap(([group, items]) => items.map(item => ({...item, group})));
    const claims = claimsBySource.get(source.id) || [];
    const height = Math.max(610, 120 + Math.max(leftItems.length, rightItems.length) * 58 + claims.length * 125);
    svg.setAttribute("viewBox", `0 0 1000 ${height}`);
    const sourcePosition = {x: 500, y: Math.min(270, height * .36)};
    const leftPositions = leftItems.map((item, index) => ({x: 165, y: 65 + index * ((Math.min(height - 220, 520) - 55) / Math.max(1, leftItems.length - 1 || 1))}));
    const rightPositions = rightItems.map((item, index) => ({x: 835, y: 65 + index * ((Math.min(height - 220, 520) - 55) / Math.max(1, rightItems.length - 1 || 1))}));
    leftPositions.forEach(position => curve(svg, {x: position.x + 90, y: position.y}, {x: sourcePosition.x - 135, y: sourcePosition.y}, "profile", 1));
    rightPositions.forEach(position => curve(svg, {x: sourcePosition.x + 135, y: sourcePosition.y}, {x: position.x - 90, y: position.y}, "profile", 1));
    drawNode(svg, {id: source.id}, sourcePosition.x, sourcePosition.y, {
      kind: "source", width: 280, height: 88, maxLines: 3, label: sourceTitle(source), title: `${source.title} (${source.year})`,
    });
    const facetSelect = item => {
      if (item.kind === "domain") {
        els.domainFilter.value = item.value;
        state.selectedSource = null;
      } else if (item.kind === "pole") {
        els.poleFilter.value = item.value;
        state.selectedSource = null;
      } else {
        state.conceptFocus = item.id;
        state.selectedSource = null;
      }
      render();
    };
    leftItems.forEach((item, index) => drawNode(svg, item, leftPositions[index].x, leftPositions[index].y, {label: item.label, minWidth: 145, maxWidth: 210, onSelect: facetSelect, title: item.label}));
    rightItems.forEach((item, index) => drawNode(svg, item, rightPositions[index].x, rightPositions[index].y, {label: item.label, minWidth: 145, maxWidth: 210, onSelect: facetSelect, title: item.label}));
    let y = Math.max(565, sourcePosition.y + 240);
    claims.forEach((claim, index) => {
      const view = claimView(claim);
      if (index) addSvg(svg, "line", {x1: 120, x2: 880, y1: y - 30, y2: y - 30, stroke: "var(--border)"});
      const start = {x: 245, y};
      const end = {x: 755, y};
      const line = addSvg(svg, "line", {class: "graph-edge claim", x1: start.x + 110, y1: y, x2: end.x - 110, y2: y});
      const title = addSvg(line, "title");
      title.textContent = view.statement;
      addSvg(svg, "path", {d: `M ${end.x - 118} ${y - 5} L ${end.x - 108} ${y} L ${end.x - 118} ${y + 5}`, fill: "none", stroke: "var(--virus)", "stroke-width": 2});
      drawNode(svg, byId.get(claim.subject) || sourceById.get(claim.subject) || {id: claim.subject}, start.x, y, {
        kind: "claim-node", width: 220, maxLines: 2, label: labelFor(claim.subject),
        onSelect: item => { if (!item.id.startsWith("src:")) { state.conceptFocus = item.id; state.selectedSource = null; render(); } },
      });
      drawNode(svg, byId.get(claim.object) || {id: claim.object}, end.x, y, {
        kind: "claim-node", width: 220, maxLines: 2, label: labelFor(claim.object),
        onSelect: item => { state.conceptFocus = item.id; state.selectedSource = null; render(); },
      });
      const predicate = addSvg(svg, "text", {class: "edge-label", x: 500, y: y - 9, "text-anchor": "middle"});
      predicate.textContent = mappedLabel("predicates", claim.predicate);
      const evidence = addSvg(svg, "text", {class: "node-count", x: 500, y: y + 17, "text-anchor": "middle"});
      evidence.textContent = isChinese()
        ? `${mappedLabel("evidence", claim.evidence_type)} · ${t("confidence")}：${mappedLabel("confidence", claim.confidence)}`
        : `${mappedLabel("evidence", claim.evidence_type)} · ${mappedLabel("confidence", claim.confidence)} ${t("confidence")}`;
      y += 125;
    });
    els.graphTitle.textContent = t("source_graph");
    els.graphSubtitle.textContent = `${source.bibliographic.author_short || source.citation_key}, ${source.year}`;
    els.graphNote.textContent = t("source_graph_note");
  }

  function citationText(source) {
    const bibliography = source.bibliographic;
    const authors = bibliography.authors.length ? bibliography.authors.join(", ") : source.citation_key;
    return `${authors} (${source.year}). ${source.title}. ${bibliography.journal}${bibliography.volume ? ` ${bibliography.volume}` : ""}${bibliography.pages ? `, ${bibliography.pages}` : ""}. https://doi.org/${source.doi}`;
  }

  const list = items => `<ul>${(items || []).map(item => `<li>${escapeHTML(item)}</li>`).join("")}</ul>`;

  function renderDetail(source) {
    if (!source) {
      els.detailBody.innerHTML = `<h3>${escapeHTML(t("how_to_read"))}</h3><p class="overview-help">${escapeHTML(t("how_to_read_body"))}</p>
        <h3>${escapeHTML(t("evidence_classes"))}</h3><div class="legend">
          <div class="legend-row"><span class="dot reported"></span><strong>${escapeHTML(t("reported"))}</strong><span>${escapeHTML(t("reported_definition"))}</span></div>
          <div class="legend-row"><span class="dot inferred"></span><strong>${escapeHTML(t("inferred"))}</strong><span>${escapeHTML(t("inferred_definition"))}</span></div>
          <div class="legend-row"><span class="dot modeled"></span><strong>${escapeHTML(t("modeled"))}</strong><span>${escapeHTML(t("modeled_definition"))}</span></div>
          <div class="legend-row"><span class="dot synthesized"></span><strong>${escapeHTML(t("synthesized"))}</strong><span>${escapeHTML(t("synthesized_definition"))}</span></div>
        </div>
        <h3>${escapeHTML(t("citation_safety"))}</h3><p class="overview-help">${escapeHTML(t("citation_safety_body"))}</p>`;
      return;
    }
    const view = sourceView(source);
    const profile = view.profile;
    const claims = claimsBySource.get(source.id) || [];
    const originalTitle = isChinese() && view.title !== source.title
      ? `<p class="published-title" lang="en"><strong>${escapeHTML(t("published_title"))}:</strong> ${escapeHTML(source.title)}</p>` : "";
    const translationNote = isChinese() ? `<p class="translation-note">${escapeHTML(t("translation_note"))}</p>` : "";
    els.detailBody.innerHTML = `<h2 class="detail-title">${escapeHTML(view.title)}</h2>${originalTitle}
      <p class="citation" lang="en">${escapeHTML(citationText(source))}</p>${translationNote}
      <div class="tags">${source.domains.map(domain => `<span class="tag ${domainClass(domain)}">${escapeHTML(mappedLabel("domains", domain))}</span>`).join("")}${source.poles.map(pole => `<span class="tag">${escapeHTML(mappedLabel("poles", pole))}</span>`).join("")}</div>
      <div class="detail-actions"><a class="link-button" href="https://doi.org/${encodeURIComponent(source.doi)}" target="_blank" rel="noopener">${escapeHTML(t("open_doi"))}</a><button class="button" id="copyKey" type="button">${escapeHTML(t("copy_key"))}</button><button class="button" id="copyBib" type="button">${escapeHTML(t("copy_bibtex"))}</button></div>
      <h3>${escapeHTML(t("study_design"))}</h3><dl class="definition-list">
        <dt>${escapeHTML(t("type"))}</dt><dd>${escapeHTML(view.studyType)}</dd>
        <dt>${escapeHTML(t("space"))}</dt><dd>${escapeHTML(profile.spatial_scope)}</dd>
        <dt>${escapeHTML(t("time"))}</dt><dd>${escapeHTML(profile.temporal_scope)}</dd>
        <dt>${escapeHTML(t("sampling"))}</dt><dd>${escapeHTML(profile.sample_design)}</dd>
        <dt>${escapeHTML(t("methods"))}</dt><dd>${escapeHTML((source.study_profile.methods || []).map(labelFor).join(isChinese() ? "；" : "; "))}</dd>
        <dt>${escapeHTML(t("variables"))}</dt><dd>${escapeHTML((profile.measured_or_derived || []).join(isChinese() ? "；" : "; "))}</dd>
      </dl>
      <h3>${escapeHTML(t("key_findings"))}</h3>${list(view.findings)}
      <h3>${escapeHTML(t("cite_for"))}</h3>${list(view.citeFor)}
      <h3>${escapeHTML(t(claims.length === 1 ? "atomic_claim" : "atomic_claims"))}</h3>${claims.map(claim => {
        const claimText = claimView(claim);
        const confidenceText = isChinese()
          ? `${t("confidence")}：${mappedLabel("confidence", claim.confidence)}`
          : `${mappedLabel("confidence", claim.confidence)} ${t("confidence")}`;
        return `<div class="claim-box"><p>${escapeHTML(claimText.statement)}</p><div class="claim-meta"><strong>${escapeHTML(labelFor(claim.subject))}</strong> → ${escapeHTML(mappedLabel("predicates", claim.predicate))} → <strong>${escapeHTML(labelFor(claim.object))}</strong><br>${escapeHTML(mappedLabel("evidence", claim.evidence_type))} · ${escapeHTML(confidenceText)} · ${escapeHTML(claimText.locator)}<br>${escapeHTML(t("scope"))}: ${escapeHTML(claimText.scope)}<br>${escapeHTML(t("basis"))}: ${escapeHTML(claimText.evidence_basis)}<br>${escapeHTML(t("confidence_reason"))}: ${escapeHTML(claimText.confidence_note)}</div></div>`;
      }).join("")}
      <h3>${escapeHTML(t("limitations"))}</h3>${list(view.limitations)}
      <h3>${escapeHTML(t("do_not_overcite"))}</h3><div class="warning-box">${list(view.doNotOvercite)}</div>
      <h3>${escapeHTML(t("data_curation"))}</h3><dl class="definition-list">
        <dt>${escapeHTML(t("accessions"))}</dt><dd>${escapeHTML(source.data_accessions.length ? source.data_accessions.join("; ") : t("none_recorded"))}</dd>
        <dt>${escapeHTML(t("checked"))}</dt><dd>${escapeHTML(source.curation.last_verified)}</dd>
        <dt>${escapeHTML(t("basis"))}</dt><dd>${escapeHTML(view.curationBasis)}</dd>
        <dt>${escapeHTML(t("key"))}</dt><dd><code>${escapeHTML(source.citation_key)}</code></dd>
      </dl>`;
    document.getElementById("copyKey").addEventListener("click", () => copyText(source.citation_key, t("citation_key_copied")));
    document.getElementById("copyBib").addEventListener("click", () => copyText(source.bibtex, t("bibtex_copied")));
  }

  function copyText(value, message) {
    const fallback = () => {
      const area = document.createElement("textarea");
      area.value = value;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
      showToast(message);
    };
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(value).then(() => showToast(message)).catch(fallback);
    else fallback();
  }

  let toastTimer;
  function showToast(message) {
    clearTimeout(toastTimer);
    els.toast.textContent = message;
    els.toast.classList.add("visible");
    toastTimer = setTimeout(() => els.toast.classList.remove("visible"), 1700);
  }

  function renderConceptFocus() {
    if (state.conceptFocus) {
      els.conceptFocus.classList.add("visible");
      els.conceptFocus.querySelector("span").textContent = t("concept_filter", {label: labelFor(state.conceptFocus)});
    } else {
      els.conceptFocus.classList.remove("visible");
    }
  }

  function renderFreshness() {
    const latestVerified = data.sources.map(source => source.curation.last_verified).sort().at(-1);
    const built = new Intl.DateTimeFormat(locale(), {dateStyle: "medium", timeStyle: "short"}).format(new Date(data.generated_at));
    els.freshness.textContent = t("built_status", {built, verified: latestVerified});
  }

  function render() {
    const sources = filteredSources();
    if (state.selectedSource && !sources.some(source => source.id === state.selectedSource)) state.selectedSource = null;
    const selected = state.selectedSource ? sourceById.get(state.selectedSource) : null;
    renderStats(sources);
    renderSourceList(sources);
    renderActiveFilters();
    renderConceptFocus();
    renderDetail(selected);
    renderFreshness();
    if (selected) renderSourceGraph(selected);
    else renderOverview(sources);
  }

  function reset() {
    [els.searchInput, els.domainFilter, els.poleFilter, els.yearFilter, els.evidenceFilter].forEach(control => { control.value = ""; });
    state.selectedSource = null;
    state.conceptFocus = null;
    render();
  }

  function commandPreview(source) {
    if (!source) {
      els.commandPreview.innerHTML = `<div class="command-section-label">${escapeHTML(t("command_preview"))}</div><p>${escapeHTML(t("command_initial"))}</p>`;
      return;
    }
    const view = sourceView(source);
    const original = isChinese() && view.title !== source.title ? `<p lang="en">${escapeHTML(source.title)}</p>` : "";
    els.commandPreview.innerHTML = `<div class="command-section-label">${escapeHTML(t("command_preview"))}</div><h2>${escapeHTML(view.title)}</h2>${original}
      <p>${escapeHTML(source.bibliographic.author_short || source.citation_key)} · ${source.year} · DOI ${escapeHTML(source.doi)}</p>
      <div class="tags">${source.domains.map(domain => `<span class="tag ${domainClass(domain)}">${escapeHTML(mappedLabel("domains", domain))}</span>`).join("")}</div>
      ${view.findings[0] ? `<p><strong>${escapeHTML(t("key_findings"))}</strong><br>${escapeHTML(view.findings[0])}</p>` : ""}
      ${view.citeFor[0] ? `<p><strong>${escapeHTML(t("cite_for"))}</strong><br>${escapeHTML(view.citeFor[0])}</p>` : ""}`;
  }

  function setCommandIndex(index) {
    if (!state.commandMatches.length) {
      state.commandIndex = 0;
      commandPreview(null);
      return;
    }
    state.commandIndex = Math.max(0, Math.min(index, state.commandMatches.length - 1));
    els.commandResults.querySelectorAll(".command-result").forEach((button, buttonIndex) => {
      button.classList.toggle("active", buttonIndex === state.commandIndex);
      button.setAttribute("aria-selected", String(buttonIndex === state.commandIndex));
      if (buttonIndex === state.commandIndex) button.scrollIntoView({block: "nearest"});
    });
    commandPreview(state.commandMatches[state.commandIndex]);
  }

  function renderCommand() {
    const query = els.commandInput.value.trim().toLowerCase();
    const candidates = query ? data.sources.filter(source => sourceText(source).includes(query)) : filteredSources();
    state.commandMatches = candidates
      .sort((a, b) => b.year - a.year || sourceTitle(a).localeCompare(sourceTitle(b), locale()))
      .slice(0, 24);
    state.commandIndex = Math.min(state.commandIndex, Math.max(0, state.commandMatches.length - 1));
    if (!state.commandMatches.length) {
      els.commandResults.innerHTML = `<div class="command-empty">${escapeHTML(t("command_empty"))}</div>`;
      commandPreview(null);
      return;
    }
    els.commandResults.innerHTML = state.commandMatches.map((source, index) => `<button class="command-result${index === state.commandIndex ? " active" : ""}" type="button" data-command-index="${index}" aria-selected="${index === state.commandIndex}">
      <span class="command-result-title">${escapeHTML(sourceTitle(source))}</span>
      <span class="command-result-meta">${escapeHTML(source.bibliographic.author_short || source.citation_key)} · ${source.year} · ${escapeHTML(source.doi)}</span>
    </button>`).join("");
    els.commandResults.querySelectorAll("[data-command-index]").forEach(button => {
      button.addEventListener("mouseenter", () => setCommandIndex(Number(button.dataset.commandIndex)));
      button.addEventListener("focus", () => setCommandIndex(Number(button.dataset.commandIndex)));
      button.addEventListener("click", () => selectCommandSource(Number(button.dataset.commandIndex)));
    });
    commandPreview(state.commandMatches[state.commandIndex]);
  }

  function openCommand() {
    state.commandOpen = true;
    state.returnFocus = document.activeElement;
    state.commandIndex = 0;
    els.commandInput.value = els.searchInput.value;
    els.commandScrim.hidden = false;
    els.commandDialog.hidden = false;
    document.body.classList.add("dialog-open");
    renderCommand();
    requestAnimationFrame(() => {
      els.commandInput.focus();
      els.commandInput.select();
    });
  }

  function closeCommand() {
    if (!state.commandOpen) return;
    state.commandOpen = false;
    els.commandScrim.hidden = true;
    els.commandDialog.hidden = true;
    document.body.classList.remove("dialog-open");
    state.returnFocus?.focus?.();
  }

  function selectCommandSource(index) {
    const source = state.commandMatches[index];
    if (!source) return;
    [els.searchInput, els.domainFilter, els.poleFilter, els.yearFilter, els.evidenceFilter].forEach(control => { control.value = ""; });
    state.conceptFocus = null;
    state.selectedSource = source.id;
    closeCommand();
    render();
    document.querySelector(`[data-source-id="${CSS.escape(source.id)}"]`)?.scrollIntoView({block: "nearest"});
    if (window.matchMedia("(max-width: 1260px)").matches) document.querySelector(".detail").scrollIntoView({behavior: "smooth", block: "start"});
  }

  applyTheme(root.dataset.theme || "dark", {persist: false});
  applyStaticTranslations();
  populateControls();

  themeButtons.forEach(button => button.addEventListener("click", () => applyTheme(button.dataset.themeChoice)));
  languageButtons.forEach(button => button.addEventListener("click", () => setLanguage(button.dataset.languageChoice)));
  systemPreference.addEventListener?.("change", () => {
    if (root.dataset.theme === "system") applyTheme("system", {persist: false});
  });
  [els.searchInput, els.domainFilter, els.poleFilter, els.yearFilter, els.evidenceFilter].forEach(control => {
    control.addEventListener(control === els.searchInput ? "input" : "change", () => {
      state.selectedSource = null;
      render();
    });
  });
  els.resetFilters.addEventListener("click", reset);
  els.clearAllFilters.addEventListener("click", reset);
  els.overviewButton.addEventListener("click", () => { state.selectedSource = null; render(); });
  els.conceptFocus.querySelector("button").addEventListener("click", () => { state.conceptFocus = null; state.selectedSource = null; render(); });
  els.brandHome.addEventListener("click", event => {
    event.preventDefault();
    reset();
    window.scrollTo({top: 0, behavior: "smooth"});
  });
  els.openCommand.addEventListener("click", openCommand);
  els.commandScrim.addEventListener("click", closeCommand);
  els.commandInput.addEventListener("input", () => { state.commandIndex = 0; renderCommand(); });
  els.commandInput.addEventListener("keydown", event => {
    if (event.key === "ArrowDown") { event.preventDefault(); setCommandIndex(state.commandIndex + 1); }
    if (event.key === "ArrowUp") { event.preventDefault(); setCommandIndex(state.commandIndex - 1); }
    if (event.key === "Enter") { event.preventDefault(); selectCommandSource(state.commandIndex); }
  });
  document.addEventListener("keydown", event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (!state.commandOpen) openCommand();
    }
    if (event.key === "Escape" && state.commandOpen) {
      event.preventDefault();
      closeCommand();
    } else if (event.key === "Escape" && document.activeElement === els.searchInput && els.searchInput.value) {
      els.searchInput.value = "";
      state.selectedSource = null;
      render();
    }
  });

  const startupParameters = new URLSearchParams(location.search);
  const startupSource = startupParameters.get("source");
  if (startupSource && sourceById.has(startupSource)) state.selectedSource = startupSource;
  render();
  if (startupParameters.get("command") === "1") {
    openCommand();
    const startupQuery = startupParameters.get("q");
    if (startupQuery) {
      els.commandInput.value = startupQuery;
      renderCommand();
    }
  }
})();

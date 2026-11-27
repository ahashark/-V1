/**
 * 全站前端静态展示交互脚本 (GitHub Pages & Local Flask Compatible)
 * 基于构建时导出的 /static/data/catalog.json 在纯前端完成实时检索、香调过滤、排序与香氛叠穿品鉴，
 * 无需任何后端动态进程即可在 https://sxy.ink (GitHub Pages) 完整运行全部交互。
 */

document.addEventListener("DOMContentLoaded", () => {
  let catalogCache = null;

  const loadCatalog = async () => {
    if (catalogCache) return catalogCache;
    try {
      const res = await fetch("/static/data/catalog.json");
      if (res.ok) {
        catalogCache = await res.json();
        return catalogCache;
      }
    } catch (_err) {
      // 回退至 Flask 本地 API（开发模式下未生成 catalog.json 时兜底）
    }
    const res = await fetch("/api/search?q=");
    const data = await res.json();
    catalogCache = { products: data.results || [] };
    return catalogCache;
  };

  // 1. 顶部品牌导览公告栏轮播
  const announcements = window.SITE_ANNOUNCEMENTS || [];
  let currentAnnouncementIdx = 0;
  const announcementEl = document.getElementById("announcementText");

  const updateAnnouncement = (step) => {
    if (!announcements.length || !announcementEl) return;
    currentAnnouncementIdx =
      (currentAnnouncementIdx + step + announcements.length) % announcements.length;
    announcementEl.textContent = announcements[currentAnnouncementIdx];
  };

  document.getElementById("prevAnnouncement")?.addEventListener("click", () => updateAnnouncement(-1));
  document.getElementById("nextAnnouncement")?.addEventListener("click", () => updateAnnouncement(1));
  if (announcements.length > 1) {
    setInterval(() => updateAnnouncement(1), 6000);
  }

  // 2. 移动端侧滑导航抽屉与顶部实时搜索图鉴浮层控制（统一遮罩与滚动锁定）
  const backdrop = document.getElementById("globalBackdrop");
  const searchDrawer = document.getElementById("searchDrawer");
  const mobileNavDrawer = document.getElementById("mobileNavDrawer");
  const openMobileMenuBtn = document.getElementById("openMobileMenuBtn");
  const colognesAccordionBtn = document.getElementById("colognesAccordionBtn");
  const colognesSubmenu = document.getElementById("colognesSubmenu");

  const closeAllOverlays = () => {
    backdrop?.classList.remove("open");
    searchDrawer?.classList.remove("open");
    mobileNavDrawer?.classList.remove("open");
    mobileNavDrawer?.setAttribute("aria-hidden", "true");
    openMobileMenuBtn?.setAttribute("aria-expanded", "false");
    document.body.classList.remove("overlay-open");
  };

  const openMobileMenu = () => {
    searchDrawer?.classList.remove("open");
    backdrop?.classList.add("open");
    mobileNavDrawer?.classList.add("open");
    mobileNavDrawer?.setAttribute("aria-hidden", "false");
    openMobileMenuBtn?.setAttribute("aria-expanded", "true");
    document.body.classList.add("overlay-open");
  };

  backdrop?.addEventListener("click", closeAllOverlays);
  document.querySelectorAll("[data-close-overlay]").forEach((btn) => {
    btn.addEventListener("click", closeAllOverlays);
  });

  openMobileMenuBtn?.addEventListener("click", () => {
    if (mobileNavDrawer?.classList.contains("open")) {
      closeAllOverlays();
    } else {
      openMobileMenu();
    }
  });

  colognesAccordionBtn?.addEventListener("click", () => {
    if (!colognesSubmenu) return;
    const isOpen = colognesSubmenu.classList.toggle("open");
    colognesAccordionBtn.setAttribute("aria-expanded", String(isOpen));
    const icon = colognesAccordionBtn.querySelector(".accordion-icon");
    if (icon) icon.textContent = isOpen ? "−" : "+";
  });

  mobileNavDrawer?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeAllOverlays);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllOverlays();
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 960 && mobileNavDrawer?.classList.contains("open")) {
      closeAllOverlays();
    }
  });

  const matchProductQuery = (p, q) => {
    if (!q) return true;
    const kw = q.toLowerCase();
    return [
      p.name_en,
      p.name_zh,
      p.scent_family,
      p.scent_family_zh,
      p.top_note,
      p.heart_note,
      p.base_note,
      p.collection,
    ].some((field) => (field || "").toLowerCase().includes(kw));
  };

  const triggerLiveSearch = async (query) => {
    const searchResultsEl = document.getElementById("liveSearchResults");
    if (!searchResultsEl) return;
    const { products = [] } = await loadCatalog();
    const q = (query || "").trim();

    const results = q
      ? products.filter((p) => matchProductQuery(p, q))
      : products.filter((p) => p.is_bestseller);

    if (results.length === 0) {
      searchResultsEl.innerHTML = `<p style="grid-column:1/-1; color:var(--text-muted); text-align:center; padding:24px 0;">未找到与「${q}」相关的香氛作品，请尝试输入“英国梨”、“海盐”、“丝柏”或“蜡烛”。</p>`;
      return;
    }

    searchResultsEl.innerHTML = results
      .slice(0, 4)
      .map(
        (p) => `
      <a href="/product/${p.slug}/" class="product-card" style="text-align:center;">
        <div class="product-media" style="aspect-ratio:1/0.85;">
          <img src="${p.image_url}" alt="${p.name_zh}">
        </div>
        <div class="search-card-body">
          <div class="product-scent">${p.scent_family_zh}</div>
          <div class="serif-title search-card-title">${p.name_en}</div>
          <div class="search-card-meta">${p.name_zh} · ${p.default_size}</div>
        </div>
      </a>
    `
      )
      .join("");
  };

  const openSearchOverlay = () => {
    mobileNavDrawer?.classList.remove("open");
    mobileNavDrawer?.setAttribute("aria-hidden", "true");
    openMobileMenuBtn?.setAttribute("aria-expanded", "false");
    backdrop?.classList.add("open");
    searchDrawer?.classList.add("open");
    document.body.classList.add("overlay-open");
    const input = document.getElementById("liveSearchInput");
    input?.focus();
    triggerLiveSearch(input?.value || "");
  };

  ["openSearchBtn", "openMobileSearchBtn", "mobileDrawerSearchBtn"].forEach((id) => {
    document.getElementById(id)?.addEventListener("click", openSearchOverlay);
  });

  let searchDebounce = null;
  document.getElementById("liveSearchInput")?.addEventListener("input", (e) => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => triggerLiveSearch(e.target.value), 150);
  });

  // 3. 首页香氛叠穿混搭品鉴切换（纯前端计算，兼容静态托管）
  const pairingBtn = document.getElementById("generatePairingBtn");
  if (pairingBtn) {
    pairingBtn.addEventListener("click", async () => {
      const baseSlug = document.getElementById("baseScentSelect")?.value;
      const layerSlug = document.getElementById("layerScentSelect")?.value;
      const { products = [] } = await loadCatalog();

      const baseProd = products.find((p) => p.slug === baseSlug);
      const layerProd = products.find((p) => p.slug === layerSlug);
      if (!baseProd || !layerProd) return;

      let harmonyTitle = "";
      let harmonyDesc = "";
      if (baseSlug === layerSlug) {
        harmonyTitle = `纯粹双重浓韵 · Pure ${baseProd.scent_family}`;
        harmonyDesc = `同款叠喷「${baseProd.name_zh}」可强化${baseProd.top_note}的明快开篇，并令尾调${baseProd.base_note}在肌肤上更加深邃持久。`;
      } else {
        harmonyTitle = `${baseProd.scent_family_zh} × ${layerProd.scent_family_zh} 专属定制香印`;
        harmonyDesc = `先以「${baseProd.name_zh}」的${baseProd.base_note}铺垫温润底色，再叠穿「${layerProd.name_zh}」的${layerProd.top_note}与${layerProd.heart_note}，交织出冷暖平衡、独树一帜的英伦高定层次。`;
      }

      document.getElementById("pairingTitle").textContent = harmonyTitle;
      document.getElementById("pairingDesc").textContent = harmonyDesc;
      document.getElementById("pairTopNote").textContent = `${baseProd.top_note} · ${layerProd.top_note}`;
      document.getElementById("pairHeartNote").textContent = `${baseProd.heart_note} · ${layerProd.heart_note}`;
      document.getElementById("pairBaseNote").textContent = `${baseProd.base_note} · ${layerProd.base_note}`;

      const baseLink = document.getElementById("baseProductLink");
      const layerLink = document.getElementById("layerProductLink");
      if (baseLink) baseLink.href = `/product/${baseProd.slug}/`;
      if (layerLink) layerLink.href = `/product/${layerProd.slug}/`;

      document.getElementById("pairingResultPanel")?.classList.add("visible");
    });
  }

  // 4. 分类页与全系图鉴页：兼容 GitHub Pages 静态 URL 参数筛选 (?scent=Woody&q=梨&sort=name_asc)
  const toolbar = document.getElementById("catalogToolbar");
  const gridWrap = document.getElementById("catalogGridWrap");
  if (toolbar && gridWrap) {
    const categorySlug = toolbar.dataset.categorySlug || "all";
    const baseUrl = toolbar.dataset.baseUrl || "/shop/";
    const sortSelect = document.getElementById("sortSelect");

    const applyStaticFilter = async () => {
      const params = new URLSearchParams(window.location.search);
      const scent = (params.get("scent") || "").trim();
      const sort = (params.get("sort") || "featured").trim();
      const q = (params.get("q") || "").trim();

      // 同步按钮与下拉选中状态，并在移动端横向筛选栏中自动将选中项居中
      toolbar.querySelectorAll(".filter-pill").forEach((pill) => {
        const isActive = (pill.dataset.scent || "") === scent;
        pill.classList.toggle("active", isActive);
        if (isActive && scent) {
          pill.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
        }
      });
      if (sortSelect) sortSelect.value = sort;

      if (!scent && sort === "featured" && !q) {
        return; // 默认状态已由静态 HTML 预渲染，无需重绘
      }

      const { products = [] } = await loadCatalog();
      let filtered = products.filter((p) => {
        if (categorySlug !== "all" && p.category_slug !== categorySlug) return false;
        if (scent && p.scent_family !== scent) return false;
        if (q && !matchProductQuery(p, q)) return false;
        return true;
      });

      if (sort === "name_asc") {
        filtered.sort((a, b) => a.name_en.localeCompare(b.name_en));
      } else if (sort === "newest") {
        filtered.sort((a, b) => b.id - a.id);
      } else {
        filtered.sort((a, b) => b.is_bestseller - a.is_bestseller || a.id - b.id);
      }

      const hintEl = document.getElementById("searchKeywordHint");
      if (hintEl) {
        if (q) {
          hintEl.style.display = "block";
          document.getElementById("searchKeywordText").textContent = q;
          document.getElementById("searchCountText").textContent = String(filtered.length);
        } else {
          hintEl.style.display = "none";
        }
      }

      if (filtered.length === 0) {
        gridWrap.innerHTML = `
          <div style="text-align:center; padding:64px 20px;">
            <h3 class="serif-title" style="font-size:1.55rem; margin-bottom:10px;">该筛选条件下暂无收录作品</h3>
            <p style="color:var(--text-muted); margin-bottom:24px;">您可以重置筛选条件，或返回全系图鉴浏览更多灵感。</p>
            <a href="${baseUrl}" class="btn btn-primary">显示全部作品</a>
          </div>
        `;
        return;
      }

      gridWrap.innerHTML = `
        <div class="product-grid" id="catalogGrid">
          ${filtered
            .map(
              (p) => `
            <article class="product-card">
              <a href="/product/${p.slug}/" class="product-media">
                ${p.badge ? `<span class="product-badge">${p.badge}</span>` : ""}
                <img src="${p.image_url}" alt="${p.name_zh}">
              </a>
              <div class="product-body">
                <div class="product-scent">${p.scent_family_zh} · ${p.collection}</div>
                <a href="/product/${p.slug}/" class="product-name-en">${p.name_en}</a>
                <div class="product-name-zh">${p.name_zh}</div>
                <div class="product-meta">
                  <span>规格：${(p.variants || []).map((v) => v.size).join(" / ")}</span>
                </div>
                <a href="/product/${p.slug}/" class="btn btn-outline btn-block">探索作品详情 · Discover</a>
              </div>
            </article>
          `
            )
            .join("")}
        </div>
      `;
    };

    sortSelect?.addEventListener("change", () => {
      const params = new URLSearchParams(window.location.search);
      params.set("sort", sortSelect.value);
      window.history.replaceState({}, "", `${baseUrl}?${params.toString()}`);
      applyStaticFilter();
    });

    toolbar.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", (e) => {
        e.preventDefault();
        const params = new URLSearchParams(window.location.search);
        const scentVal = pill.dataset.scent || "";
        if (scentVal) params.set("scent", scentVal);
        else params.delete("scent");
        const qs = params.toString();
        window.history.replaceState({}, "", qs ? `${baseUrl}?${qs}` : baseUrl);
        applyStaticFilter();
      });
    });

    applyStaticFilter();
  }
});

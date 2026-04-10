/**
 * 根据 body[data-page] 高亮顶部导航当前页
 */
(function () {
  var THEME_KEY = "ui_theme";
  var THEMES = ["default", "cards", "bili"];

  function applyTheme(theme) {
    var t = THEMES.indexOf(theme) >= 0 ? theme : "default";
    document.body.classList.remove("theme-default", "theme-cards", "theme-bili");
    document.body.classList.add("theme-" + t);
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch (_) {}
    return t;
  }

  function loadTheme() {
    var t = "default";
    try {
      t = localStorage.getItem(THEME_KEY) || "default";
    } catch (_) {}
    return applyTheme(t);
  }

  function createThemeSwitcher(currentTheme) {
    var wrap = document.createElement("div");
    wrap.className = "theme-switcher";
    wrap.innerHTML =
      "<button type='button' class='theme-switcher__toggle'>风格装扮</button>" +
      "<div class='theme-switcher__panel' role='menu' aria-hidden='true'>" +
      "<button type='button' class='theme-switcher__item' data-theme='default'><span class='theme-icon'>✨</span><span>默认风格</span></button>" +
      "<button type='button' class='theme-switcher__item' data-theme='cards'><span class='theme-icon'>🧩</span><span>卡片风格</span></button>" +
      "<button type='button' class='theme-switcher__item' data-theme='bili'><span class='theme-icon'>📺</span><span>哔哩风格</span></button>" +
      "</div>";
    document.body.appendChild(wrap);

    function syncActive(theme) {
      wrap.querySelectorAll(".theme-switcher__item").forEach(function (el) {
        el.classList.toggle("active", el.getAttribute("data-theme") === theme);
      });
    }

    var toggle = wrap.querySelector(".theme-switcher__toggle");
    var panel = wrap.querySelector(".theme-switcher__panel");
    toggle.addEventListener("click", function () {
      var open = wrap.classList.toggle("open");
      panel.setAttribute("aria-hidden", open ? "false" : "true");
    });
    wrap.querySelectorAll(".theme-switcher__item").forEach(function (el) {
      el.addEventListener("click", function () {
        var theme = applyTheme(el.getAttribute("data-theme"));
        syncActive(theme);
        wrap.classList.remove("open");
        panel.setAttribute("aria-hidden", "true");
      });
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) {
        wrap.classList.remove("open");
        panel.setAttribute("aria-hidden", "true");
      }
    });

    syncActive(currentTheme);
  }

  var currentTheme = loadTheme();
  createThemeSwitcher(currentTheme);

  function bindTiltMotion(el, options) {
    var opt = options || {};
    var maxRx = opt.maxRx || 3;
    var maxRy = opt.maxRy || 5;
    var scale = opt.scale || 1;
    var shortWidth = opt.shortWidth || 0;
    var shortBoost = opt.shortBoost || 1;
    var shortScale = opt.shortScale || scale;
    var rafId = 0;
    var lastEvent = null;

    function update() {
      rafId = 0;
      if (!lastEvent) return;
      var rect = el.getBoundingClientRect();
      var x = lastEvent.clientX - rect.left;
      var y = lastEvent.clientY - rect.top;
      var cx = rect.width / 2;
      var cy = rect.height / 2;
      var boost = shortWidth && rect.width <= shortWidth ? shortBoost : 1;
      var finalScale = shortWidth && rect.width <= shortWidth ? shortScale : scale;
      var rx = ((cy - y) / cy) * (maxRx * boost);
      var ry = ((x - cx) / cx) * (maxRy * boost);
      el.style.setProperty("--rx", rx.toFixed(2) + "deg");
      el.style.setProperty("--ry", ry.toFixed(2) + "deg");
      el.style.setProperty("--mx", x.toFixed(1) + "px");
      el.style.setProperty("--my", y.toFixed(1) + "px");
      el.style.setProperty("--brx", rx.toFixed(2) + "deg");
      el.style.setProperty("--bry", ry.toFixed(2) + "deg");
      el.style.setProperty("--bscale", String(finalScale));
    }

    el.addEventListener("mousemove", function (e) {
      lastEvent = e;
      if (!rafId) rafId = requestAnimationFrame(update);
    });
    el.addEventListener("mouseleave", function () {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
      lastEvent = null;
      el.style.setProperty("--rx", "0deg");
      el.style.setProperty("--ry", "0deg");
      el.style.setProperty("--mx", "50%");
      el.style.setProperty("--my", "50%");
      el.style.setProperty("--brx", "0deg");
      el.style.setProperty("--bry", "0deg");
      el.style.setProperty("--bscale", "1");
    });
  }

  // 快捷操作卡片：轻微 3D 跟随鼠标
  document.querySelectorAll(".action-tile").forEach(function (card) {
    if (!card.querySelector(".tile-glow")) {
      var glow = document.createElement("span");
      glow.className = "tile-glow";
      card.appendChild(glow);
    }
    bindTiltMotion(card, { maxRx: 6.5, maxRy: 9, scale: 1.015 });
  });

  // 全局按钮：轻微 3D 跟随鼠标
  document.querySelectorAll("button, .btn").forEach(function (btn) {
    if (btn.dataset.fxBind === "1") return;
    btn.dataset.fxBind = "1";
    bindTiltMotion(btn, {
      maxRx: 3.2,
      maxRy: 5.2,
      scale: 1.01,
      shortWidth: 120,
      shortBoost: 1.85,
      shortScale: 1.035,
    });
  });

  var page = document.body.getAttribute("data-page");
  var navIcons = {
    index: "🏠",
    devices: "🧩",
    monitor: "📈",
    control: "🎛️",
    ai: "🤖",
    ble: "📶",
    profile: "👤",
  };

  document.querySelectorAll(".topbar [data-nav]").forEach(function (el) {
    var navKey = el.getAttribute("data-nav");
    var icon = navIcons[navKey];
    if (icon && !el.querySelector(".nav-icon")) {
      var iconEl = document.createElement("span");
      iconEl.className = "nav-icon";
      iconEl.textContent = icon;
      el.insertBefore(iconEl, el.firstChild);
    }
  });

  if (!page) return;
  document.querySelectorAll(".topbar [data-nav]").forEach(function (el) {
    if (el.getAttribute("data-nav") === page) {
      el.classList.add("active");
    }
  });
})();

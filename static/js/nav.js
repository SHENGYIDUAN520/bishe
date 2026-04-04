/**
 * 根据 body[data-page] 高亮顶部导航当前页
 */
(function () {
  var page = document.body.getAttribute("data-page");
  if (!page) return;
  document.querySelectorAll(".topbar [data-nav]").forEach(function (el) {
    if (el.getAttribute("data-nav") === page) {
      el.classList.add("active");
    }
  });
})();

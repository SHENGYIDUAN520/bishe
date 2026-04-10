function showToast(message, type, duration) {
  var msg = String(message || "");
  var kind = type || "info";
  var ttl = duration || 2600;
  var root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    root.className = "toast-container";
    document.body.appendChild(root);
  }
  var toast = document.createElement("div");
  toast.className = "toast " + kind;
  toast.textContent = msg;
  root.appendChild(toast);
  setTimeout(function () {
    toast.remove();
    if (!root.children.length) root.remove();
  }, ttl);
}

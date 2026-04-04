/**
 * 统一封装浏览器端 fetch：自动携带 Cookie，解析 {code,msg,data}
 * 与《开发文档.md》第四章约定一致
 */
async function apiFetch(url, options = {}) {
  const opts = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  };
  const res = await fetch(url, opts);
  let body;
  try {
    body = await res.json();
  } catch (e) {
    throw new Error("服务器返回非 JSON，请检查接口或网络");
  }
  if (body.code !== 0) {
    const err = new Error(body.msg || "请求失败");
    err.code = body.code;
    err.data = body.data;
    throw err;
  }
  return body.data;
}

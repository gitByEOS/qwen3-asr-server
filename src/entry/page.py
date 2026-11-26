"""转写页。内嵌 HTML，无独立前端工程。"""

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>离线转写</title>
  <style>
    :root { color-scheme: dark; --bg:#151515; --text:#f4f4f5; --muted:#9a9a9f; --panel:#2b2b2b; --border:#3a3a3c; --primary:#496dff; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); }
    .app { max-width: 720px; margin: 0 auto; padding: 24px 18px 96px; }
    h1 { margin: 0; font-size: 18px; }
    .subtitle { margin-top: 4px; color: var(--muted); font-size: 13px; }
    form { margin-top: 24px; padding: 16px; background: var(--panel); border: 1px solid var(--border); border-radius: 12px; }
    label { display: flex; align-items: center; gap: 8px; margin: 12px 0; }
    button { border: 0; border-radius: 999px; padding: 8px 22px; background: var(--primary); color: #fff; cursor: pointer; }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    #result, #status, #enhance-state { white-space: pre-wrap; margin-top: 16px; line-height: 1.6; }
    #status { color: var(--muted); }
  </style>
</head>
<body>
  <div class="app">
    <h1>离线转写</h1>
    <div class="subtitle">上传音视频，可选人声增强。只出文本。</div>
    <form id="form">
      <input id="file" type="file" accept="audio/*,video/*" required />
      <label><input id="enhance" type="checkbox" checked /> 人声增强</label>
      <button id="submit" type="submit">转写</button>
    </form>
    <div id="status"></div>
    <div id="enhance-state"></div>
    <div id="result"></div>
  </div>
  <script>
    const form = document.getElementById("form");
    const fileInput = document.getElementById("file");
    const enhanceBox = document.getElementById("enhance");
    const submit = document.getElementById("submit");
    const status = document.getElementById("status");
    const enhanceState = document.getElementById("enhance-state");
    const result = document.getElementById("result");
    const apiBasePath = window.location.pathname.replace(/\/$/, "");
    const transcribePath = apiBasePath === "" ? "/api/transcribe" : `${apiBasePath}/api/transcribe`;
    let busy = false;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy) return;
      const file = fileInput.files[0];
      if (!file) return;
      busy = true;
      submit.disabled = true;
      status.textContent = "转写中";
      result.textContent = "";
      enhanceState.textContent = "";
      const enhance = enhanceBox.checked ? "on" : "off";
      const body = new FormData();
      body.append("file", file);
      body.append("enhance", enhance);
      try {
        const response = await fetch(transcribePath, { method: "POST", body });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          result.textContent = data.error || "转写失败";
          return;
        }
        result.textContent = data.text || "";
        enhanceState.textContent = data.enhance || "";
      } catch (error) {
        result.textContent = error.message;
      } finally {
        busy = false;
        submit.disabled = false;
        status.textContent = "";
      }
    });
  </script>
</body>
</html>
"""

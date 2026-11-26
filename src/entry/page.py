"""转写页。内嵌 HTML，支持拖入，缺包仍可打开。"""

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>离线转写</title>
  <style>
    :root { color-scheme: dark; --bg:#0d1117; --text:#e6edf3; --muted:#8b949e; --panel:#161b22; --border:#2a3140; --primary:#4e7af3; --warn:#f59e0b; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
    .app { max-width: 720px; margin: 0 auto; padding: 24px 18px 96px; }
    h1 { margin: 0; font-size: 22px; }
    .subtitle { margin-top: 4px; color: var(--muted); font-size: 13px; }
    .warning-bar { display: none; margin: 16px 0 0; padding: 11px 14px; border: 1px solid rgba(245, 158, 11, .18); border-radius: 9px; background: rgba(245, 158, 11, .045); color: #c8bd99; font-size: 13px; }
    .warning-bar.is-on { display: block; }
    form { margin-top: 24px; }
    .drop-zone { position: relative; display: flex; min-height: 180px; flex-direction: column; align-items: center; justify-content: center; padding: 28px; border: 1.5px dashed var(--border); border-radius: 14px; background: rgba(22, 27, 34, .72); cursor: pointer; text-align: center; }
    .drop-zone::before { display: grid; width: 44px; height: 44px; place-items: center; margin-bottom: 12px; border-radius: 14px; background: rgba(78, 122, 243, .16); color: #8eacff; content: "↑"; font-size: 25px; font-weight: 750; }
    .drop-zone:hover, .drop-zone.drag-over, .drop-zone:focus-visible { border-color: var(--primary); background: rgba(45, 212, 191, .08); }
    .drop-zone strong { font-size: 17px; }
    .drop-zone span { margin-top: 5px; color: var(--muted); font-size: 13px; }
    .drop-zone input[type="file"] { position: absolute; inset: 0; width: 100%; height: 100%; cursor: pointer; opacity: 0; }
    .file-name { margin-top: 10px; color: var(--muted); font-size: 13px; }
    .row { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
    button { border: 0; border-radius: 999px; padding: 8px 22px; background: var(--primary); color: #fff; cursor: pointer; }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    #result, #status, #enhance-state { white-space: pre-wrap; margin-top: 16px; line-height: 1.6; }
    #status { color: var(--muted); }
  </style>
</head>
<body>
  <div class="app">
    <h1>离线转写</h1>
    <div class="subtitle">拖入或选择音视频。缺包时页面仍可用，转写会说明缺什么。</div>
    <div id="warning" class="warning-bar"></div>
    <form id="form">
      <div id="drop-zone" class="drop-zone" role="button" tabindex="0" aria-label="拖拽音视频到这里或点击选择">
        <strong>选择或拖拽音视频</strong>
        <span>支持 wav；有 ffmpeg 时也可 mp3 / mp4 / m4a</span>
        <input id="file" type="file" accept="audio/*,video/*" />
      </div>
      <div id="file-name" class="file-name"></div>
      <div class="row">
        <label><input id="enhance" type="checkbox" checked /> 人声增强</label>
        <button id="submit" type="submit">转写</button>
      </div>
    </form>
    <div id="status"></div>
    <div id="enhance-state"></div>
    <div id="result"></div>
  </div>
  <script>
    const form = document.getElementById("form");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file");
    const fileName = document.getElementById("file-name");
    const enhanceBox = document.getElementById("enhance");
    const submit = document.getElementById("submit");
    const status = document.getElementById("status");
    const enhanceState = document.getElementById("enhance-state");
    const result = document.getElementById("result");
    const warning = document.getElementById("warning");
    const apiBasePath = window.location.pathname.replace(/\/$/, "");
    const transcribePath = apiBasePath === "" ? "/api/transcribe" : `${apiBasePath}/api/transcribe`;
    const healthPath = apiBasePath === "" ? "/health" : `${apiBasePath}/health`;
    let busy = false;
    let dragDepth = 0;

    function showFile(file) {
      fileName.textContent = file ? file.name : "";
    }

    function isFileDrag(event) {
      return Array.from(event.dataTransfer?.types || []).includes("Files");
    }

    document.addEventListener("dragenter", (event) => {
      if (!isFileDrag(event)) return;
      event.preventDefault();
      dragDepth += 1;
      dropZone.classList.add("drag-over");
    });
    document.addEventListener("dragover", (event) => {
      if (!isFileDrag(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    });
    document.addEventListener("dragleave", (event) => {
      if (!isFileDrag(event)) return;
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) dropZone.classList.remove("drag-over");
    });
    document.addEventListener("drop", (event) => {
      if (!isFileDrag(event)) return;
      event.preventDefault();
      dragDepth = 0;
      dropZone.classList.remove("drag-over");
      const file = event.dataTransfer.files[0];
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      fileInput.files = transfer.files;
      showFile(file);
    });
    fileInput.addEventListener("change", () => showFile(fileInput.files[0]));

    fetch(healthPath).then((response) => response.json()).then((data) => {
      if (data.missing && data.missing.length) {
        warning.classList.add("is-on");
        warning.textContent = "缺少：" + data.missing.join("、") + "。网页仍可用，转写时会提示缺什么。";
      }
    }).catch(() => {});

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

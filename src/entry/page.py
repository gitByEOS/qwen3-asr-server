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
    .app { max-width: 980px; margin: 0 auto; padding: 24px 18px 48px; }
    h1 { margin: 0; font-size: 22px; }
    .subtitle { margin-top: 4px; color: var(--muted); font-size: 13px; }
    .warning-bar { display: none; margin: 16px 0 0; padding: 11px 14px; border: 1px solid rgba(245, 158, 11, .18); border-radius: 8px; background: rgba(245, 158, 11, .045); color: #c8bd99; font-size: 13px; }
    .warning-bar.is-on { display: block; }
    .board { display: grid; grid-template-columns: minmax(260px, 320px) minmax(0, 1fr); gap: 14px; margin-top: 20px; }
    .panel { padding: 16px; border: 1px solid var(--border); border-radius: 8px; background: rgba(22, 27, 34, .82); }
    .panel h2 { margin: 0 0 12px; color: var(--muted); font-size: 12px; font-weight: 650; letter-spacing: .08em; }
    .panel-head { display: flex; align-items: center; margin-bottom: 12px; }
    .panel-head h2 { margin: 0; }
    .panel-log { grid-column: 1 / -1; }
    .drop-zone { position: relative; display: flex; min-height: 168px; flex-direction: column; align-items: center; justify-content: center; padding: 22px; border: 1.5px dashed var(--border); border-radius: 8px; background: rgba(13, 17, 23, .55); cursor: pointer; text-align: center; }
    .drop-zone::before { display: grid; width: 44px; height: 44px; place-items: center; margin-bottom: 12px; border-radius: 8px; background: rgba(78, 122, 243, .16); color: #8eacff; content: "↑"; font-size: 25px; font-weight: 750; }
    .drop-zone:hover, .drop-zone.drag-over, .drop-zone:focus-visible { border-color: var(--primary); background: rgba(45, 212, 191, .08); }
    .drop-zone strong { font-size: 17px; }
    .drop-zone span { margin-top: 5px; color: var(--muted); font-size: 13px; }
    .drop-zone input[type="file"] { position: absolute; inset: 0; width: 100%; height: 100%; cursor: pointer; opacity: 0; }
    .row { display: flex; align-items: center; margin-top: 16px; }
    button { margin-left: auto; border: 0; border-radius: 8px; padding: 8px 22px; background: var(--primary); color: #fff; cursor: pointer; }
    #copy { margin-left: auto; padding: 0; border: 0; border-radius: 0; background: none; color: var(--muted); font-size: 12px; text-decoration: underline; text-underline-offset: 3px; }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    #result { height: 220px; margin: 0; padding: 12px 14px; overflow: auto; border-radius: 8px; background: rgba(255, 255, 255, .04); white-space: pre-wrap; text-align: left; font-size: 16px; line-height: 1.7; }
    #result:empty::before { color: var(--muted); content: "转写文本会出现在这里"; }
    #status, #enhance-state { display: none; }
    .log-panel { max-height: 160px; margin: 0; overflow: auto; color: var(--muted); font-size: 12px; line-height: 1.55; white-space: pre-wrap; }
    @media (max-width: 760px) {
      .board { grid-template-columns: 1fr; }
      .panel-log { grid-column: auto; }
    }
  </style>
</head>
<body>
  <div class="app">
    <h1>离线转写</h1>
    <div class="subtitle">使用本地 {{model}} 模型，离线完成解析</div>
    <div id="warning" class="warning-bar"></div>
    <div class="board">
      <section class="panel">
        <h2>上传</h2>
        <form id="form">
          <div id="drop-zone" class="drop-zone" role="button" tabindex="0" aria-label="拖拽音视频到这里或点击选择">
            <strong>选择或拖拽音视频</strong>
            <span id="file-name">支持 wav；有 ffmpeg 时也可 mp3 / mp4 / m4a</span>
            <input id="file" type="file" accept="audio/*,video/*" />
          </div>
          <div class="row">
            <label><input id="enhance" type="checkbox" checked /> 人声增强</label>
            <button id="submit" type="submit">转写</button>
          </div>
        </form>
      </section>
      <section class="panel panel-result">
        <div class="panel-head">
          <h2>转写结果</h2>
          <button id="copy" type="button">复制</button>
        </div>
        <div id="result"></div>
        <div id="status"></div>
        <div id="enhance-state"></div>
      </section>
      <section class="panel panel-log">
        <h2>日志</h2>
        <pre id="log" class="log-panel"></pre>
      </section>
    </div>
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
    const copy = document.getElementById("copy");
    const warning = document.getElementById("warning");
    const log = document.getElementById("log");
    const apiBasePath = window.location.pathname.replace(/\/$/, "");
    const transcribePath = apiBasePath === "" ? "/api/transcribe" : `${apiBasePath}/api/transcribe`;
    const healthPath = apiBasePath === "" ? "/health" : `${apiBasePath}/health`;
    const eventsPath = apiBasePath === "" ? "/api/events" : `${apiBasePath}/api/events`;

    function appendLog(line) {
      if (!line) return;
      log.textContent += line + "\n";
      log.scrollTop = log.scrollHeight;
    }

    let busy = false;
    let gotText = false;
    let dragDepth = 0;

    function setBusy(on) {
      busy = on;
      submit.disabled = on;
    }

    const events = new EventSource(eventsPath);
    events.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (typeof data.busy === "boolean") setBusy(data.busy);
        if (data.text) {
          gotText = true;
          result.textContent = data.text;
        }
        appendLog(data.log || "");
      } catch (error) {
        appendLog(event.data);
      }
    };

    const fileHint = "支持 wav；有 ffmpeg 时也可 mp3 / mp4 / m4a";
    function showFile(file) {
      fileName.textContent = file ? file.name : fileHint;
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
    copy.addEventListener("click", async () => {
      const text = result.textContent;
      if (!text) return;
      await navigator.clipboard.writeText(text);
      copy.textContent = "已复制";
      setTimeout(() => { copy.textContent = "复制"; }, 1200);
    });

    fetch(healthPath).then((response) => response.json()).then((data) => {
      if (data.missing && data.missing.length) {
        warning.classList.add("is-on");
        warning.textContent = "缺少：" + data.missing.join("、") + "。网页仍可用，转写时会提示缺什么。";
      }
      if (data.busy) setBusy(true);
    }).catch(() => {});

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy) return;
      const file = fileInput.files[0];
      if (!file) {
        result.textContent = "请先拖入文件";
        return;
      }
      busy = true;
      gotText = false;
      submit.disabled = true;
      status.textContent = "转码中";
      result.textContent = "等待出字...";
      enhanceState.textContent = "";
      appendLog("提交 " + file.name);
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

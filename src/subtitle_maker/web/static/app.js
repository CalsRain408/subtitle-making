const elements = {
  input: document.querySelector("#video-input"),
  dropZone: document.querySelector("#drop-zone"),
  fileCard: document.querySelector("#file-card"),
  fileName: document.querySelector("#file-name"),
  fileMeta: document.querySelector("#file-meta"),
  removeFile: document.querySelector("#remove-file"),
  startButton: document.querySelector("#start-button"),
  formError: document.querySelector("#form-error"),
  uploadView: document.querySelector("#upload-view"),
  progressView: document.querySelector("#progress-view"),
  processingVisual: document.querySelector("#processing-visual"),
  statusKicker: document.querySelector("#status-kicker"),
  statusTitle: document.querySelector("#status-title"),
  statusDetail: document.querySelector("#status-detail"),
  progressTrack: document.querySelector("#progress-track"),
  progressFill: document.querySelector("#progress-fill"),
  progressLabel: document.querySelector("#progress-label"),
  progressPercent: document.querySelector("#progress-percent"),
  stepLabel: document.querySelector("#step-label"),
  uploadStep: document.querySelector("#process-upload"),
  generateStep: document.querySelector("#process-generate"),
  exportStep: document.querySelector("#process-export"),
  downloadButton: document.querySelector("#download-button"),
  subtitleDownloadButton: document.querySelector("#subtitle-download-button"),
  newTaskButton: document.querySelector("#new-task-button"),
  retryButton: document.querySelector("#retry-button"),
};

const acceptedExtensions = new Set(["mp4", "mov", "mkv", "webm", "avi", "m4v", "mpeg", "mpg"]);
const activeJobKey = "subtitle-maker-active-job";
let selectedFile = null;
let pollTimer = null;
let progressTimer = null;
let estimatedProgress = 36;

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function showError(message) {
  elements.formError.textContent = message;
  elements.formError.hidden = false;
}

function clearError() {
  elements.formError.textContent = "";
  elements.formError.hidden = true;
}

function isVideo(file) {
  const extension = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  return file.type.startsWith("video/") || acceptedExtensions.has(extension);
}

function chooseFile(file) {
  clearError();
  if (!file || !isVideo(file)) {
    showError("请选择有效的视频文件（如 MP4、MOV、MKV 或 WebM）。");
    return;
  }
  if (file.size === 0) {
    showError("这个视频文件是空的，请重新选择。");
    return;
  }
  selectedFile = file;
  elements.fileName.textContent = file.name;
  elements.fileMeta.textContent = `${formatBytes(file.size)} · 已准备上传`;
  elements.dropZone.hidden = true;
  elements.fileCard.hidden = false;
  elements.startButton.disabled = false;
}

function resetFile() {
  selectedFile = null;
  elements.input.value = "";
  elements.dropZone.hidden = false;
  elements.fileCard.hidden = true;
  elements.startButton.disabled = true;
  clearError();
}

function setProgress(value, label, indeterminate = false) {
  const safeValue = Math.max(0, Math.min(100, Math.round(value)));
  elements.progressFill.style.width = `${safeValue}%`;
  elements.progressLabel.textContent = label;
  elements.progressPercent.textContent = indeterminate ? "处理中" : `${safeValue}%`;
  elements.progressTrack.classList.toggle("is-indeterminate", indeterminate);
  elements.progressTrack.setAttribute("aria-valuenow", String(safeValue));
}

function setSteps(activeStep) {
  const steps = [elements.uploadStep, elements.generateStep, elements.exportStep];
  steps.forEach((step, index) => {
    step.classList.toggle("is-complete", index < activeStep);
    step.classList.toggle("is-active", index === activeStep);
  });
}

function showProgressView() {
  elements.uploadView.hidden = true;
  elements.progressView.hidden = false;
  elements.stepLabel.textContent = "第 2 步 / 共 3 步";
  elements.processingVisual.className = "processing-visual";
  elements.downloadButton.hidden = true;
  elements.subtitleDownloadButton.hidden = true;
  elements.newTaskButton.hidden = true;
  elements.retryButton.hidden = true;
}

function beginUpload() {
  if (!selectedFile) return;
  clearError();
  showProgressView();
  setSteps(0);
  elements.statusKicker.textContent = "UPLOADING";
  elements.statusTitle.textContent = "正在安全上传视频…";
  elements.statusDetail.textContent = "请保持页面打开，上传完成后会自动开始处理。";
  setProgress(0, "正在上传");

  const formData = new FormData();
  formData.append("video", selectedFile);
  const request = new XMLHttpRequest();
  request.open("POST", "/v1/jobs");
  request.responseType = "json";

  request.upload.addEventListener("progress", (event) => {
    if (!event.lengthComputable) return;
    setProgress((event.loaded / event.total) * 32, `上传 ${formatBytes(event.loaded)} / ${formatBytes(event.total)}`);
  });
  request.addEventListener("load", () => {
    if (request.status < 200 || request.status >= 300) {
      const detail = request.response?.detail || "视频上传失败，请稍后重试。";
      showFailure(detail, true);
      return;
    }
    const job = request.response;
    localStorage.setItem(activeJobKey, JSON.stringify({ id: job.id, filename: job.filename }));
    showProcessing(job.filename);
    pollJob(job.status_url);
  });
  request.addEventListener("error", () => showFailure("无法连接到字幕服务，请确认服务仍在运行。", true));
  request.send(formData);
}

function showProcessing(filename) {
  setSteps(1);
  elements.stepLabel.textContent = "第 2 步 / 共 3 步";
  elements.statusKicker.textContent = "PROCESSING";
  elements.statusTitle.textContent = "正在生成双语字幕并压制成片…";
  elements.statusDetail.textContent = `${filename} 已上传。转录、翻译和视频编码需要一些时间，请保留此页面。`;
  estimatedProgress = 36;
  setProgress(estimatedProgress, "语音识别与翻译", true);
  window.clearInterval(progressTimer);
  progressTimer = window.setInterval(() => {
    if (estimatedProgress < 82) estimatedProgress += Math.max(1, (82 - estimatedProgress) * 0.06);
  }, 1500);
}

async function pollJob(statusUrl) {
  window.clearTimeout(pollTimer);
  try {
    const response = await fetch(statusUrl, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("任务状态暂时无法获取");
    const job = await response.json();
    if (job.status === "succeeded") {
      showSuccess(job);
      return;
    }
    if (job.status === "failed") {
      showFailure(job.error || "字幕生成失败，请检查服务配置后重试。", false);
      return;
    }
    pollTimer = window.setTimeout(() => pollJob(statusUrl), 1800);
  } catch (error) {
    elements.statusDetail.textContent = `${error.message}，正在自动重试…`;
    pollTimer = window.setTimeout(() => pollJob(statusUrl), 3500);
  }
}

function showSuccess(job) {
  window.clearInterval(progressTimer);
  localStorage.removeItem(activeJobKey);
  setSteps(3);
  elements.processingVisual.classList.add("is-success");
  elements.stepLabel.textContent = "已完成";
  elements.statusKicker.textContent = "READY TO DOWNLOAD";
  elements.statusTitle.textContent = "双语字幕成片已经准备好了";
  const segmentText = job.segment_count ? `共生成 ${job.segment_count} 条字幕。` : "字幕已生成。";
  elements.statusDetail.textContent = `${segmentText} 中文在上、英文在下，已经压制到画面底部。`;
  setProgress(100, "字幕成片生成完成");
  elements.downloadButton.href = job.video_download_url;
  elements.downloadButton.hidden = false;
  elements.subtitleDownloadButton.href = job.download_url;
  elements.subtitleDownloadButton.hidden = false;
  elements.newTaskButton.hidden = false;
}

function showFailure(message, uploadFailed) {
  window.clearInterval(progressTimer);
  window.clearTimeout(pollTimer);
  localStorage.removeItem(activeJobKey);
  showProgressView();
  elements.processingVisual.classList.add("is-error");
  elements.statusKicker.textContent = "TASK FAILED";
  elements.statusTitle.textContent = uploadFailed ? "视频上传没有完成" : "字幕生成遇到了问题";
  elements.statusDetail.textContent = message;
  elements.progressTrack.classList.remove("is-indeterminate");
  setProgress(uploadFailed ? 0 : estimatedProgress, "任务已停止");
  elements.progressPercent.textContent = "失败";
  elements.retryButton.hidden = false;
}

function newTask() {
  window.clearTimeout(pollTimer);
  window.clearInterval(progressTimer);
  localStorage.removeItem(activeJobKey);
  elements.progressView.hidden = true;
  elements.uploadView.hidden = false;
  elements.stepLabel.textContent = "第 1 步 / 共 3 步";
  resetFile();
}

function restoreActiveJob() {
  const value = localStorage.getItem(activeJobKey);
  if (!value) return;
  try {
    const job = JSON.parse(value);
    if (!job.id || !job.filename) throw new Error("invalid job");
    showProgressView();
    showProcessing(job.filename);
    pollJob(`/v1/jobs/${encodeURIComponent(job.id)}`);
  } catch {
    localStorage.removeItem(activeJobKey);
  }
}

elements.input.addEventListener("change", () => chooseFile(elements.input.files[0]));
elements.removeFile.addEventListener("click", resetFile);
elements.startButton.addEventListener("click", beginUpload);
elements.newTaskButton.addEventListener("click", newTask);
elements.retryButton.addEventListener("click", newTask);
elements.dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    elements.input.click();
  }
});
["dragenter", "dragover"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("is-dragging");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("is-dragging");
  });
});
elements.dropZone.addEventListener("drop", (event) => chooseFile(event.dataTransfer.files[0]));

restoreActiveJob();

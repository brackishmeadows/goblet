const SAVE_KEY = "goblet.labyrinth.save";
const TRANSCRIPT_KEY = "goblet.labyrinth.transcript";
const SEED_KEY = "goblet.labyrinth.seed";
const VERSION_KEY = "goblet.labyrinth.version";
const SPLASH_MINIMUM_MS = 3000;

const PY_FILES = [
  "__init__.py",
  "add.py",
  "arithmetic.py",
  "browser_session.py",
  "compare.py",
  "divide.py",
  "fraction.py",
  "increment.py",
  "labyrinth.py",
  "liars.py",
  "multiply.py",
  "normalize.py",
  "prime.py",
  "random_range.py",
  "relation.py",
  "render.py",
  "subtract.py",
  "words.py",
];

let pyodideRuntime = null;
let busy = true;
let canonicalTranscript = "";
const commandHistory = [];
let commandHistoryIndex = 0;
let commandDraft = "";
const splashStartedAt = performance.now();

const els = {
  loadingSplash: document.getElementById("loadingSplash"),
  loadingSplashStatus: document.querySelector(".loading-splash-status"),
  status: document.getElementById("status"),
  transcript: document.getElementById("transcript"),
  transcriptEnd: document.getElementById("transcriptEnd"),
  seedInput: document.getElementById("seedInput"),
  newGameButton: document.getElementById("newGameButton"),
  resetButton: document.getElementById("resetButton"),
  commandPanel: document.querySelector(".command-panel"),
  commandForm: document.getElementById("commandForm"),
  commandInput: document.getElementById("commandInput"),
  submitButton: document.getElementById("submitButton"),
  copyButton: document.getElementById("copyButton"),
  downloadButton: document.getElementById("downloadButton"),
};

setBusy(true);
boot();

els.newGameButton.addEventListener("click", () => startGame());
els.resetButton.addEventListener("click", () => resetGame());
els.copyButton.addEventListener("click", () => copyTranscript());
els.downloadButton.addEventListener("click", () => downloadTranscript());
els.commandForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const command = els.commandInput.value.trim();
  if (command) {
    rememberCommand(command);
    runCommand(command);
  }
});
els.commandInput.addEventListener("keydown", (event) => {
  const isUndo = (event.ctrlKey || event.metaKey)
    && !event.altKey
    && !event.shiftKey
    && event.key.toLowerCase() === "z";
  if (isUndo && els.commandInput.value) {
    event.preventDefault();
    els.commandInput.value = "";
    commandHistoryIndex = commandHistory.length;
    commandDraft = "";
    return;
  }
  if (event.key === "ArrowUp" || event.key === "ArrowDown") {
    event.preventDefault();
    recallCommand(event.key === "ArrowUp" ? -1 : 1);
  }
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => {
    const command = button.dataset.command;
    rememberCommand(command);
    runCommand(command);
  });
});

const transcriptEndObserver = new IntersectionObserver(
  ([entry]) => {
    const isMobile = window.matchMedia("(max-width: 700px)").matches;
    els.commandPanel.classList.toggle("show-secondary", isMobile && entry.isIntersecting);
  },
  { rootMargin: "0px 0px -60px 0px" },
);
transcriptEndObserver.observe(els.transcriptEnd);

async function boot() {
  try {
    pyodideRuntime = await loadPyodide();
    await loadGobletPackage(pyodideRuntime);
    setStatus(hasSave() ? "ready; local save found" : "ready");
    if (hasSave()) {
      renderTranscript(localStorage.getItem(TRANSCRIPT_KEY) || "");
    }
  } catch (error) {
    console.error(error);
    setStatus(`load failed: ${error.message}`, true);
  } finally {
    await finishSplash();
    setBusy(false);
  }
}

async function finishSplash() {
  const elapsed = performance.now() - splashStartedAt;
  const remaining = Math.max(0, SPLASH_MINIMUM_MS - elapsed);
  if (remaining > 0) {
    await new Promise((resolve) => setTimeout(resolve, remaining));
  }
  els.loadingSplashStatus.textContent = els.status.textContent;
  els.loadingSplash.classList.add("is-hidden");
  els.loadingSplash.addEventListener("transitionend", () => {
    els.loadingSplash.remove();
  }, { once: true });
}

async function loadGobletPackage(pyodide) {
  pyodide.FS.mkdirTree("/home/pyodide/goblet");
  for (const file of PY_FILES) {
    const response = await fetch(`../src/goblet/${file}`);
    if (!response.ok) {
      throw new Error(`could not load ${file}`);
    }
    pyodide.FS.writeFile(`/home/pyodide/goblet/${file}`, await response.text());
  }
  pyodide.runPython("import sys\nsys.path.insert(0, '/home/pyodide')");
  pyodide.runPython("from goblet import browser_session");
}

async function startGame() {
  const seed = els.seedInput.value.trim();
  await callSession("start", seed || null);
}

async function resetGame() {
  if (!window.confirm("Reset the local labyrinth save?")) {
    return;
  }
  localStorage.removeItem(SAVE_KEY);
  localStorage.removeItem(TRANSCRIPT_KEY);
  localStorage.removeItem(SEED_KEY);
  localStorage.removeItem(VERSION_KEY);
  renderTranscript("", { scrollToTop: true });
  setStatus("reset");
}

async function runCommand(command) {
  const saveData = localStorage.getItem(SAVE_KEY);
  if (!saveData) {
    setStatus("start a game first");
    return;
  }
  await callSession("step", saveData, command);
  els.commandInput.value = "";
  els.commandInput.focus();
}

async function callSession(functionName, ...args) {
  if (!pyodideRuntime || busy) {
    return;
  }
  setBusy(true);
  try {
    pyodideRuntime.globals.set("session_args_json", JSON.stringify(args));
    pyodideRuntime.globals.set("session_function_name", functionName);
    const result = pyodideRuntime.runPython(`
import json
session_args = json.loads(session_args_json)
packet = getattr(browser_session, session_function_name)(*session_args)
json.dumps(packet)
`);
    const packet = JSON.parse(result);
    persistPacket(packet);
    renderTranscript(packet.transcript, {
      scrollToLatestTurn: functionName === "step",
      scrollToTop: functionName === "start",
    });
    setStatus(statusText(packet));
  } catch (error) {
    console.error(error);
    setStatus(`command failed: ${error.message}`, true);
  } finally {
    pyodideRuntime.globals.delete("session_args_json");
    pyodideRuntime.globals.delete("session_function_name");
    setBusy(false);
  }
}

function persistPacket(packet) {
  localStorage.setItem(SAVE_KEY, packet.save_data);
  localStorage.setItem(TRANSCRIPT_KEY, packet.transcript || "");
  localStorage.setItem(VERSION_KEY, String(packet.version));
  if (packet.seed !== null && packet.seed !== undefined) {
    localStorage.setItem(SEED_KEY, String(packet.seed));
  }
}

function renderTranscript(text, { scrollToLatestTurn = false, scrollToTop = false } = {}) {
  const previousDisplayText = transcriptForDisplay(canonicalTranscript);
  canonicalTranscript = text;
  const fragment = document.createDocumentFragment();
  let latestCommandLine = null;
  let responseLineIndex = 0;
  const displayText = transcriptForDisplay(text);
  const hasAppendedTurn = scrollToLatestTurn
    && previousDisplayText
    && displayText.startsWith(previousDisplayText);
  const lines = displayText ? displayText.split("\n") : [];
  let lineOffset = 0;
  lines.forEach((line, index) => {
    if (line.startsWith("> ")) {
      const lineElement = document.createElement("span");
      lineElement.classList.add("player-command");
      lineElement.textContent = line;
      latestCommandLine = lineElement;
      fragment.append(lineElement);
    } else if (hasAppendedTurn && lineOffset >= previousDisplayText.length && line) {
      const lineElement = document.createElement("span");
      lineElement.classList.add("new-response");
      lineElement.style.setProperty("--reveal-delay", `${Math.min(responseLineIndex * 35, 140)}ms`);
      lineElement.textContent = line;
      responseLineIndex += 1;
      fragment.append(lineElement);
    } else {
      fragment.append(document.createTextNode(line));
    }
    if (index < lines.length - 1) {
      fragment.append(document.createTextNode("\n"));
    }
    lineOffset += line.length + 1;
  });
  els.transcript.replaceChildren(fragment);

  requestAnimationFrame(() => {
    if (scrollToTop) {
      scrollTranscriptToTop();
    } else if (scrollToLatestTurn && latestCommandLine) {
      scrollTranscriptToLine(latestCommandLine);
    } else if (window.matchMedia("(max-width: 700px)").matches) {
      const transcriptBottom = window.scrollY + els.transcript.getBoundingClientRect().bottom;
      const commandBarClearance = 72;
      window.scrollTo(0, Math.max(0, transcriptBottom - window.innerHeight + commandBarClearance));
    } else {
      els.transcript.scrollTop = els.transcript.scrollHeight;
    }
  });
}

function transcriptForDisplay(text) {
  if (!text) {
    return "";
  }
  const lines = text.split("\n");
  let titleIndex = 0;
  if (lines[0]?.startsWith("random seed: ")) {
    titleIndex = 1;
  }
  if (lines[titleIndex] !== "Liar's Labyrinth") {
    return text;
  }
  let contentIndex = titleIndex + 1;
  while (lines[contentIndex] === "") {
    contentIndex += 1;
  }
  return lines.slice(contentIndex).join("\n");
}

function scrollTranscriptToLine(lineElement) {
  const readingMargin = 12;
  const lineTop = lineElement.getBoundingClientRect().top;
  const behavior = preferredScrollBehavior();
  if (window.matchMedia("(max-width: 700px)").matches) {
    window.scrollTo({
      top: Math.max(0, window.scrollY + lineTop - readingMargin),
      behavior,
    });
    return;
  }
  const transcriptTop = els.transcript.getBoundingClientRect().top;
  els.transcript.scrollTo({
    top: Math.max(0, els.transcript.scrollTop + lineTop - transcriptTop - readingMargin),
    behavior,
  });
}

function scrollTranscriptToTop() {
  const behavior = preferredScrollBehavior();
  if (window.matchMedia("(max-width: 700px)").matches) {
    window.scrollTo({ top: 0, behavior });
    return;
  }
  els.transcript.scrollTo({ top: 0, behavior });
}

function preferredScrollBehavior() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

function rememberCommand(command) {
  commandHistory.push(command);
  commandHistoryIndex = commandHistory.length;
  commandDraft = "";
}

function recallCommand(direction) {
  if (!commandHistory.length) {
    return;
  }
  if (direction < 0) {
    if (commandHistoryIndex === commandHistory.length) {
      commandDraft = els.commandInput.value;
    }
    commandHistoryIndex = Math.max(0, commandHistoryIndex - 1);
    els.commandInput.value = commandHistory[commandHistoryIndex];
  } else if (commandHistoryIndex < commandHistory.length - 1) {
    commandHistoryIndex += 1;
    els.commandInput.value = commandHistory[commandHistoryIndex];
  } else {
    commandHistoryIndex = commandHistory.length;
    els.commandInput.value = commandDraft;
  }
  els.commandInput.setSelectionRange(els.commandInput.value.length, els.commandInput.value.length);
}

function statusText(packet) {
  const seed = packet.seed ? `; seed ${packet.seed}` : "";
  return `${packet.status}; saved locally${seed}`;
}

function hasSave() {
  return Boolean(localStorage.getItem(SAVE_KEY));
}

async function copyTranscript() {
  const text = localStorage.getItem(TRANSCRIPT_KEY) || canonicalTranscript;
  await navigator.clipboard.writeText(text);
  setStatus("transcript copied");
}

function downloadTranscript() {
  const text = localStorage.getItem(TRANSCRIPT_KEY) || canonicalTranscript;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "liars-labyrinth-transcript.txt";
  link.click();
  URL.revokeObjectURL(url);
  setStatus("transcript exported");
}

function setBusy(value) {
  busy = value;
  [
    els.seedInput,
    els.newGameButton,
    els.resetButton,
    els.commandInput,
    els.submitButton,
    els.copyButton,
    els.downloadButton,
    ...document.querySelectorAll("[data-command]"),
  ].forEach((element) => {
    element.disabled = value;
  });
}

function setStatus(message, isError = false) {
  els.status.textContent = message;
  els.status.classList.toggle("error", isError);
}

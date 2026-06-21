const SAVE_KEY = "goblet.labyrinth.save";
const TRANSCRIPT_KEY = "goblet.labyrinth.transcript";
const SEED_KEY = "goblet.labyrinth.seed";
const VERSION_KEY = "goblet.labyrinth.version";

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

const els = {
  status: document.getElementById("status"),
  transcript: document.getElementById("transcript"),
  seedInput: document.getElementById("seedInput"),
  newGameButton: document.getElementById("newGameButton"),
  continueButton: document.getElementById("continueButton"),
  resetButton: document.getElementById("resetButton"),
  commandForm: document.getElementById("commandForm"),
  commandInput: document.getElementById("commandInput"),
  submitButton: document.getElementById("submitButton"),
  copyButton: document.getElementById("copyButton"),
  downloadButton: document.getElementById("downloadButton"),
};

setBusy(true);
boot();

els.newGameButton.addEventListener("click", () => startGame());
els.continueButton.addEventListener("click", () => continueGame());
els.resetButton.addEventListener("click", () => resetGame());
els.copyButton.addEventListener("click", () => copyTranscript());
els.downloadButton.addEventListener("click", () => downloadTranscript());
els.commandForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const command = els.commandInput.value.trim();
  if (command) {
    runCommand(command);
  }
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => runCommand(button.dataset.command));
});

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
    setBusy(false);
  }
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

async function continueGame() {
  const saveData = localStorage.getItem(SAVE_KEY);
  if (!saveData) {
    setStatus("no local save");
    return;
  }
  await callSession("show", saveData);
}

async function resetGame() {
  if (!window.confirm("Reset the local labyrinth save?")) {
    return;
  }
  localStorage.removeItem(SAVE_KEY);
  localStorage.removeItem(TRANSCRIPT_KEY);
  localStorage.removeItem(SEED_KEY);
  localStorage.removeItem(VERSION_KEY);
  renderTranscript("");
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
    renderTranscript(packet.transcript);
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

function renderTranscript(text) {
  els.transcript.textContent = text;
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function statusText(packet) {
  const seed = packet.seed ? `; seed ${packet.seed}` : "";
  return `${packet.status}; saved locally${seed}`;
}

function hasSave() {
  return Boolean(localStorage.getItem(SAVE_KEY));
}

async function copyTranscript() {
  const text = localStorage.getItem(TRANSCRIPT_KEY) || els.transcript.textContent;
  await navigator.clipboard.writeText(text);
  setStatus("transcript copied");
}

function downloadTranscript() {
  const text = localStorage.getItem(TRANSCRIPT_KEY) || els.transcript.textContent;
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
    els.continueButton,
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

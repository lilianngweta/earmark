const form = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const dropzoneText = document.getElementById("dropzone-text");
const status = document.getElementById("status");
const generateBtn = document.getElementById("generate-btn");

const nowPlaying = document.getElementById("now-playing");
const nowPlayingTitle = document.getElementById("now-playing-title");
const nowPlayingScript = document.getElementById("now-playing-script");
const player = document.getElementById("player");

const episodeList = document.getElementById("episode-list");
const emptyLibrary = document.getElementById("empty-library");

let currentEpisodeId = null;

function formatDate(timestamp) {
  return new Date(timestamp * 1000).toLocaleString();
}

function setStatus(message, tone = "default") {
  status.textContent = message;
  status.className = tone === "default" ? "status" : `status is-${tone}`;
}

function renderEpisodes(episodes) {
  episodeList.innerHTML = "";
  emptyLibrary.hidden = episodes.length > 0;
  for (const episode of episodes) {
    const item = document.createElement("li");
    item.className = "episode";
    item.innerHTML = `
      <div class="episode-info">
        <p class="episode-title"></p>
        <p class="episode-meta"></p>
      </div>
      <div class="episode-actions">
        <button class="play-btn">Play</button>
        <button class="delete-btn" title="Delete episode" aria-label="Delete episode">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M7 7l1 12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-12"/>
          </svg>
        </button>
      </div>
    `;
    item.querySelector(".episode-title").textContent = episode.title;
    item.querySelector(".episode-meta").textContent =
      `from ${episode.source_filename} · ${formatDate(episode.created_at)}`;
    item.querySelector(".play-btn").addEventListener("click", () => playEpisode(episode));
    item.querySelector(".delete-btn").addEventListener("click", () => deleteEpisode(episode));
    episodeList.appendChild(item);
  }
}

function playEpisode(episode) {
  currentEpisodeId = episode.id;
  nowPlaying.hidden = false;
  nowPlayingTitle.textContent = episode.title;
  nowPlayingScript.textContent = episode.script;
  player.src = episode.audio_url;
  player.play();
  nowPlaying.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function deleteEpisode(episode) {
  if (!confirm(`Delete "${episode.title}"? This can't be undone.`)) return;

  try {
    const response = await fetch(`/api/episodes/${episode.id}`, { method: "DELETE" });
    if (!response.ok) throw new Error("delete failed");

    if (currentEpisodeId === episode.id) {
      currentEpisodeId = null;
      player.pause();
      player.removeAttribute("src");
      nowPlaying.hidden = true;
    }
    await loadEpisodes();
  } catch (err) {
    setStatus("Couldn't delete that episode — try again.", "error");
  }
}

async function loadEpisodes() {
  try {
    const response = await fetch("/api/episodes");
    if (!response.ok) return;
    renderEpisodes(await response.json());
  } catch (err) {
    // The library is a nice-to-have — a failed fetch shouldn't block uploading.
  }
}

function updateDropzoneLabel() {
  dropzoneText.textContent = fileInput.files.length
    ? `Selected: ${fileInput.files[0].name}`
    : "Drop a .md file here, or click to browse";
}

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");
  if (event.dataTransfer.files.length) {
    fileInput.files = event.dataTransfer.files;
    updateDropzoneLabel();
  }
});
fileInput.addEventListener("change", updateDropzoneLabel);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length) {
    setStatus("Choose a Markdown file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("markdown", fileInput.files[0]);

  generateBtn.disabled = true;
  setStatus("Writing the script and recording the episode — this can take a minute…");

  try {
    const response = await fetch("/api/generate", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || "Something went wrong.", "error");
      return;
    }
    setStatus("Episode is ready.", "success");
    playEpisode(data);
    await loadEpisodes();
  } catch (err) {
    setStatus("Couldn't reach the server. Is it running?", "error");
  } finally {
    generateBtn.disabled = false;
  }
});

loadEpisodes();

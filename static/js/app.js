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

function formatDate(timestamp) {
  return new Date(timestamp * 1000).toLocaleString();
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
      <button class="play-btn">▶ Play</button>
    `;
    item.querySelector(".episode-title").textContent = episode.title;
    item.querySelector(".episode-meta").textContent =
      `from ${episode.source_filename} · ${formatDate(episode.created_at)}`;
    item.querySelector(".play-btn").addEventListener("click", () => playEpisode(episode));
    episodeList.appendChild(item);
  }
}

function playEpisode(episode) {
  nowPlaying.hidden = false;
  nowPlayingTitle.textContent = episode.title;
  nowPlayingScript.textContent = episode.script;
  player.src = episode.audio_url;
  player.play();
  nowPlaying.scrollIntoView({ behavior: "smooth", block: "start" });
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
    status.textContent = "Choose a Markdown file first.";
    return;
  }

  const formData = new FormData();
  formData.append("markdown", fileInput.files[0]);

  generateBtn.disabled = true;
  status.textContent = "🎙️ Writing the script and recording your episode — this can take a minute...";

  try {
    const response = await fetch("/api/generate", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      status.textContent = `⚠️ ${data.error || "Something went wrong."}`;
      return;
    }
    status.textContent = "✅ Episode is ready!";
    playEpisode(data);
    await loadEpisodes();
  } catch (err) {
    status.textContent = "⚠️ Couldn't reach the server. Is it running?";
  } finally {
    generateBtn.disabled = false;
  }
});

loadEpisodes();

// AIS-140 Web App Client Controller
let currentProfile = "VLTD";
let isRunning = false;
let selectedRto = { code: "GJ-16", name: "Bharuch", lat: 21.7051, lon: 72.9959 };
let rtoDatabase = {};

const SERVERS = {
  VLTD: "commonlayer.parivahan.gov.in : 9031 (Emergency: :9032)",
  CGM:  "103.234.162.150 : 5013 (Mines Gujarat)",
  GPCB: "103.234.162.31 : 9999 (Pollution Control Board)"
};

// DOM Elements
const statusDot = document.getElementById("global-status-dot");
const statusText = document.getElementById("global-status-text");
const packetCountEl = document.getElementById("global-packet-count");
const terminalBody = document.getElementById("terminal-body");
const linkInput = document.getElementById("location-link-input");
const btnExtract = document.getElementById("btn-extract-link");
const linkStatus = document.getElementById("link-extract-status");

const rtoSearchInput = document.getElementById("rto-search");
const rtoDropdown = document.getElementById("rto-dropdown");
const rtoTargetInfo = document.getElementById("rto-target-info");
const rtoClearBtn = document.getElementById("rto-clear-btn");

const btnStartStop = document.getElementById("btn-start-stop");
const btnSosOn = document.getElementById("btn-sos-on");
const btnSosOff = document.getElementById("btn-sos-off");
const serverBanner = document.getElementById("server-banner");

// Init
window.addEventListener("DOMContentLoaded", () => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
  setupSSE();
  setupProfileTabs();
  setupAutocomplete();
  setupActions();
  checkUrlParams();
});

// 1. URL Query Parameter Support (?q=lat,lon or ?url=...)
function checkUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q") || params.get("query");
  const rawUrl = params.get("url");

  if (q) {
    linkInput.value = q;
    extractLocation(q);
  } else if (rawUrl) {
    linkInput.value = rawUrl;
    extractLocation(rawUrl);
  }
}

// 2. Real-Time SSE Telemetry Stream
function setupSSE() {
  const evSource = new EventSource("/api/events");

  evSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.event === "init") {
        if (data.data.rtos) rtoDatabase = data.data.rtos;
      } else if (data.event === "log") {
        appendLog(data.data.time, data.data.msg);
      } else if (data.event === "status") {
        updateStatus(data.data.status, data.data.count);
      }
    } catch (err) {
      console.error("SSE parse error", err);
    }
  };

  evSource.onerror = () => {
    console.warn("SSE connection interrupted. Reconnecting in 3s...");
  };
}

function updateStatus(status, count) {
  statusText.textContent = status.toUpperCase();
  packetCountEl.textContent = count;

  statusDot.className = "status-dot";
  if (status === "Sending") {
    statusDot.classList.add("sending");
    isRunning = true;
    btnStartStop.textContent = "⏹ STOP SIMULATOR";
    btnStartStop.className = "btn btn-danger btn-large";
    btnSosOn.disabled = false;
    btnSosOff.disabled = false;
  } else if (status === "Connecting" || status === "Connected") {
    statusDot.classList.add("connecting");
  } else {
    statusDot.classList.add("stopped");
    isRunning = false;
    btnStartStop.textContent = "▶ START SIMULATOR";
    btnStartStop.className = "btn btn-success btn-large";
    btnSosOn.disabled = true;
    btnSosOff.disabled = true;
  }
}

function appendLog(time, msg) {
  const div = document.createElement("div");
  div.className = "log-entry";
  if (msg.includes("[TX]") || msg.includes("TX:")) div.classList.add("tx");
  else if (msg.includes("[RX]") || msg.includes("ACK")) div.classList.add("rx");
  else if (msg.includes("ERR") || msg.includes("Error") || msg.includes("Failed")) div.classList.add("err");
  else if (msg.includes("WARN")) div.classList.add("warn");
  else div.classList.add("system");

  div.textContent = `[${time}] ${msg}`;
  terminalBody.appendChild(div);
  terminalBody.scrollTop = terminalBody.scrollHeight;
}

// 3. Location Link Extraction
btnExtract.addEventListener("click", () => {
  const raw = linkInput.value.trim();
  if (!raw) {
    linkStatus.textContent = "⚠️ Please enter a WhatsApp or Google Maps link.";
    linkStatus.style.color = "var(--warning)";
    return;
  }
  extractLocation(raw);
});

async function extractLocation(urlOrText) {
  linkStatus.textContent = "🔍 Extracting GPS coordinates...";
  linkStatus.style.color = "var(--text-accent)";
  try {
    const res = await fetch(`/api/extract_location?url=${encodeURIComponent(urlOrText)}`);
    const data = await res.json();
    if (data.success) {
      linkStatus.textContent = `✅ Extracted (${data.lat.toFixed(6)}, ${data.lon.toFixed(6)}) → Nearest RTO: ${data.rto_code} (${data.rto_name}, ~${data.distance_km}km away)`;
      linkStatus.style.color = "var(--success)";

      // Apply to UI
      selectedRto = { code: data.rto_code, name: data.rto_name, lat: data.lat, lon: data.lon };
      rtoSearchInput.value = `${data.rto_code} – ${data.rto_name}`;
      rtoTargetInfo.textContent = `GPS Target: ${data.lat.toFixed(6)}°N, ${data.lon.toFixed(6)}°E (${data.rto_name})`;

      document.getElementById("cfg-lat").value = data.lat.toFixed(6);
      document.getElementById("cfg-lon").value = data.lon.toFixed(6);
    } else {
      linkStatus.textContent = "❌ Failed to extract coordinates from link. Ensure link format has ?q=lat,lon";
      linkStatus.style.color = "var(--danger)";
    }
  } catch (err) {
    linkStatus.textContent = "❌ Error connecting to extractor API.";
    linkStatus.style.color = "var(--danger)";
  }
}

// 4. Google-style Instant Autocomplete Search
function setupAutocomplete() {
  let activeIndex = -1;

  async function triggerSearch(queryText) {
    const raw = (queryText !== undefined ? queryText : rtoSearchInput.value).trim();
    let query = raw;
    if (raw.includes(" – ")) {
      query = raw.split(" – ")[1].trim();
    }
    try {
      const res = await fetch(`/api/rto_search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      activeIndex = -1;
      renderDropdown(data.matches || []);
    } catch (err) {
      console.error("RTO search failed", err);
    }
  }

  rtoSearchInput.addEventListener("input", () => triggerSearch());

  rtoSearchInput.addEventListener("focus", () => {
    rtoSearchInput.select();
    triggerSearch("");
  });

  rtoSearchInput.addEventListener("click", () => {
    if (rtoDropdown.classList.contains("hidden")) {
      triggerSearch();
    }
  });

  rtoClearBtn.addEventListener("click", () => {
    rtoSearchInput.value = "";
    rtoSearchInput.focus();
    triggerSearch("");
  });

  rtoSearchInput.addEventListener("keydown", (e) => {
    const items = rtoDropdown.querySelectorAll(".autocomplete-item");
    if (rtoDropdown.classList.contains("hidden") || items.length === 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        triggerSearch("");
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveHighlight(items, activeIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveHighlight(items, activeIndex);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < items.length) {
        items[activeIndex].click();
      } else if (items.length > 0) {
        items[0].click();
      }
    } else if (e.key === "Escape") {
      rtoDropdown.classList.add("hidden");
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".autocomplete-wrapper")) {
      rtoDropdown.classList.add("hidden");
    }
  });
}

function updateActiveHighlight(items, index) {
  items.forEach((it, i) => {
    if (i === index) {
      it.classList.add("selected");
      it.scrollIntoView({ block: "nearest" });
    } else {
      it.classList.remove("selected");
    }
  });
}

function renderDropdown(matches) {
  rtoDropdown.innerHTML = "";
  if (!matches || matches.length === 0) {
    rtoDropdown.classList.add("hidden");
    return;
  }

  matches.forEach(item => {
    let code, name, lat, lon;
    if (typeof item === "object" && item.code) {
      code = item.code;
      name = item.name;
      lat = parseFloat(item.lat);
      lon = parseFloat(item.lon);
    } else {
      const parts = String(item).split(" – ");
      code = parts[0] ? parts[0].trim() : "GJ-01";
      name = parts[1] ? parts[1].trim() : "";
      const dbEntry = (rtoDatabase && rtoDatabase[code]) || {};
      lat = dbEntry.lat || 21.7051;
      lon = dbEntry.lon || 72.9959;
    }

    const latStr = (!isNaN(lat) && lat !== 0) ? lat.toFixed(4) : "21.7051";
    const lonStr = (!isNaN(lon) && lon !== 0) ? lon.toFixed(4) : "72.9959";

    const div = document.createElement("div");
    div.className = "autocomplete-item";
    div.innerHTML = `
      <span>${code} – <strong>${name}</strong></span>
      <span class="autocomplete-coords">${latStr}°N, ${lonStr}°E</span>
    `;
    div.addEventListener("click", () => {
      selectedRto = { code, name, lat, lon };
      rtoSearchInput.value = `${code} – ${name}`;
      rtoTargetInfo.textContent = `GPS Target: ${parseFloat(latStr).toFixed(6)}°N, ${parseFloat(lonStr).toFixed(6)}°E (${name})`;
      document.getElementById("cfg-lat").value = parseFloat(latStr).toFixed(6);
      document.getElementById("cfg-lon").value = parseFloat(lonStr).toFixed(6);
      rtoDropdown.classList.add("hidden");
    });
    rtoDropdown.appendChild(div);
  });

  rtoDropdown.classList.remove("hidden");
}

// 5. Profile Switching
function setupProfileTabs() {
  document.querySelectorAll(".profile-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".profile-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentProfile = tab.dataset.profile;
      applyProfileView(currentProfile);
    });
  });
}

function applyProfileView(profile) {
  serverBanner.textContent = `Target Server: ${SERVERS[profile] || SERVERS["VLTD"]}`;
  const rtoGroup = document.getElementById("rto-group");
  const coordsRow = document.getElementById("coords-row");
  const autoSosGroup = document.getElementById("auto-sos-group");
  const vregGroup = document.getElementById("vreg-group");
  const singlePushSec = document.getElementById("single-push-section");

  if (profile === "VLTD") {
    rtoGroup.style.display = "flex";
    coordsRow.style.display = "none";
    autoSosGroup.style.display = "flex";
    vregGroup.style.display = "none";
    singlePushSec.style.display = "flex";
  } else if (profile === "GPCB") {
    rtoGroup.style.display = "none";
    coordsRow.style.display = "flex";
    autoSosGroup.style.display = "none";
    vregGroup.style.display = "flex";
    singlePushSec.style.display = "none";
  } else if (profile === "CGM") {
    rtoGroup.style.display = "none";
    coordsRow.style.display = "flex";
    autoSosGroup.style.display = "none";
    vregGroup.style.display = "none";
    singlePushSec.style.display = "none";
  }
}

// 6. Simulator Actions
function getConfig() {
  const imei = document.getElementById("cfg-imei").value.trim();
  const vreg = document.getElementById("cfg-vreg").value.trim();
  const interval = parseInt(document.getElementById("cfg-interval").value, 10) || 10;
  const autoSos = document.getElementById("cfg-auto-sos").checked;
  const lat = parseFloat(document.getElementById("cfg-lat").value) || selectedRto.lat;
  const lon = parseFloat(document.getElementById("cfg-lon").value) || selectedRto.lon;

  return {
    profile: currentProfile,
    imei: imei,
    vreg: currentProfile === "GPCB" ? vreg : "GJ01AC0000",
    lat: lat,
    lat_h: "N",
    lon: lon,
    lon_h: "E",
    interval: interval,
    rto: currentProfile === "VLTD" ? selectedRto.code : null,
    auto_sos: autoSos
  };
}

function setupActions() {
  btnStartStop.addEventListener("click", async () => {
    if (isRunning) {
      await fetch("/api/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: 1 })
      });
    } else {
      const cfg = getConfig();
      await fetch("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: 1, config: cfg })
      });
    }
  });

  btnSosOn.addEventListener("click", async () => {
    const cfg = getConfig();
    await fetch("/api/sos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: 1, config: cfg, mode: "EMR" })
    });
  });

  btnSosOff.addEventListener("click", async () => {
    const cfg = getConfig();
    await fetch("/api/sos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: 1, config: cfg, mode: "SEM" })
    });
  });

  document.querySelectorAll("[data-push]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const ptype = btn.dataset.push;
      const cfg = getConfig();
      await fetch("/api/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: 1, config: cfg, packet_type: ptype })
      });
    });
  });

  document.getElementById("btn-clear-logs").addEventListener("click", () => {
    terminalBody.innerHTML = "";
  });

  document.getElementById("btn-export-logs").addEventListener("click", () => {
    const text = terminalBody.innerText;
    const blob = new Blob([text], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ais140_logs_${Date.now()}.txt`;
    a.click();
  });
}

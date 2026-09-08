"use strict";

const state = {
  status: null,
  analytics: null,
  plateSearch: null,
  plateResults: [],
  vehicles: [],
  selectedId: null,
  journey: null,
  visitIndex: 0,
  sampleIndex: 0,
  replayTimer: null,
  markers: [],
};

const elements = {
  status: document.querySelector("#system-status"),
  disclosure: document.querySelector("#disclosure-banner"),
  form: document.querySelector("#search-form"),
  search: document.querySelector("#search"),
  multiOnly: document.querySelector("#multi-only"),
  resultSummary: document.querySelector("#result-summary"),
  list: document.querySelector("#vehicle-list"),
  title: document.querySelector("#journey-title"),
  meta: document.querySelector("#journey-meta"),
  replay: document.querySelector("#replay"),
  timeline: document.querySelector("#timeline"),
  evidenceTitle: document.querySelector("#evidence-title"),
  evidenceContent: document.querySelector("#evidence-content"),
  sampleTabs: document.querySelector("#sample-tabs"),
  vehicleTemplate: document.querySelector("#vehicle-template"),
  analyticsNotice: document.querySelector("#analytics-notice"),
  analyticsSummary: document.querySelector("#analytics-summary"),
  densityTable: document.querySelector("#density-table"),
  odTable: document.querySelector("#od-table"),
  bottleneckTable: document.querySelector("#bottleneck-table"),
  plateForm: document.querySelector("#plate-search-form"),
  plateInput: document.querySelector("#plate-search-input"),
  plateButton: document.querySelector("#plate-search-button"),
  plateChip: document.querySelector("#plate-search-chip"),
  plateStatus: document.querySelector("#plate-search-status"),
  plateResults: document.querySelector("#plate-search-results"),
};

const map = L.map("map", { attributionControl: false, zoomControl: true });
const cameraLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map);

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${detail}`);
  }
  return response.json();
}

function seconds(value) {
  return `${Number(value).toFixed(2)} s`;
}

function shortId(value) {
  return value.replace("roadeye_", "").slice(0, 12);
}

function setError(message) {
  elements.status.textContent = "Runtime error";
  elements.status.className = "status-chip fail";
  elements.timeline.className = "timeline";
  elements.timeline.replaceChildren();
  const error = document.createElement("p");
  error.className = "error-box";
  error.textContent = message;
  elements.timeline.append(error);
}

function drawCameras() {
  cameraLayer.clearLayers();
  const points = [];
  const density = new Map(
    (state.analytics?.camera_density || []).map((row) => [row.camera, row.observed_runtime_visit_count]),
  );
  const maximumDensity = Math.max(1, ...density.values());
  Object.entries(state.status.camera_positions).forEach(([camera, position]) => {
    const point = [position.latitude, position.longitude];
    const observedVisits = density.get(camera) || 0;
    points.push(point);
    L.circleMarker(point, {
      radius: 6 + 12 * Math.sqrt(observedVisits / maximumDensity),
      color: "#6d91a8",
      weight: 2,
      fillColor: "#21c997",
      fillOpacity: .25 + .65 * (observedVisits / maximumDensity),
    }).bindTooltip(`${camera} · ${observedVisits} observed predicted visits`).addTo(cameraLayer);
  });
  if (points.length) map.fitBounds(points, { padding: [70, 70], maxZoom: 19 });
}

function metric(label, value) {
  const card = document.createElement("div");
  const number = document.createElement("strong");
  number.textContent = String(value);
  const caption = document.createElement("span");
  caption.textContent = label;
  card.append(number, caption);
  return card;
}

function tableRows(root, rows, render) {
  root.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No multi-camera prediction in this runtime.";
    root.append(empty);
    return;
  }
  rows.forEach((row) => {
    const item = document.createElement("div");
    const [label, value] = render(row);
    const name = document.createElement("span");
    name.textContent = label;
    const count = document.createElement("strong");
    count.textContent = value;
    item.append(name, count);
    root.append(item);
  });
}

function renderAnalytics() {
  const analytics = state.analytics;
  const summary = analytics.summary;
  elements.analyticsNotice.textContent = state.status.analytics_notice;
  elements.analyticsSummary.replaceChildren(
    metric("predicted IDs", summary.predicted_global_vehicle_ids),
    metric("multi-camera", summary.multi_camera_predicted_vehicle_ids),
    metric("observed visits", summary.observed_runtime_visits),
    metric("predicted links", summary.predicted_transitions),
  );
  tableRows(elements.densityTable, analytics.camera_density, (row) => [
    row.camera,
    `${row.observed_runtime_visit_count} visits`,
  ]);
  tableRows(elements.odTable, analytics.origin_destination_pairs.slice(0, 8), (row) => [
    `${row.origin_camera} → ${row.destination_camera}`,
    `${row.predicted_vehicle_count} IDs`,
  ]);
  tableRows(elements.bottleneckTable, analytics.bottleneck_proxies.slice(0, 8), (row) => [
    `${row.from_camera} → ${row.to_camera}`,
    `${row.predicted_transition_count} links`,
  ]);
}

function renderPlateSearchStatus() {
  const plateSearch = state.plateSearch;
  const ready = plateSearch.availability === "READY";
  elements.plateInput.disabled = !ready;
  elements.plateButton.disabled = !ready;
  elements.plateChip.textContent = ready ? "UNVERIFIED" : "BLOCKED";
  elements.plateChip.className = `mini-status ${ready ? "unverified" : "blocked"}`;
  elements.plateStatus.textContent = ready
    ? `${plateSearch.index_entry_count} predicted plate observations indexed. ${plateSearch.score_notice}`
    : plateSearch.reason;
  if (!ready) {
    elements.plateResults.replaceChildren();
  }
}

async function searchPlates() {
  const query = new URLSearchParams({
    q: elements.plateInput.value.trim(),
    limit: "25",
  });
  const response = await getJson(`/api/plate-search?${query}`);
  state.plateResults = response.results;
  renderPlateResults(response);
}

function renderPlateResults(response) {
  elements.plateResults.replaceChildren();
  if (!response.results.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = response.enabled
      ? "No matching predicted plate observation."
      : response.reason;
    elements.plateResults.append(empty);
    return;
  }
  response.results.forEach((result) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "plate-result";
    const plate = document.createElement("strong");
    plate.textContent = result.predicted_plate_text;
    const evidence = document.createElement("span");
    evidence.textContent = `${result.match_kind} match · ${result.camera} · ${seconds(result.observed_s)}`;
    const notice = document.createElement("span");
    notice.textContent = `OCR ${result.ocr_score.toFixed(3)} · uncalibrated prediction`;
    row.append(plate, evidence, notice);
    row.addEventListener("click", () =>
      selectJourney(result.global_id, result.visit_index, result.sample_index),
    );
    elements.plateResults.append(row);
  });
}

async function loadVehicles() {
  const query = new URLSearchParams({
    q: elements.search.value.trim(),
    multi_camera_only: String(elements.multiOnly.checked),
    limit: "50",
  });
  state.vehicles = await getJson(`/api/vehicles?${query}`);
  renderVehicles();
}

function renderVehicles() {
  elements.list.replaceChildren();
  elements.resultSummary.textContent = `${state.vehicles.length} prediction${state.vehicles.length === 1 ? "" : "s"} shown`;
  if (!state.vehicles.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No matching predicted vehicle.";
    elements.list.append(empty);
    return;
  }
  state.vehicles.forEach((vehicle) => {
    const row = elements.vehicleTemplate.content.firstElementChild.cloneNode(true);
    row.dataset.globalId = vehicle.global_id;
    row.classList.toggle("selected", vehicle.global_id === state.selectedId);
    row.querySelector("img").src = vehicle.representative_crop_url;
    row.querySelector(".vehicle-id").textContent = shortId(vehicle.global_id);
    row.querySelector(".vehicle-cameras").textContent = `${vehicle.camera_count} cameras · ${vehicle.cameras.join(" → ")}`;
    row.querySelector(".vehicle-time").textContent = `${seconds(vehicle.first_observed_s)} to ${seconds(vehicle.last_observed_s)}`;
    row.addEventListener("click", () => selectJourney(vehicle.global_id));
    elements.list.append(row);
  });
}

async function selectJourney(globalId, visitIndex = 0, sampleIndex = 0) {
  stopReplay();
  state.selectedId = globalId;
  state.journey = await getJson(`/api/vehicles/${encodeURIComponent(globalId)}`);
  state.visitIndex = visitIndex;
  state.sampleIndex = sampleIndex;
  renderVehicles();
  renderJourney();
  selectVisit(visitIndex, sampleIndex);
}

function markerIcon(sequence, active = false) {
  return L.divIcon({
    className: `step-marker${active ? " active" : ""}`,
    html: String(sequence),
    iconSize: [28, 28],
  });
}

function renderJourney() {
  routeLayer.clearLayers();
  state.markers = [];
  const journey = state.journey;
  elements.title.textContent = `Vehicle ${shortId(journey.global_id)}`;
  elements.meta.textContent = `${journey.visit_count} observed visits across ${journey.camera_count} predicted cameras`;
  elements.replay.disabled = journey.visits.length < 2;
  const points = journey.visits.map((visit) => [visit.position.latitude, visit.position.longitude]);
  if (points.length > 1) {
    L.polyline(points, { color: "#ffd166", weight: 3, dashArray: "8 7", opacity: .9 })
      .bindTooltip("Interpolated straight segments")
      .addTo(routeLayer);
  }
  journey.visits.forEach((visit) => {
    const marker = L.marker([visit.position.latitude, visit.position.longitude], {
      icon: markerIcon(visit.sequence),
      zIndexOffset: 100 + visit.sequence,
    }).bindTooltip(`${visit.sequence}. ${visit.camera} · ${seconds(visit.first_observed_s)}`);
    marker.on("click", () => selectVisit(visit.sequence - 1));
    marker.addTo(routeLayer);
    state.markers.push(marker);
  });
  if (points.length) map.fitBounds(points, { padding: [90, 90], maxZoom: 20 });

  elements.timeline.className = "timeline";
  elements.timeline.replaceChildren();
  journey.visits.forEach((visit, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "visit";
    const heading = document.createElement("strong");
    const number = document.createElement("span");
    number.className = "visit-number";
    number.textContent = visit.sequence;
    heading.append(number, document.createTextNode(visit.camera));
    const detail = document.createElement("span");
    detail.className = "visit-details";
    detail.textContent = `Observed ${seconds(visit.first_observed_s)} · tracklet ${visit.tracklet_key.split("/").at(-1)}`;
    const link = document.createElement("span");
    link.className = "link-details";
    link.textContent = visit.incoming_link
      ? `Linked at ${visit.incoming_link.appearance_similarity.toFixed(3)} appearance similarity (uncalibrated)`
      : "Founding observation · independent RoadEye ID";
    button.append(heading, detail, link);
    button.addEventListener("click", () => selectVisit(index));
    elements.timeline.append(button);
  });
}

function selectVisit(index, sampleIndex = 0) {
  if (!state.journey) return;
  state.visitIndex = index;
  state.sampleIndex = sampleIndex;
  document.querySelectorAll(".visit").forEach((row, rowIndex) => row.classList.toggle("selected", rowIndex === index));
  state.markers.forEach((marker, markerIndex) => marker.setIcon(markerIcon(markerIndex + 1, markerIndex === index)));
  const visit = state.journey.visits[index];
  map.panTo([visit.position.latitude, visit.position.longitude]);
  renderSampleTabs();
  renderEvidence();
}

function renderSampleTabs() {
  elements.sampleTabs.replaceChildren();
  const samples = state.journey.visits[state.visitIndex].evidence_samples;
  samples.forEach((sample, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `Frame ${sample.frame}`;
    button.classList.toggle("selected", index === state.sampleIndex);
    button.addEventListener("click", () => {
      state.sampleIndex = index;
      renderSampleTabs();
      renderEvidence();
    });
    elements.sampleTabs.append(button);
  });
}

function figure(url, alt, caption) {
  const root = document.createElement("figure");
  root.className = "evidence-figure";
  const image = document.createElement("img");
  image.src = url;
  image.alt = alt;
  const text = document.createElement("figcaption");
  text.textContent = caption;
  root.append(image, text);
  return root;
}

function renderEvidence() {
  const visit = state.journey.visits[state.visitIndex];
  const sample = visit.evidence_samples[state.sampleIndex];
  elements.evidenceTitle.textContent = `${visit.camera} · ${seconds(sample.time_s)} · observed frame ${sample.frame}`;
  elements.evidenceContent.className = "evidence-content";
  elements.evidenceContent.replaceChildren(
    figure(
      sample.crop_url,
      `Vehicle crop at ${visit.camera}, frame ${sample.frame}`,
      `Model input crop · SHA-256 ${sample.crop_sha256.slice(0, 12)}…`,
    ),
    figure(
      sample.source_frame_url,
      `Source frame at ${visit.camera}, frame ${sample.frame}`,
      `Source frame with predicted baseline box · score ${sample.baseline_score.value.toFixed(2)} (${sample.baseline_score.kind.replaceAll("_", " ")}; not a probability)`,
    ),
  );
  if (sample.plate_prediction) {
    const plate = document.createElement("div");
    plate.className = "plate-evidence-note";
    const title = document.createElement("strong");
    title.textContent = `Predicted plate: ${sample.plate_prediction.predicted_plate_text}`;
    const notice = document.createElement("span");
    notice.textContent = `OCR ${sample.plate_prediction.ocr_score.toFixed(3)} · uncalibrated prediction, not ground truth`;
    plate.append(title, notice);
    elements.evidenceContent.append(plate);
  }
}

function stopReplay() {
  if (state.replayTimer !== null) window.clearInterval(state.replayTimer);
  state.replayTimer = null;
  elements.replay.textContent = "Replay journey";
}

function replay() {
  if (!state.journey || state.journey.visits.length < 2) return;
  stopReplay();
  let index = 0;
  selectVisit(index);
  elements.replay.textContent = "Replaying…";
  state.replayTimer = window.setInterval(() => {
    index += 1;
    if (index >= state.journey.visits.length) {
      stopReplay();
      return;
    }
    selectVisit(index);
  }, 1400);
}

async function start() {
  try {
    state.status = await getJson("/api/status");
    state.analytics = await getJson("/api/analytics");
    state.plateSearch = await getJson("/api/plate-search/status");
    elements.status.textContent = `${state.status.status} | ${state.status.runtime_artifact_integrity} integrity | ${state.status.predicted_link_count} predicted links`;
    elements.status.className = state.status.status === "UNVERIFIED"
      ? "status-chip unverified"
      : "status-chip pass";
    if (state.status.disclosure) {
      elements.disclosure.textContent = state.status.disclosure;
      elements.disclosure.hidden = false;
    }
    renderAnalytics();
    renderPlateSearchStatus();
    drawCameras();
    await loadVehicles();
    if (state.vehicles.length) await selectJourney(state.vehicles[0].global_id);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  }
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await loadVehicles(); } catch (error) { setError(String(error)); }
});
elements.plateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await searchPlates(); } catch (error) { setError(String(error)); }
});
elements.multiOnly.addEventListener("change", async () => {
  try { await loadVehicles(); } catch (error) { setError(String(error)); }
});
elements.replay.addEventListener("click", replay);

start();

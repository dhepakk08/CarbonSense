/* ==========================================================
   CarbonSense — script.js
   Handles: view routing, auth (local demo), activity logging,
   carbon-footprint calculation, the "growth rings" chart,
   AI-style tips, and goal progress.

   NOTE ON THE BACKEND:
   This file talks to the Flask API through the small `api`
   object below. Every api.* method tries a real fetch() to
   /api/... first. Until backend/app.py exists (next build
   step), those calls fail and each method falls back to a
   local calculation / localStorage, so the site stays fully
   usable on its own. Once the backend is running, no HTML/CSS
   changes are needed — the fetch calls just start succeeding.
   ========================================================== */

const API_BASE = "/api";

const STORAGE_KEYS = {
  user: "cs_user",
  activities: "cs_activities",
  goal: "cs_goal",
};

/* Emission factors (kg CO2e per unit).
   Mirrors the constants that will live in backend/carbon_calculator.py
   so results stay consistent once the real API takes over. */
const EMISSION_FACTORS = {
  travel: {
    car_petrol: 0.192,   // per km
    car_diesel: 0.171,   // per km
    bus: 0.105,          // per km
    train: 0.041,        // per km
    flight: 0.255,       // per km
    bike: 0,              // per km
  },
  electricity: 0.82,      // per kWh
  food: {
    meat: 3.3,            // per meal
    dairy: 1.9,           // per meal
    veg: 1.1,             // per meal
    vegan: 0.9,           // per meal
  },
  waste: {
    landfill: 0.58,       // per kg
    recycled: 0.21,       // per kg
    composted: 0.05,      // per kg
  },
};

const CATEGORY_META = {
  travel:      { label: "Travel",      color: "#C1683C" },
  electricity: { label: "Electricity", color: "#D9A441" },
  food:        { label: "Food",        color: "#6B8F71" },
  waste:       { label: "Waste",       color: "#3E4C42" },
};

/* ---------------- state ---------------- */
let state = {
  user: null,
  activities: [],
  goal: null,
};

/* ---------------- tiny API abstraction ---------------- */
const api = {
  async login(name, email) {
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email }),
      });
      if (!res.ok) throw new Error("no backend yet");
      return await res.json();
    } catch (_) {
      // Fallback: local-only "session"
      return { id: `local-${Date.now()}`, name, email };
    }
  },

  async addActivity(entry) {
    try {
      const res = await fetch(`${API_BASE}/activity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(entry),
      });
      if (!res.ok) throw new Error("no backend yet");
      return await res.json();
    } catch (_) {
      // Fallback: calculate locally using the same factors the backend will use
      const co2 = calculateCo2(entry.category, entry);
      const saved = { ...entry, co2, id: `local-${Date.now()}` };
      return saved;
    }
  },

  async getRecommendations(activities) {
    try {
      const res = await fetch(`${API_BASE}/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activities }),
      });
      if (!res.ok) throw new Error("no backend yet");
      return await res.json();
    } catch (_) {
      return generateLocalTips(activities);
    }
  },
};

/* ---------------- carbon calculation (client-side fallback) ---------------- */
function calculateCo2(category, fields) {
  switch (category) {
    case "travel": {
      const factor = EMISSION_FACTORS.travel[fields.mode] ?? 0;
      const distance = parseFloat(fields.distance) || 0;
      return +(factor * distance).toFixed(2);
    }
    case "electricity": {
      const units = parseFloat(fields.units) || 0;
      return +(EMISSION_FACTORS.electricity * units).toFixed(2);
    }
    case "food": {
      const factor = EMISSION_FACTORS.food[fields.mealType] ?? 0;
      const meals = parseFloat(fields.meals) || 0;
      return +(factor * meals).toFixed(2);
    }
    case "waste": {
      const factor = EMISSION_FACTORS.waste[fields.wasteType] ?? 0;
      const weight = parseFloat(fields.weight) || 0;
      return +(factor * weight).toFixed(2);
    }
    default:
      return 0;
  }
}

function generateLocalTips(activities) {
  const totals = computeCategoryTotals(activities);
  const tips = [];

  if (totals.travel > 30) {
    tips.push("Your travel emissions are your biggest contributor — swapping one petrol-car trip a week for a bus or train could save several kg of CO₂e a month.");
  }
  const carKm = activities
    .filter((a) => a.category === "travel" && (a.mode === "car_petrol" || a.mode === "car_diesel"))
    .reduce((s, a) => s + (parseFloat(a.distance) || 0), 0);
  if (carKm >= 20) {
    tips.push(`You've logged ${carKm.toFixed(0)} km by car recently — carpooling twice this week would cut roughly ${(carKm * 0.19 * 0.4).toFixed(1)} kg CO₂e.`);
  }
  if (totals.electricity > 15) {
    tips.push("Electricity use is trending high — switching a few devices to power-saving mode during peak hours can meaningfully lower this category.");
  }
  const meatMeals = activities.filter((a) => a.category === "food" && a.mealType === "meat").length;
  if (meatMeals >= 3) {
    tips.push("You've logged several meat-based meals — one extra plant-based meal a week is one of the highest-impact small changes you can make.");
  }
  if (totals.waste > 5) {
    tips.push("A good share of your waste is going to landfill — sorting out recyclables and compostables could cut this category's footprint by half.");
  }
  if (tips.length === 0) {
    tips.push("Keep logging activities — personalised suggestions get sharper the more data CarbonSense has to work with.");
  }
  return tips.slice(0, 4);
}

/* ---------------- helpers ---------------- */
function computeCategoryTotals(activities) {
  const totals = { travel: 0, electricity: 0, food: 0, waste: 0 };
  activities.forEach((a) => {
    if (totals[a.category] !== undefined) {
      totals[a.category] += a.co2 || 0;
    }
  });
  Object.keys(totals).forEach((k) => (totals[k] = +totals[k].toFixed(2)));
  return totals;
}

function persist() {
  if (state.user) localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(state.user));
  localStorage.setItem(STORAGE_KEYS.activities, JSON.stringify(state.activities));
  if (state.goal) localStorage.setItem(STORAGE_KEYS.goal, JSON.stringify(state.goal));
}

function loadPersisted() {
  try {
    state.user = JSON.parse(localStorage.getItem(STORAGE_KEYS.user));
  } catch (_) { state.user = null; }
  try {
    state.activities = JSON.parse(localStorage.getItem(STORAGE_KEYS.activities)) || [];
  } catch (_) { state.activities = []; }
  try {
    state.goal = JSON.parse(localStorage.getItem(STORAGE_KEYS.goal));
  } catch (_) { state.goal = null; }
}

/* ---------------- growth rings chart (signature visual) ---------------- */
function buildRingsSVG(dataArr, { size = 260, strokeWidth = 14, gap = 6, muted = false } = {}) {
  const center = size / 2;
  const baseRadius = center - strokeWidth;
  const max = Math.max(...dataArr.map((d) => d.value), 1);

  const rings = dataArr
    .map((d, i) => {
      const radius = baseRadius - i * (strokeWidth + gap);
      const circumference = 2 * Math.PI * radius;
      const fraction = muted ? 0 : Math.min(d.value / max, 1);
      const dash = circumference * fraction;
      return `
        <circle cx="${center}" cy="${center}" r="${radius}"
          fill="none" stroke="#D9DACB" stroke-width="${strokeWidth}" opacity="0.5" />
        <circle cx="${center}" cy="${center}" r="${radius}"
          fill="none" stroke="${d.color}" stroke-width="${strokeWidth}"
          stroke-linecap="round"
          stroke-dasharray="${dash} ${circumference}"
          transform="rotate(-90 ${center} ${center})"
          style="transition: stroke-dasharray 0.6s ease;" />
      `;
    })
    .join("");

  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="Emission breakdown by category">${rings}</svg>`;
}

function renderRingsPreview() {
  const el = document.getElementById("ringsPreview");
  if (!el) return;
  const demo = [
    { value: 60, color: CATEGORY_META.food.color },
    { value: 40, color: CATEGORY_META.travel.color },
    { value: 25, color: CATEGORY_META.electricity.color },
    { value: 15, color: CATEGORY_META.waste.color },
  ];
  el.innerHTML = buildRingsSVG(demo, { size: 260 });
}

function renderRingsChart(totals) {
  const el = document.getElementById("ringsChart");
  if (!el) return;
  const hasData = Object.values(totals).some((v) => v > 0);
  const dataArr = Object.keys(CATEGORY_META).map((key) => ({
    value: totals[key] || 0,
    color: CATEGORY_META[key].color,
  }));
  el.innerHTML = buildRingsSVG(dataArr, { size: 260, muted: !hasData });
}

/* ---------------- rendering ---------------- */
function renderDashboard() {
  const totals = computeCategoryTotals(state.activities);
  const totalAll = +Object.values(totals).reduce((a, b) => a + b, 0).toFixed(2);

  document.getElementById("totalCo2").textContent = totalAll;
  document.getElementById("monthLabel").textContent = new Date().toLocaleString("default", { month: "long", year: "numeric" });

  const statSub = document.getElementById("statTrend");
  if (state.activities.length === 0) {
    statSub.textContent = "Log your first activity to start your reading.";
  } else if (state.goal) {
    const pct = Math.round((totalAll / state.goal) * 100);
    statSub.textContent = pct <= 100
      ? `You're at ${pct}% of your ${state.goal} kg CO₂e monthly goal.`
      : `You're ${pct - 100}% over your ${state.goal} kg CO₂e monthly goal.`;
  } else {
    statSub.textContent = `${state.activities.length} activities logged so far.`;
  }

  renderRingsChart(totals);

  const legend = document.getElementById("categoryLegend");
  legend.innerHTML = Object.keys(CATEGORY_META).map((key) => `
    <li>
      <span class="swatch" style="background:${CATEGORY_META[key].color}"></span>
      <span class="legend__label">${CATEGORY_META[key].label}</span>
      <span class="legend__value">${totals[key] || 0} kg</span>
    </li>
  `).join("");

  renderActivityList();
  renderTips();
  renderGoalProgress();
}

function renderActivityList() {
  const list = document.getElementById("activityList");
  if (!state.activities.length) {
    list.innerHTML = `<li class="empty-state">Nothing logged yet — your activity feed will show up here.</li>`;
    return;
  }
  const recent = [...state.activities].reverse().slice(0, 6);
  list.innerHTML = recent.map((a) => `
    <li class="activity-item">
      <div class="activity-item__meta">
        <span class="activity-item__cat">${CATEGORY_META[a.category]?.label || a.category}</span>
        <span class="activity-item__detail">${describeActivity(a)} · ${a.date || "no date"}</span>
      </div>
      <span class="activity-item__co2">${a.co2} kg</span>
    </li>
  `).join("");
}

function describeActivity(a) {
  switch (a.category) {
    case "travel": return `${a.mode?.replace("_", " ")}, ${a.distance} km`;
    case "electricity": return `${a.units} kWh`;
    case "food": return `${a.meals} × ${a.mealType} meal`;
    case "waste": return `${a.weight} kg, ${a.wasteType}`;
    default: return "";
  }
}

async function renderTips() {
  const list = document.getElementById("tipList");
  if (!state.activities.length) {
    list.innerHTML = `<li class="empty-state">Tips appear once there's data to learn from.</li>`;
    return;
  }
  const tips = await api.getRecommendations(state.activities);
  list.innerHTML = tips.map((t) => `<li class="tip-item"><span class="tip-item__icon">🌱</span><span>${t}</span></li>`).join("");
}

function renderGoalProgress() {
  const fill = document.getElementById("goalProgressFill");
  const caption = document.getElementById("goalProgressCaption");
  const tag = document.getElementById("goalStatusTag");
  if (!fill) return;

  const totals = computeCategoryTotals(state.activities);
  const totalAll = +Object.values(totals).reduce((a, b) => a + b, 0).toFixed(2);

  if (!state.goal) {
    fill.style.width = "0%";
    if (caption) caption.textContent = "Set a goal above to see your progress bar.";
    if (tag) tag.textContent = "No goal set";
    return;
  }
  const pct = Math.min(Math.round((totalAll / state.goal) * 100), 100);
  fill.style.width = `${pct}%`;
  if (caption) caption.textContent = `${totalAll} kg of ${state.goal} kg CO₂e used this month (${pct}%).`;
  if (tag) tag.textContent = totalAll <= state.goal ? "On track" : "Over target";
}

/* ---------------- navigation ---------------- */
function showView(name) {
  document.querySelectorAll(".view").forEach((v) => (v.hidden = true));
  const target = document.getElementById(`view-${name}`);
  if (target) target.hidden = false;

  document.querySelectorAll(".navlink").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.nav === name);
  });

  if (name === "dashboard") renderDashboard();
  if (name === "goals") renderGoalProgress();

  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

function updateAuthUI() {
  const hello = document.getElementById("helloUser");
  const logoutBtn = document.getElementById("logoutBtn");
  const loginNavBtn = document.getElementById("loginNavBtn");
  const navlinks = document.getElementById("navlinks");

  if (state.user) {
    hello.hidden = false;
    hello.textContent = `Hi, ${state.user.name.split(" ")[0]}`;
    logoutBtn.hidden = false;
    loginNavBtn.hidden = true;
    navlinks.style.display = "flex";
  } else {
    hello.hidden = true;
    logoutBtn.hidden = true;
    loginNavBtn.hidden = false;
    navlinks.style.display = "none";
  }
}

/* ---------------- event wiring ---------------- */
function wireNav() {
  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const target = el.dataset.nav;
      if (target !== "login" && !state.user) {
        showView("login");
        return;
      }
      showView(target);
    });
  });

  document.getElementById("logoutBtn").addEventListener("click", () => {
    state.user = null;
    localStorage.removeItem(STORAGE_KEYS.user);
    updateAuthUI();
    showView("login");
  });
}

function wireLoginForm() {
  document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const name = form.name.value.trim();
    const email = form.email.value.trim();
    if (!name || !email) return;

    const user = await api.login(name, email);
    state.user = user;
    persist();
    updateAuthUI();
    showView("dashboard");
  });
}

function wireCategoryTabs() {
  document.querySelectorAll("#categoryTabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#categoryTabs .tab").forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      const cat = tab.dataset.cat;
      document.querySelectorAll("[data-cat-fields]").forEach((fieldset) => {
        fieldset.hidden = fieldset.dataset.catFields !== cat;
      });
    });
  });
}

function wireActivityForm() {
  const form = document.getElementById("activityForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const activeTab = document.querySelector("#categoryTabs .tab.is-active");
    const category = activeTab.dataset.cat;
    const fd = new FormData(form);
    const entry = { category, date: fd.get("date") || new Date().toISOString().slice(0, 10) };

    if (category === "travel") { entry.mode = fd.get("mode"); entry.distance = fd.get("distance"); }
    if (category === "electricity") { entry.units = fd.get("units"); }
    if (category === "food") { entry.mealType = fd.get("mealType"); entry.meals = fd.get("meals"); }
    if (category === "waste") { entry.wasteType = fd.get("wasteType"); entry.weight = fd.get("weight"); }

    const saved = await api.addActivity(entry);
    state.activities.push(saved);
    persist();

    const result = document.getElementById("formResult");
    result.textContent = `Saved — ${saved.co2} kg CO₂e added.`;
    form.reset();
    setTimeout(() => { result.textContent = ""; }, 4000);
  });
}

function wireGoalForm() {
  document.getElementById("goalForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const target = parseFloat(new FormData(e.target).get("target"));
    if (!target || target <= 0) return;
    state.goal = target;
    persist();
    document.getElementById("goalResult").textContent = `Goal set to ${target} kg CO₂e / month.`;
    renderGoalProgress();
    setTimeout(() => { document.getElementById("goalResult").textContent = ""; }, 4000);
  });
}

/* ---------------- init ---------------- */
document.addEventListener("DOMContentLoaded", () => {
  loadPersisted();
  wireNav();
  wireLoginForm();
  wireCategoryTabs();
  wireActivityForm();
  wireGoalForm();
  updateAuthUI();
  renderRingsPreview();

  if (state.user) {
    showView("dashboard");
  } else {
    showView("login");
  }
});

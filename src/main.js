import './index.css';

import mainPy from '../main.py?raw';
import constantsPy from '../pycraft/constants.py?raw';
import blocksPy from '../pycraft/blocks.py?raw';
import assetsPy from '../pycraft/assets.py?raw';
import audioPy from '../pycraft/audio.py?raw';
import noisePy from '../pycraft/noise.py?raw';
import biomesPy from '../pycraft/biomes.py?raw';
import mobsPy from '../pycraft/mobs.py?raw';
import worldPy from '../pycraft/world.py?raw';
import physicsPy from '../pycraft/physics.py?raw';
import inventoryPy from '../pycraft/inventory.py?raw';
import inventoryUiPy from '../pycraft/inventory_ui.py?raw';
import rendererPy from '../pycraft/renderer.py?raw';
import lightingPy from '../pycraft/lighting.py?raw';
import storagePy from '../pycraft/storage.py?raw';
import pygameAppPy from '../pycraft/pygame_app.py?raw';
import downloadAssetsPy from '../scripts/download_assets.py?raw';

const MODULES = [
  {path: 'main.py', code: mainPy},
  {path: 'pycraft/constants.py', code: constantsPy},
  {path: 'pycraft/blocks.py', code: blocksPy},
  {path: 'pycraft/inventory.py', code: inventoryPy},
  {path: 'pycraft/inventory_ui.py', code: inventoryUiPy},
  {path: 'pycraft/assets.py', code: assetsPy},
  {path: 'pycraft/audio.py', code: audioPy},
  {path: 'pycraft/noise.py', code: noisePy},
  {path: 'pycraft/biomes.py', code: biomesPy},
  {path: 'pycraft/mobs.py', code: mobsPy},
  {path: 'pycraft/world.py', code: worldPy},
  {path: 'pycraft/physics.py', code: physicsPy},
  {path: 'pycraft/renderer.py', code: rendererPy},
  {path: 'pycraft/lighting.py', code: lightingPy},
  {path: 'pycraft/storage.py', code: storagePy},
  {path: 'pycraft/pygame_app.py', code: pygameAppPy},
  {path: 'scripts/download_assets.py', code: downloadAssetsPy},
];

let selectedIdx = 0;

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

const root = document.getElementById('root');

root.innerHTML = `
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
      <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-4">
        <div class="flex items-center gap-3">
          <div class="grid h-10 w-10 place-items-center rounded-lg bg-emerald-600 font-mono text-lg font-bold text-white">
            Py
          </div>
          <div>
            <h1 class="text-lg font-bold tracking-tight text-white">PyCraft — Full-Scale Minecraft for Pydroid 3</h1>
            <p class="text-xs text-slate-400">Pure Pygame Engine • Full-Scale 16×16 Textures • 3×3 Shaped Crafting • 7 Biomes + Nether</p>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <button id="copy-btn" class="rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-700 active:scale-95">
            Copy Current File
          </button>
          <a href="/pycraft_pydroid.zip" download="pycraft_pydroid.zip" class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 active:scale-95">
            Download Complete Project (.zip)
          </a>
        </div>
      </div>
    </header>

    <main class="mx-auto grid max-w-6xl gap-6 px-5 py-6 lg:grid-cols-12">
      <aside class="space-y-4 lg:col-span-4">
        <div class="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 class="text-xs font-bold uppercase tracking-wider text-emerald-400">Pydroid 3 Setup</h2>
          <ol class="mt-2.5 space-y-2 text-sm text-slate-300">
            <li><span class="font-semibold text-white">1.</span> Download &amp; unzip <code class="rounded bg-slate-800 px-1 text-xs text-emerald-300">pycraft_pydroid.zip</code> on your phone.</li>
            <li><span class="font-semibold text-white">2.</span> Install <code class="rounded bg-slate-800 px-1 text-xs">pygame</code> via Pydroid Pip (pure SDL/Pygame C loader, zero heavy libraries).</li>
            <li><span class="font-semibold text-white">3.</span> Open <code class="rounded bg-slate-800 px-1 text-xs text-emerald-300">main.py</code> in <span class="font-semibold text-white">Pydroid 3</span> and press Play!</li>
          </ol>
        </div>

        <div class="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 class="text-xs font-bold uppercase tracking-wider text-sky-400">Python Modules (${MODULES.length})</h2>
          <div id="file-list" class="mt-2.5 max-h-72 space-y-1 overflow-auto pr-1"></div>
        </div>

        <div class="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h2 class="text-xs font-bold uppercase tracking-wider text-amber-400">Minecraft Features &amp; Engine</h2>
          <ul class="mt-2 space-y-1 text-xs text-slate-300">
            <li>• <span class="font-semibold text-white">Dual-Channel Block Lighting:</span> BFS flood-fill propagation for 0–15 daylight shafts + night torches, glowstone &amp; wall shadows</li>
            <li>• <span class="font-semibold text-white">Shaped 3×3 &amp; 2×2 Crafting + Visual Furnace:</span> Category filters, live recipe ingredient grids, bulk Craft All, and smelting chamber slots</li>
            <li>• <span class="font-semibold text-white">Full-Scale 16×16 Texture Engine:</span> Native C PNG loading via Pygame + greedy-merged 16×16 &amp; 8×8 UV patches without pure-Python overhead</li>
            <li>• <span class="font-semibold text-white">Persistent Inventory Overlay:</span> Tracks collected blocks &amp; tools across saves, with pinned HUD quick-switch &amp; swipeable tabs</li>
            <li>• <span class="font-semibold text-white">High-FPS World &amp; Weather:</span> Culled underground voids, bilinear biome climate, rain/snow/thunderstorms &amp; 2,048-byte chunks</li>
          </ul>
        </div>
      </aside>

      <section class="flex flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70 lg:col-span-8">
        <div class="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-4 py-2.5">
          <span id="active-path" class="font-mono text-xs font-semibold text-emerald-300"></span>
          <span id="status-msg" class="text-xs text-emerald-400"></span>
        </div>
        <pre class="max-h-[74vh] flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed text-slate-200"><code id="code-view"></code></pre>
      </section>
    </main>
  </div>
`;

const fileListEl = document.getElementById('file-list');
const activePathEl = document.getElementById('active-path');
const codeViewEl = document.getElementById('code-view');
const statusEl = document.getElementById('status-msg');

function renderActiveModule() {
  const mod = MODULES[selectedIdx];
  activePathEl.textContent = `${mod.path} (${mod.code.split('\n').length} lines)`;
  codeViewEl.innerHTML = escapeHtml(mod.code);

  fileListEl.innerHTML = '';
  MODULES.forEach((m, idx) => {
    const btn = document.createElement('button');
    const active = idx === selectedIdx;
    btn.className = `w-full rounded-md px-2.5 py-1.5 text-left font-mono text-xs transition ${
      active ? 'bg-emerald-600/25 font-semibold text-emerald-300 ring-1 ring-emerald-500/40' : 'text-slate-300 hover:bg-slate-800'
    }`;
    btn.textContent = m.path;
    btn.addEventListener('click', () => {
      selectedIdx = idx;
      renderActiveModule();
    });
    fileListEl.appendChild(btn);
  });
}

document.getElementById('copy-btn').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(MODULES[selectedIdx].code);
    statusEl.textContent = `Copied ${MODULES[selectedIdx].path}`;
    setTimeout(() => { statusEl.textContent = ''; }, 2200);
  } catch {
    statusEl.textContent = 'Copy unavailable — download the ZIP';
  }
});

renderActiveModule();

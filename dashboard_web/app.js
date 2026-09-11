/* LatamBOT Dashboard — SPA (vanilla JS, sin build step) — port del diseño Claude Design */
const app = document.getElementById('app');

async function api(path, opts) {
  const r = await fetch(path, { credentials: 'same-origin', ...opts });
  if (r.status === 401) return { __unauth: true };
  try { return await r.json(); } catch { return {}; }
}

function toast(msg, ok = true) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + (ok ? 'ok' : 'err');
  setTimeout(() => { t.className = 'toast'; }, 2600);
}
function esc(s) { return (s == null ? '' : String(s)).replace(/"/g, '&quot;').replace(/</g, '&lt;'); }
function initials(name) { return (String(name || '?').replace(/[^\p{L}\p{N} ]/gu, '').trim().split(/\s+/).map(w => w[0]).join('').slice(0, 2) || '?').toUpperCase(); }

/* Logo real del bot (avatar) con fallback a la marca verde */
function logoHTML(src, cls) {
  return src ? `<img class="lb-logo ${cls || ''}" src="${esc(src)}" alt="LatamBOT">`
             : `<div class="lb-mark ${cls || ''}"><i></i></div>`;
}
function botAvatar() { return (window.INFO && window.INFO.avatar) || (window.ME && window.ME.bot && window.ME.bot.avatar) || ''; }

/* Avatar del usuario logueado (URL completa desde /api/me, o fallback a inicial) */
function userAvHTML(user, uname) {
  const url = user && user.avatar;
  if (url) return `<img class="av" src="${esc(url)}" alt="" referrerpolicy="no-referrer">`;
  return `<div class="av">${esc((uname[0] || '?').toUpperCase())}</div>`;
}

/* ---------- Loading ---------- */
function spinnerHTML(texto) { return `<div class="loading"><div class="spinner"></div><span>${esc(texto || 'Cargando…')}</span></div>`; }
function loadingFull(texto) { app.innerHTML = spinnerHTML(texto); }

/* ---------- Arranque / router ---------- */
async function start() {
  loadingFull('Cargando tu panel…');
  const me = await api('/api/me');
  if (me.__unauth || !me.authenticated) return renderLogin();
  renderGuildPicker(me);
}

async function renderLogin() {
  const params = new URLSearchParams(location.search);
  const errMap = {
    forbidden: 'Acceso restringido: por ahora solo el owner puede entrar.',
    state: 'Sesión inválida, probá de nuevo.',
    token: 'No se pudo validar con Discord.',
    discord: 'Error hablando con Discord.',
  };
  const err = params.get('error');
  const info = await api('/api/info').catch(() => ({}));
  window.INFO = info;
  const links = info.links ? `<div class="support">
      <a class="btn kofi sm" href="${info.links.kofi}" target="_blank" rel="noopener">☕ Ko-fi</a>
      <a class="btn patreon sm" href="${info.links.patreon}" target="_blank" rel="noopener">🅿️ Patreon</a>
    </div>` : '';
  app.innerHTML = `<div class="login">
    <div class="ltop">
      ${logoHTML(info.avatar)}
      <b>${esc(info.name || 'LatamBOT')}</b>
      <span class="url">dashboard self-hosted</span>
    </div>
    <div class="lmid">
      <div class="lbox">
        <span class="rail"></span>
        <div class="kick">l!panel</div>
        <h1>Ingresá<br>al panel.</h1>
        <p class="sub">Configurá tu servidor desde el navegador, sin escribir comandos.</p>
        ${err ? `<div class="err">${esc(errMap[err] || 'Error: ' + err)}</div>` : ''}
        <a class="btn primary" id="login-btn" href="/api/login?join=1">Continuar con Discord</a>
        <label class="joinopt"><input type="checkbox" id="join-chk" checked><span>Unirme a la comunidad de LatamBOT <small>(soporte, novedades y beneficios extra)</small></span></label>
        <div class="join-benefits" id="join-benefits" hidden>
          <div class="jb-title">Si te unís a la comunidad, desbloqueás:</div>
          <ul>
            <li><b>+25</b> usos de IA (<code>l!ask</code>) por día</li>
            <li><b>+5</b> búsquedas web / imágenes / noticias por día</li>
            <li><b>+25%</b> más monedas en <code>l!daily</code></li>
            <li>Soporte directo, novedades y anuncios del bot</li>
          </ul>
          <div class="jb-hint">Podés salir cuando quieras. Es gratis.</div>
        </div>
        <div class="or">o con código</div>
        <div class="code-row">
          <input id="code-input" maxlength="6" placeholder="Código del bot" autocomplete="off" aria-label="Código del bot">
          <button id="code-btn" class="btn">Entrar</button>
        </div>
        <div id="code-err" class="err"></div>
        <p class="hint">El bot te da tu código con <code>l!panel</code>.</p>
        ${links}
      </div>
    </div>
    <div class="lfoot"><span>es · pt · en</span><span class="dot">·</span><span>hecho en latam</span></div>
  </div>`;
  const joinChk = document.getElementById('join-chk');
  const loginBtn = document.getElementById('login-btn');
  const joinBenefits = document.getElementById('join-benefits');
  const syncJoin = () => {
    const on = !!(joinChk && joinChk.checked);
    if (loginBtn) loginBtn.href = '/api/login?join=' + (on ? '1' : '0');
    if (joinBenefits) joinBenefits.hidden = on; // si lo desactiva, mostramos beneficios
  };
  if (joinChk) {
    joinChk.addEventListener('change', syncJoin);
    syncJoin();
  }
  const input = document.getElementById('code-input');
  input.addEventListener('input', () => { input.value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, ''); });
  const go = async () => {
    const code = input.value.trim();
    if (code.length < 4) return;
    document.getElementById('code-btn').disabled = true;
    const res = await api('/api/code', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) });
    document.getElementById('code-btn').disabled = false;
    if (res.ok) start();
    else document.getElementById('code-err').textContent = 'Código inválido o vencido.';
  };
  document.getElementById('code-btn').onclick = go;
  input.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
}

/* ---------- Server picker ---------- */
function rankBadge(r) {
  if (r === 'Dueño') return '<span class="pro">OWNER</span>';
  if (r === 'Admin') return '<span class="pro">ADMIN</span>';
  if (r === 'Owner Bot') return '<span class="pro">DEV</span>';
  return '';
}
function renderGuildPicker(me) {
  window.ME = me;
  const uname = (me.user && me.user.username) || 'staff';
  const cards = me.guilds.map(g => {
    const color = g.color || '#3dbd78';
    const ic = g.icon ? `<img src="${g.icon}" alt="">`
      : `<div class="ph" style="background:${color}1f;color:${color};border:1px solid ${color}55">${esc(initials(g.name))}</div>`;
    return `<button class="guild-card" data-id="${g.id}">
      <div class="gc-top">${ic}
        <div class="gc-name">
          <strong>${esc(g.name)} ${rankBadge(g.rank)}</strong>
          <small>${g.members ? g.members + ' miembros' : (g.rank || 'Staff')}</small>
        </div>
      </div>
      <div class="cta">Configurar →</div>
    </button>`;
  }).join('');
  app.innerHTML = `<div class="pick-wrap">
    <div class="pick-top">
      ${logoHTML(botAvatar())}<b>${esc((me.bot && me.bot.name) || 'LatamBOT')}</b>
      <div class="pick-user">${userAvHTML(me.user, uname)}<span class="pick-uname">${esc(uname)}</span></div>
      <button class="btn ghost sm out" id="logout">Cerrar sesión</button>
    </div>
    <h2>Elegí un servidor</h2>
    <p class="sub">Configurá cualquiera de tus comunidades donde LatamBOT está presente.</p>
    <div class="guild-grid">
      ${cards}
      <a class="guild-add" href="/api/login"><div class="plus">+</div><span>Agregar a otro servidor</span></a>
    </div>
    ${cards ? '' : '<p class="muted" style="margin-top:20px">No hay servidores configurables. ¿El bot está en tu server y sos admin?</p>'}
  </div>`;
  document.getElementById('logout').onclick = async () => { await api('/api/logout', { method: 'POST' }); start(); };
  document.querySelectorAll('.guild-card').forEach(b => b.onclick = () => openGuild(b.dataset.id, me));
}

/* ---------- Panel de un servidor ---------- */
const SECTION_CMD = {
  canales: 'l!canales', sistemas: 'l!setup', xp: 'l!rank', roles: 'l!autorol', ia: 'l!ask',
  bienvenida: 'l!bienvenida', verificacion: 'l!verificar', triggers: 'l!trigger', comandos: 'l!setup',
  mascotas: 'l!mascota', honeypot: 'l!honeypot', stats_voice: 'l!stats', confesiones: 'l!confesar', apariencia: 'l!setup',
  reaction_roles: '/reactionrole',
  autoreaccion: 'panel',
  home: 'l!panel', downloads: 'l!dl', embed: 'l!embed',
};

async function openGuild(gid, me) {
  loadingFull('Abriendo el servidor…');
  const data = await api('/api/guild/' + gid);
  if (data.__unauth) return renderLogin();
  if (data.error) { toast('No autorizado para ese servidor', false); renderGuildPicker(me); return; }
  window.GDATA = data; window.GID = gid; window.GME = me;
  applyAppearance(data.config);

  const groups = [
    { label: 'Principal', items: [
      { id: 'home', label: 'Inicio' },
      { id: 'downloads', label: 'Descargas' },
      { id: 'embed', label: 'Constructor de embeds' },
    ]},
    { label: 'Configuración', items: data.schema.map(s => ({ id: s.id, label: s.label, premium: !!s.premium })) },
  ];
  const nav = groups.map(grp =>
    `<div class="nav-group">${esc(grp.label)}</div>` +
    grp.items.map(it => `<button class="navitem" data-view="${it.id}">
        <span class="dot"></span><span class="nm">${esc(it.label)}</span>
        ${it.premium ? '<span class="pro">PRO</span>' : ''}
        <span class="cmd" hidden></span>
      </button>`).join('')
  ).join('');

  const g = data.guild;
  const color = g.color || '#3dbd78';
  const sIcon = g.icon ? `<img src="${g.icon}" alt="">`
    : `<div class="ph" style="background:${color}1f;color:${color};border:1px solid ${color}55">${esc(initials(g.name))}</div>`;
  const uname = (me.user && me.user.username) || 'staff';
  const links = me.links || (data.links) || null;

  app.innerHTML = `<div class="shell">
    <div class="backdrop" id="backdrop"></div>
    <aside class="sidebar" id="sidebar">
      <div class="side-brand">${logoHTML(botAvatar())}<b>${esc((me.bot && me.bot.name) || 'LatamBOT')}</b></div>
      <div class="side-server">${sIcon}<div class="ss-name"><strong>${esc(g.name)}</strong><span>Servidor</span></div></div>
      <nav class="navwrap">${nav}</nav>
      ${(g.premium ? '' : `<div class="side-premium">
        <div class="sp-t">LatamBOT Premium</div>
        <div class="sp-d">Desbloqueá IA, honeypot y descargas sin límite.</div>
        <a class="btn primary" href="${links ? links.kofi : '#'}" target="_blank" rel="noopener">Mejorar</a>
      </div>`)}
      <div class="side-foot">
        ${userAvHTML(me.user, uname)}
        <div class="who">${esc(uname)}<span>${me.user && me.user.is_owner ? 'Owner' : 'Administrador'}</span></div>
        <button class="out" id="side-logout" title="Salir">⏻</button>
      </div>
    </aside>
    <main class="main">
      <header class="mainhead" id="mainhead"></header>
      <div class="scrollarea" id="main-content"></div>
      <div class="savebar" id="savebar" hidden>
        <div class="sb-inner">
          <span class="sb-msg">Tenés cambios sin guardar.</span>
          <div class="sb-actions">
            <button class="btn ghost" id="sb-discard">Descartar</button>
            <button class="btn primary" id="sb-save">Guardar cambios</button>
          </div>
        </div>
      </div>
    </main>
  </div>`;

  document.getElementById('side-logout').onclick = async () => { await api('/api/logout', { method: 'POST' }); start(); };
  document.getElementById('backdrop').onclick = closeSidebar;
  document.getElementById('sb-discard').onclick = () => showView(CUR_VIEW);
  document.getElementById('sb-save').onclick = saveCurrent;
  document.querySelectorAll('.navitem[data-view]').forEach(b => b.onclick = () => { showView(b.dataset.view); closeSidebar(); });
  showView('home');
}

function closeSidebar() {
  const s = document.getElementById('sidebar'); if (s) s.classList.remove('open');
  const b = document.getElementById('backdrop'); if (b) b.classList.remove('show');
}
function openSidebar() {
  const s = document.getElementById('sidebar'); if (s) s.classList.add('open');
  const b = document.getElementById('backdrop'); if (b) b.classList.add('show');
}

let CUR_VIEW = 'home';
let DIRTY = false;   // hay cambios sin guardar en la sección actual

/* header por sección: breadcrumb + título + cmd badge + sync pill */
function renderHeader(title, cmd) {
  const g = GDATA.guild;
  const mh = document.getElementById('mainhead');
  mh.innerHTML = `<button class="menu-btn" id="menu-btn">☰</button>
    <div style="min-width:0">
      <div class="mh-crumb">${esc(g.name)} / ${esc(title)}</div>
      <div class="mh-title"><h1>${esc(title)}</h1>${cmd ? `<span class="mh-cmd">${esc(cmd)}</span>` : ''}</div>
    </div>
    <div class="sync-pill" id="sync-pill"><span class="sp-dot"></span><span class="sp-txt">Sincronizado</span></div>`;
  document.getElementById('menu-btn').onclick = openSidebar;
}
function setSync(state) {
  const p = document.getElementById('sync-pill'); if (!p) return;
  p.className = 'sync-pill' + (state === 'dirty' ? ' dirty' : state === 'saving' ? ' saving' : '');
  p.querySelector('.sp-txt').textContent = state === 'dirty' ? 'Sin guardar' : state === 'saving' ? 'Guardando…' : 'Sincronizado';
}
function showSaveBar(show) {
  const sb = document.getElementById('savebar'); if (sb) sb.hidden = !show;
}

async function showView(view) {
  // Si hay cambios sin guardar en la sección actual, guardarlos antes de irse.
  // (Antes se descartaban en silencio: configurabas, cambiabas de sección y se perdía.)
  if (DIRTY && CUR_VIEW !== view) {
    try { await saveCurrent(); } catch (e) { /* si falla, saveCurrent ya avisa */ }
  }
  CUR_VIEW = view;
  document.querySelectorAll('.navitem').forEach(b => {
    const on = b.dataset.view === view;
    b.classList.toggle('active', on);
    const cmd = b.querySelector('.cmd');
    if (cmd) { cmd.hidden = !(on && !b.querySelector('.pro')); cmd.textContent = on ? (SECTION_CMD[view] || '') : ''; }
  });
  showSaveBar(false); setSync('clean');
  const m = document.getElementById('main-content');
  m.scrollTop = 0;

  if (view === 'home') { renderHeader('Inicio', SECTION_CMD.home); return renderHome(); }
  if (view === 'downloads') { renderHeader('Descargas', SECTION_CMD.downloads); return loadDownloads(GID, GME, GDATA); }
  if (view === 'embed') { renderHeader('Constructor de embeds', SECTION_CMD.embed); return renderEmbedBuilder(); }
  const sec = GDATA.schema.find(s => s.id === view);
  if (!sec) return;
  renderHeader(sec.label, SECTION_CMD[sec.id]);
  if (sec.premium && !(GDATA.guild && GDATA.guild.premium)) { m.innerHTML = lockedCard(sec); return; }
  m.innerHTML = `<div class="content">${sectionHelp(sec)}${renderSection(sec, GDATA)}</div>`;
  wireSections(GID, GDATA, GME);
}

const SECTION_HELP = {
  verificacion: 'Protegé tu server: activá la verificación, elegí el canal donde aparece el botón y el rol que se da al verificarse. Con eso alcanza.',
  roles: 'Autorol: el rol que reciben los nuevos miembros al entrar. Verificado: el rol que se da al pasar la verificación. Staff: roles con permisos del bot.',
  reaction_roles: 'Elegí el canal y un mensaje reciente (sin pegar IDs). Sumá emoji → rol y aplicá. El bot reacciona en ese mensaje y entrega el rol. Tiene que estar por encima de esos roles.',
  autoreaccion: 'El bot reacciona solo cuando el mensaje matchea. Podés filtrar por texto, regex o adjunto, por un canal o todo el server. Máx. 15 reglas y 3 emojis por regla.',
  apariencia: 'Personalizá el color de acento y el tema del dashboard para este servidor.',
};
function sectionHelp(sec) {
  return SECTION_HELP[sec.id] ? `<div class="sec-help">💡 ${esc(SECTION_HELP[sec.id])}</div>` : '';
}

function lockedCard(sec) {
  const l = (window.INFO && window.INFO.links) || (GME && GME.links) || { kofi: '#', patreon: '#' };
  return `<div class="content"><div class="locked">
    <div class="lock-badge">🔒 Función Premium</div>
    <h3>${esc(sec.label)}</h3>
    <p>Esta sección es parte de <strong>LatamBOT Premium</strong>. Apoyá el proyecto para desbloquear <strong>${esc(sec.label)}</strong>, la apariencia personalizable y perks extra.</p>
    <div class="support">
      <a class="btn kofi" href="${l.kofi}" target="_blank" rel="noopener">☕ Apoyar en Ko-fi</a>
      <a class="btn patreon" href="${l.patreon}" target="_blank" rel="noopener">🅿️ Patreon</a>
    </div>
    <p class="muted" style="margin-top:14px;font-size:12.5px">Premium se activa cuando el dueño del servidor tiene un tier de apoyo activo.</p>
  </div></div>`;
}

function applyAppearance(cfg) {
  const root = document.documentElement;
  const accent = cfg && cfg.dash_accent;
  if (accent && /^#[0-9a-fA-F]{6}$/.test(accent)) {
    root.style.setProperty('--accent', accent);
    root.style.setProperty('--accent-ghost', accent + '22');
  } else { root.style.removeProperty('--accent'); root.style.removeProperty('--accent-ghost'); }
  const theme = cfg && cfg.dash_theme;
  if (theme === 'oscuro') root.dataset.theme = 'dark';
  else if (theme === 'claro') root.dataset.theme = 'light';
  else delete root.dataset.theme;
}

/* ---------- Home ---------- */
function statCard(icon, value, label) { return `<div class="stat-card"><div class="stat-ic">${icon}</div><div class="stat-num">${value}</div><div class="stat-lbl">${label}</div></div>`; }
function quickCard(view, icon, label, desc) { return `<button class="quick-card" data-go="${view}"><span class="qc-ic">${icon}</span><strong>${label}</strong><small>${desc || ''}</small></button>`; }
function renderHome() {
  const g = GDATA.guild;
  const main = document.getElementById('main-content');
  main.innerHTML = `<div class="content">
    <div class="notice-banner">
      <b>Aviso · YouTube</b>
      Las descargas de YouTube están inestables: el proxy de la Pi dejó de andar bien, así que ahora salen directo desde el servidor. TikTok, Instagram y el resto siguen igual.
    </div>
    <div class="home-hero">
      ${g.icon ? `<img class="home-icon" src="${g.icon}" alt="">` : ''}
      <div><span class="kicker">✨ Dashboard del servidor</span><h2>${esc(g.name)}</h2>
        <p class="muted">Configurá tu servidor desde acá, sin escribir comandos.</p></div>
    </div>
    <div class="stats-grid">
      ${statCard('👥', g.members ?? '—', 'Miembros')}
      ${statCard('#', (g.text_channels ?? 0) + '/' + (g.voice_channels ?? 0), 'Canales T/V')}
      ${statCard('🛡️', g.roles ?? '—', 'Roles')}
      ${statCard('📥', g.downloads ?? 0, 'Descargas')}
    </div>
    <h3 class="block-title">Empezá por acá</h3>
    <div class="quick-grid">
      ${quickCard('canales', '📍', 'Canales', 'General, logs, staff y más')}
      ${quickCard('sistemas', '🔧', 'Sistemas', 'Anti-spam, automod, logs')}
      ${quickCard('bienvenida', '👋', 'Bienvenida', 'Mensaje e imagen de entrada')}
      ${quickCard('verificacion', '✅', 'Verificación', 'Protegé tu server')}
      ${quickCard('roles', '👥', 'Roles', 'Autorol, staff, verificado')}
      ${quickCard('downloads', '📥', 'Descargas', 'Archivos de l!dl / l!mp3')}
    </div></div>`;
  main.querySelectorAll('[data-go]').forEach(b => b.onclick = () => showView(b.dataset.go));
}

/* ---------- Descargas ---------- */
async function loadDownloads(gid, me, data) {
  const main = document.getElementById('main-content');
  main.innerHTML = spinnerHTML('Cargando descargas…');
  const res = await api('/api/guild/' + gid + '/downloads');
  if (res.__unauth) return renderLogin();
  const items = (res.downloads || []);
  const rows = items.map(d => {
    const fecha = d.ts ? new Date(d.ts).toLocaleString() : '';
    const tipo = d.type === 'mp3' ? '🎵 MP3' : '🎬 Video';
    return `<tr><td>${tipo}</td><td class="fn">${esc(d.filename || '—')}</td><td>${esc(d.user_name || d.user_id || '')}</td>
      <td>${d.size_mb ? d.size_mb + ' MB' : ''}</td><td class="dt">${esc(fecha)}</td>
      <td><a class="btn sm" href="${esc(d.url)}" target="_blank" rel="noopener">Abrir</a></td></tr>`;
  }).join('');
  main.innerHTML = `<div class="content">
    <div class="notice-banner">
      <b>Aviso · YouTube</b>
      Las descargas de YouTube están inestables: el proxy de la Pi dejó de andar bien, así que ahora salen directo desde el servidor. TikTok, Instagram y el resto siguen igual.
    </div>
    <p class="sec-desc">Todo lo que se guardó en este servidor con <span class="mono" style="color:var(--lila)">l!dl</span> y <span class="mono" style="color:var(--lila)">l!mp3</span>. <span class="count">${items.length}</span></p>
    ${items.length ? `<div class="table-wrap"><table class="dl-table">
      <thead><tr><th>Tipo</th><th>Archivo</th><th>Usuario</th><th>Tamaño</th><th>Fecha</th><th></th></tr></thead>
      <tbody>${rows}</tbody></table></div>` : '<p class="muted">Todavía no hay descargas registradas en este servidor.</p>'}
  </div>`;
}

/* ---------- Constructor de embeds ---------- */
function ebVal(id) { const e = document.getElementById(id); return e ? e.value : ''; }
function renderEmbedBuilder() {
  const m = document.getElementById('main-content');
  m.innerHTML = `<div class="content">
    <p class="sec-desc">Armá un embed y enviálo a un canal (bienvenidas, anuncios, reglas…).</p>
    <div class="embed-builder">
      <div class="eb-form">
        <label>Canal destino</label>${lbSelect('eb-channel', GDATA.channels || [], '', { kind: 'channel', placeholder: '— elegí un canal —' })}
        <label>Título</label><input id="eb-title" maxlength="256" placeholder="Título del embed">
        <label>Descripción</label><textarea id="eb-desc" maxlength="4000" placeholder="Texto del embed"></textarea>
        <label>Color</label><input type="color" id="eb-color" value="#3dbd78">
        <label>Imagen (URL)</label><input id="eb-image" placeholder="https://...">
        <label>Footer</label><input id="eb-footer" maxlength="200" placeholder="Texto del pie">
        <button class="btn primary" id="eb-send">Enviar al canal</button>
      </div>
      <div class="eb-preview"><span class="muted mono" style="font-size:12px">Vista previa</span><div class="discord-embed" id="eb-prev"></div></div>
    </div></div>`;
  ['eb-title', 'eb-desc', 'eb-color', 'eb-image', 'eb-footer'].forEach(id => document.getElementById(id).addEventListener('input', renderEmbedPreview));
  renderEmbedPreview();
  document.getElementById('eb-send').onclick = sendEmbed;
}
function renderEmbedPreview() {
  const prev = document.getElementById('eb-prev');
  prev.style.borderLeftColor = ebVal('eb-color') || '#3dbd78';
  prev.innerHTML = `${ebVal('eb-title') ? `<div class="de-title">${esc(ebVal('eb-title'))}</div>` : ''}
    ${ebVal('eb-desc') ? `<div class="de-desc">${esc(ebVal('eb-desc')).replace(/\n/g, '<br>')}</div>` : ''}
    ${ebVal('eb-image') ? `<img class="de-img" src="${esc(ebVal('eb-image'))}" alt="">` : ''}
    ${ebVal('eb-footer') ? `<div class="de-footer">${esc(ebVal('eb-footer'))}</div>` : ''}
    ${!(ebVal('eb-title') || ebVal('eb-desc') || ebVal('eb-image')) ? '<span class="muted">El embed está vacío…</span>' : ''}`;
}
async function sendEmbed() {
  const btn = document.getElementById('eb-send'); btn.disabled = true;
  const res = await api('/api/guild/' + GID + '/action', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'embed_send', channel: lbSelValue('eb-channel'),
      embed: { title: ebVal('eb-title'), description: ebVal('eb-desc'), color: ebVal('eb-color'), image: ebVal('eb-image'), footer: ebVal('eb-footer') } }),
  });
  btn.disabled = false;
  toast(res.ok ? 'Embed enviado ✓' : ('Error: ' + (res.error || '')), !!res.ok);
}

/* ---------- Campos ---------- */
function optList(list, val) { return list.map(o => `<option value="${o.id}" ${String(o.id) === String(val) ? 'selected' : ''}>${esc(o.name)}</option>`).join(''); }

/* Selectores buscables / dinamicos */
function lbSelect(id, options, value, opts = {}) {
  const placeholder = opts.placeholder || '— ninguno —';
  const emptyValue = opts.emptyValue == null ? '' : String(opts.emptyValue);
  const kind = opts.kind || 'plain'; // plain | channel | role | message
  const list = Array.isArray(options) ? options : [];
  const items = [{ id: emptyValue, name: placeholder, _empty: true }, ...list.map(o => ({
    id: String(o.id),
    name: String(o.name || o.label || o.id),
    color: o.color || '',
    preview: o.preview || '',
  }))];
  const curVal = value == null || value === '' ? emptyValue : String(value);
  const cur = items.find(o => String(o.id) === curVal) || items[0];
  const labelHtml = lbSelLabel(cur, kind, placeholder);
  const optsHtml = items.map(o => {
    const active = String(o.id) === String(cur.id) ? ' active' : '';
    return `<button type="button" class="lb-sel-opt${active}" data-v="${esc(o.id)}" data-t="${esc((o.name || '').toLowerCase())}">${lbSelLabel(o, kind, placeholder)}</button>`;
  }).join('');
  return `<div class="lb-sel" id="${id}" data-value="${esc(cur.id)}" data-kind="${esc(kind)}" data-empty="${esc(emptyValue)}">
    <button type="button" class="lb-sel-btn" aria-haspopup="listbox">${labelHtml}</button>
    <div class="lb-sel-drop" hidden>
      <input type="search" class="lb-sel-search" placeholder="Buscar..." autocomplete="off">
      <div class="lb-sel-list">${optsHtml || '<div class="lb-sel-empty">Sin opciones</div>'}</div>
    </div>
  </div>`;
}
function lbSelLabel(o, kind, placeholder) {
  if (!o || o._empty || o.id === '') return `<span class="lb-sel-placeholder">${esc(placeholder)}</span>`;
  if (kind === 'channel') return `<span class="lb-sel-hash">#</span><span>${esc(o.name)}</span>`;
  if (kind === 'role') {
    const dot = o.color ? `<span class="lb-sel-dot" style="background:${esc(o.color)}"></span>` : '';
    return `${dot}<span>@${esc(o.name)}</span>`;
  }
  return `<span>${esc(o.name)}</span>`;
}
function lbSelValue(id) {
  const el = document.getElementById(id);
  if (!el) return '';
  const v = el.dataset.value;
  const empty = el.dataset.empty == null ? '' : el.dataset.empty;
  return v === empty ? '' : (v || '');
}
function lbSelSetOptions(id, options, value, opts = {}) {
  const el = document.getElementById(id);
  if (!el) return;
  const kind = opts.kind || el.dataset.kind || 'plain';
  const placeholder = opts.placeholder || '— ninguno —';
  const emptyValue = opts.emptyValue == null ? (el.dataset.empty || '') : String(opts.emptyValue);
  const wrap = document.createElement('div');
  wrap.innerHTML = lbSelect(id, options, value, { kind, placeholder, emptyValue });
  el.replaceWith(wrap.firstElementChild);
}
function lbSelCloseAll(except) {
  document.querySelectorAll('.lb-sel.open').forEach(s => {
    if (except && s === except) return;
    s.classList.remove('open');
    const drop = s.querySelector('.lb-sel-drop');
    if (drop) drop.hidden = true;
  });
}
document.addEventListener('click', e => {
  const sel = e.target.closest('.lb-sel');
  if (!sel) { lbSelCloseAll(); return; }
  const btn = e.target.closest('.lb-sel-btn');
  const opt = e.target.closest('.lb-sel-opt');
  const search = e.target.closest('.lb-sel-search');
  if (btn) {
    const open = !sel.classList.contains('open');
    lbSelCloseAll(sel);
    sel.classList.toggle('open', open);
    const drop = sel.querySelector('.lb-sel-drop');
    if (drop) {
      drop.hidden = !open;
      if (open) {
        const inp = drop.querySelector('.lb-sel-search');
        if (inp) { inp.value = ''; inp.focus(); drop.querySelectorAll('.lb-sel-opt').forEach(o => { o.style.display = ''; }); }
      }
    }
    return;
  }
  if (opt) {
    const v = opt.dataset.v;
    sel.dataset.value = v;
    const btnEl = sel.querySelector('.lb-sel-btn');
    if (btnEl) btnEl.innerHTML = opt.innerHTML;
    sel.querySelectorAll('.lb-sel-opt').forEach(o => o.classList.toggle('active', o === opt));
    lbSelCloseAll();
    sel.dispatchEvent(new CustomEvent('lbchange', { bubbles: true, detail: { value: v } }));
    markDirty();
    return;
  }
  if (search) return;
});
document.addEventListener('input', e => {
  if (!e.target.classList.contains('lb-sel-search')) return;
  const q = (e.target.value || '').toLowerCase();
  const list = e.target.closest('.lb-sel-drop')?.querySelectorAll('.lb-sel-opt') || [];
  list.forEach(o => { o.style.display = (o.dataset.t || '').includes(q) ? '' : 'none'; });
});

function fieldControl(f, value, data) {
  const id = 'f_' + f.key;
  switch (f.type) {
    case 'toggle': return `<label class="switch"><input type="checkbox" id="${id}" ${value ? 'checked' : ''}><span></span></label>`;
    case 'number': return `<input type="number" id="${id}" value="${value ?? ''}" ${f.min != null ? `min="${f.min}"` : ''} ${f.max != null ? `max="${f.max}"` : ''}>`;
    case 'text': return `<input type="text" id="${id}" maxlength="${f.maxlen || 100}" value="${esc(value)}">`;
    case 'textarea': return `<textarea id="${id}" maxlength="${f.maxlen || 1000}">${esc(value)}</textarea>`;
    case 'color': return `<input type="color" id="${id}" value="${/^#[0-9a-fA-F]{6}$/.test(value || '') ? value : '#3dbd78'}">`;
    case 'select': return lbSelect(id, (f.options || []).map(o => ({ id: o, name: o })), value, { placeholder: 'Elegí…', emptyValue: '' });
    case 'channel': return lbSelect(id, data.channels, value, { kind: 'channel', placeholder: '— ningún canal —' });
    case 'role': return lbSelect(id, data.roles, value, { kind: 'role', placeholder: '— ningún rol —' });
    case 'roles': return multiCheck(id, data.roles.map(r => ({ value: r.id, label: r.name, color: r.color })), value);
    case 'channels': return multiCheck(id, data.channels.map(c => ({ value: c.id, label: '#' + c.name })), value);
    case 'multiselect': return multiCheck(id, (f.options || []).map(o => ({ value: o, label: o })), value);
    case 'commands': return multiCheck(id, (data.commands || []).map(c => ({ value: c, label: c })), value);
    case 'kvlist': return kvEditor(id, value || {});
    case 'taglist': return tagEditor(id, value || []);
    case 'readonly': return `<span class="ro">${esc(value ?? '—')}</span>`;
    default: return '';
  }
}

function multiCheck(id, options, selected) {
  const sel = new Set((selected || []).map(String));
  const big = options.length > 12;
  const search = big ? `<input class="mc-search" placeholder="🔍 Buscar..." oninput="mcFilter('${id}', this.value)">` : '';
  const count = (selected || []).length;
  const rows = options.map(o => {
    const on = sel.has(String(o.value));
    const dot = o.color ? `<span class="mc-dot" style="background:${o.color}"></span>` : '';
    return `<label class="mc-item ${on ? 'on' : ''}" data-t="${esc(String(o.label || '').toLowerCase())}">
      <input type="checkbox" value="${esc(o.value)}" ${on ? 'checked' : ''}>
      <span class="mc-box"></span>${dot}<span class="mc-lbl">${esc(o.label)}</span></label>`;
  }).join('') || '<div class="mc-empty">Sin opciones</div>';
  return `<div class="multicheck ${big ? 'big' : ''}" id="${id}"><div class="mc-count">${count} seleccionado(s)</div>${search}<div class="mc-list">${rows}</div></div>`;
}
function mcSelected(el) { return [...el.querySelectorAll('input[type=checkbox]:checked')].map(c => c.value); }
window.mcFilter = function (id, q) {
  q = (q || '').toLowerCase();
  document.querySelectorAll('#' + id + ' .mc-item').forEach(it => { it.style.display = it.dataset.t.includes(q) ? '' : 'none'; });
};
document.addEventListener('change', e => {
  if (e.target.matches('.mc-item input[type=checkbox]')) {
    const item = e.target.closest('.mc-item');
    item.classList.toggle('on', e.target.checked);
    const box = item.closest('.multicheck');
    const c = box.querySelector('.mc-count');
    if (c) c.textContent = mcSelected(box).length + ' seleccionado(s)';
  }
});

function renderField(f, data) {
  const ctrl = fieldControl(f, data.config[f.key], data);
  const wide = ['textarea', 'kvlist', 'taglist', 'commands', 'multiselect', 'channels', 'roles'].includes(f.type) ? ' wide' : '';
  if (f.type === 'toggle' || f.type === 'readonly') {
    return `<div class="field row${wide}"><div class="flabel"><label>${esc(f.label)}</label></div>${ctrl}</div>`;
  }
  return `<div class="field col${wide}"><div class="flabel"><label>${esc(f.label)}</label></div><div class="fctrl">${ctrl}</div></div>`;
}

function rrRow(emoji = '', rolId = '', roles) {
  const sid = 'rr_role_' + Math.random().toString(36).slice(2, 9);
  return `<div class="rr-row" style="display:flex;gap:10px;margin-bottom:8px;align-items:center">
    <input type="text" class="rr-emoji" placeholder="🎮" maxlength="64" value="${esc(emoji)}" style="max-width:96px;text-align:center">
    <span style="color:var(--ink3)">→</span>
    <div class="rr-role-wrap" style="flex:1;min-width:160px">${lbSelect(sid, roles, rolId, { kind: 'role', placeholder: '— rol —' })}</div>
    <button type="button" class="btn rr-del" title="Quitar">✕</button>
  </div>`;
}
function arRuleRow(rule = {}, channels = []) {
  const r = rule || {};
  const scope = r.scope || 'channel';
  const match = r.match || 'contains';
  const emojis = Array.isArray(r.emojis) ? r.emojis.join(' ') : (r.emojis || '');
  const hidePatron = match === 'attachment';
  const hideCanal = scope === 'guild';
  return `<div class="ar-row" data-id="${esc(r.id || '')}" style="border:1px solid var(--line, #333);border-radius:10px;padding:12px;margin-bottom:10px">
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
      <label style="display:flex;gap:6px;align-items:center;font-size:13px"><input type="checkbox" class="ar-activo" ${r.activo === false ? '' : 'checked'}> Activa</label>
      <select class="ar-scope" style="min-width:140px">
        <option value="channel" ${scope === 'channel' ? 'selected' : ''}>Un canal</option>
        <option value="guild" ${scope === 'guild' ? 'selected' : ''}>Todo el server</option>
      </select>
      <div class="ar-canal-wrap" style="flex:1;min-width:160px;${hideCanal ? 'display:none' : ''}">${lbSelect('ar_canal_' + Math.random().toString(36).slice(2, 8), channels, r.canal_id, { kind: 'channel', placeholder: '— canal —' })}</div>
      <button type="button" class="btn ar-del" title="Quitar">✕</button>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
      <select class="ar-match" style="min-width:150px">
        <option value="contains" ${match === 'contains' ? 'selected' : ''}>Contiene texto</option>
        <option value="regex" ${match === 'regex' ? 'selected' : ''}>Regex</option>
        <option value="attachment" ${match === 'attachment' ? 'selected' : ''}>Adjunto / imagen</option>
      </select>
      <input type="text" class="ar-patron" placeholder="palabra, frase o regex" maxlength="200" value="${esc(r.patron || '')}" style="flex:1;min-width:180px;${hidePatron ? 'display:none' : ''}">
      <input type="text" class="ar-emojis" placeholder="🔥 ❤️ ✨" maxlength="120" value="${esc(emojis)}" style="min-width:120px;max-width:200px">
    </div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--ink3)">
      <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" class="ar-bots" ${r.incluir_bots ? 'checked' : ''}> Incluir bots</label>
      <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" class="ar-case" ${r.case_sensitive ? 'checked' : ''}> Mayúsculas importan</label>
    </div>
  </div>`;
}
function renderARSection(data) {
  const cfg = data.config || {};
  const rules = Array.isArray(cfg.autoreacciones) ? cfg.autoreacciones : [];
  const on = !!cfg.autoreaccion_activo;
  const rows = rules.map(r => arRuleRow(r, data.channels)).join('');
  return `<section class="section-card" id="sec-autoreaccion">
    <div class="master-card ${on ? 'on' : ''}">
      <div><div class="mc-t">Autoreacción <span class="badge ${on ? 'on' : 'off'}">${on ? 'Activado' : 'Desactivado'}</span></div></div>
      <label class="switch"><input type="checkbox" id="ar_activo" ${on ? 'checked' : ''}><span></span></label>
    </div>
    <div class="fields" style="grid-template-columns:1fr;margin-top:12px">
      <div class="field col"><div class="flabel"><label>Reglas (máx. 15)</label></div>
        <div class="fctrl"><div id="ar-rules">${rows}</div>
          <button type="button" class="btn" id="ar-add" style="margin-top:6px">+ Agregar regla</button></div></div>
    </div>
    <div class="save-row" style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px">
      <button class="btn primary" id="ar-save">Guardar</button>
    </div>
  </section>`;
}
function readARRules() {
  const out = [];
  document.querySelectorAll('#ar-rules .ar-row').forEach(row => {
    const match = row.querySelector('.ar-match').value;
    const scope = row.querySelector('.ar-scope').value;
    const emojis = row.querySelector('.ar-emojis').value.trim().split(/\s+/).filter(Boolean).slice(0, 3);
    const patron = row.querySelector('.ar-patron').value.trim();
    if (!emojis.length) return;
    if (match !== 'attachment' && !patron) return;
    const canalSel = row.querySelector('.ar-canal-wrap .lb-sel');
    const canal_id = canalSel ? lbSelValue(canalSel.id) : '';
    if (scope === 'channel' && !canal_id) return;
    out.push({
      id: row.dataset.id || '',
      activo: row.querySelector('.ar-activo').checked,
      scope,
      canal_id: canal_id || null,
      match,
      patron: match === 'attachment' ? '' : patron,
      emojis,
      incluir_bots: row.querySelector('.ar-bots').checked,
      case_sensitive: row.querySelector('.ar-case').checked,
    });
  });
  return out;
}
async function saveAR(gid) {
  const body = {
    action: 'autoreaccion_save',
    activo: !!document.getElementById('ar_activo')?.checked,
    rules: readARRules(),
  };
  const res = await api('/api/guild/' + gid + '/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  toast(res.ok ? ('Guardado ✓ · ' + (res.count || 0) + ' reglas') : ('Error: ' + (res.error || '')), !!res.ok);
  if (res.ok) {
    GDATA.config.autoreaccion_activo = !!res.activo;
    GDATA.config.autoreacciones = Array.isArray(res.rules) ? res.rules : body.rules;
  }
}
function wireAR(gid, data) {
  const box = document.getElementById('ar-rules');
  const add = document.getElementById('ar-add');
  if (!box || !add) return;
  add.onclick = () => {
    if (box.querySelectorAll('.ar-row').length >= 15) { toast('Máximo 15 reglas', false); return; }
    box.insertAdjacentHTML('beforeend', arRuleRow({}, data.channels));
  };
  box.addEventListener('click', e => {
    if (e.target.classList.contains('ar-del')) e.target.closest('.ar-row').remove();
  });
  box.addEventListener('change', e => {
    const row = e.target.closest('.ar-row');
    if (!row) return;
    if (e.target.classList.contains('ar-scope')) {
      const canal = row.querySelector('.ar-canal-wrap');
      if (canal) canal.style.display = e.target.value === 'guild' ? 'none' : '';
    }
    if (e.target.classList.contains('ar-match')) {
      const patron = row.querySelector('.ar-patron');
      if (patron) patron.style.display = e.target.value === 'attachment' ? 'none' : '';
    }
  });
  const save = document.getElementById('ar-save');
  if (save) save.onclick = () => saveAR(gid);
  const master = document.getElementById('ar_activo');
  if (master) {
    master.addEventListener('change', () => {
      const mc = master.closest('.master-card');
      if (!mc) return;
      const on = master.checked;
      mc.classList.toggle('on', on);
      const b = mc.querySelector('.badge');
      if (b) { b.className = 'badge ' + (on ? 'on' : 'off'); b.textContent = on ? 'Activado' : 'Desactivado'; }
    });
  }
}
function renderRRSection(data) {
  const cfg = data.config || {};
  const pairs = Array.isArray(cfg.rr_editor) ? cfg.rr_editor : [];
  const rows = pairs.map(p => rrRow(p.emoji, p.rol_id, data.roles)).join('');
  return `<section class="section-card" id="sec-reaction_roles">
    <div class="fields" style="grid-template-columns:1fr">
      <div class="field col"><div class="flabel"><label>Canal</label></div>
        <div class="fctrl">${lbSelect('rr_canal', data.channels, cfg.rr_canal, { kind: 'channel', placeholder: '— elegí un canal —' })}</div></div>
      <div class="field col"><div class="flabel"><label>Mensaje</label></div>
        <div class="fctrl">
          ${lbSelect('rr_mensaje', [], cfg.rr_mensaje, { kind: 'message', placeholder: 'Primero elegí un canal…' })}
          <div class="rr-msg-hint">Se listan los últimos mensajes del canal. No hace falta copiar ningún ID.</div>
        </div></div>
      <div class="field col"><div class="flabel"><label>Roles (emoji → rol)</label></div>
        <div class="fctrl"><div id="rr-pairs">${rows}</div>
          <button type="button" class="btn" id="rr-add" style="margin-top:6px">+ Agregar rol</button></div></div>
      <details style="margin-top:4px">
        <summary style="cursor:pointer;color:var(--ink3);font-size:13px">Opciones al crear un panel nuevo</summary>
        <div class="fields" style="grid-template-columns:1fr;margin-top:10px">
          <div class="field col"><div class="flabel"><label>Título del panel</label></div>
            <div class="fctrl"><input type="text" id="rr_titulo" maxlength="256" value="${esc(cfg.rr_titulo || 'Reaction Roles')}"></div></div>
          <div class="field col"><div class="flabel"><label>Descripción</label></div>
            <div class="fctrl"><textarea id="rr_descripcion" maxlength="2000">${esc(cfg.rr_descripcion || '')}</textarea></div></div>
        </div>
      </details>
    </div>
    <div class="save-row" style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px;flex-wrap:wrap">
      <button class="btn" id="rr-save">Guardar borrador</button>
      <button class="btn" id="rr-create">Crear panel nuevo</button>
      <button class="btn primary" id="rr-apply">Aplicar al mensaje</button>
    </div>
  </section>`;
}
function readRRPairs() {
  const out = [];
  document.querySelectorAll('#rr-pairs .rr-row').forEach(r => {
    const emoji = r.querySelector('.rr-emoji').value.trim();
    const roleSel = r.querySelector('.rr-role-wrap .lb-sel');
    const rol_id = roleSel ? lbSelValue(roleSel.id) : '';
    if (emoji && rol_id) out.push({ emoji, rol_id });
  });
  return out;
}
function rrFormBody() {
  return {
    titulo: (document.getElementById('rr_titulo') || {}).value || 'Reaction Roles',
    descripcion: (document.getElementById('rr_descripcion') || {}).value || '',
    canal: lbSelValue('rr_canal'),
    mensaje: lbSelValue('rr_mensaje'),
    pairs: readRRPairs(),
  };
}
async function saveRR(gid) {
  const body = { action: 'rr_save', ...rrFormBody() };
  const res = await api('/api/guild/' + gid + '/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  toast(res.ok ? ('Guardado ✓ · ' + (res.count || 0) + ' roles') : ('Error: ' + (res.error || '')), !!res.ok);
  if (res.ok) {
    GDATA.config.rr_titulo = body.titulo; GDATA.config.rr_descripcion = body.descripcion;
    GDATA.config.rr_canal = body.canal; GDATA.config.rr_mensaje = body.mensaje; GDATA.config.rr_editor = body.pairs;
  }
}
async function applyRR(gid) {
  const body = { action: 'rr_apply', ...rrFormBody() };
  if (!body.canal) return toast('Elegí un canal', false);
  if (!body.mensaje) return toast('Elegí un mensaje del canal', false);
  if (!body.pairs.length) return toast('Agregá al menos un emoji → rol', false);
  const res = await api('/api/guild/' + gid + '/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  toast(res.ok ? ('Aplicado ✓ · ' + (res.count || 0) + ' reacciones' + (res.channel ? ' en #' + res.channel : '')) : ('Error: ' + (res.error || '')), !!res.ok);
  if (res.ok) {
    GDATA.config.rr_titulo = body.titulo; GDATA.config.rr_descripcion = body.descripcion;
    GDATA.config.rr_canal = body.canal; GDATA.config.rr_mensaje = body.mensaje; GDATA.config.rr_editor = body.pairs;
  }
}
async function loadRRMessages(gid, channelId, selected) {
  if (!channelId) {
    lbSelSetOptions('rr_mensaje', [], '', { kind: 'message', placeholder: 'Primero elegí un canal…' });
    return;
  }
  lbSelSetOptions('rr_mensaje', [], selected || '', { kind: 'message', placeholder: 'Cargando mensajes…' });
  const res = await api('/api/guild/' + gid + '/messages?channel=' + encodeURIComponent(channelId));
  if (res.error) {
    lbSelSetOptions('rr_mensaje', [], '', { kind: 'message', placeholder: 'No pude leer ese canal' });
    toast('No pude listar mensajes: ' + res.error, false);
    return;
  }
  const msgs = res.messages || [];
  lbSelSetOptions('rr_mensaje', msgs, selected || '', { kind: 'message', placeholder: msgs.length ? '— elegí un mensaje —' : 'No hay mensajes recientes' });
}
function wireRR(gid, data) {
  const pairsBox = document.getElementById('rr-pairs');
  const rrAdd = document.getElementById('rr-add');
  if (rrAdd && pairsBox) {
    rrAdd.onclick = () => pairsBox.insertAdjacentHTML('beforeend', rrRow('', '', data.roles));
    pairsBox.addEventListener('click', e => { if (e.target.classList.contains('rr-del')) e.target.closest('.rr-row').remove(); });
  }
  const rrSave = document.getElementById('rr-save');
  if (rrSave) rrSave.onclick = () => saveRR(gid);
  const rrApply = document.getElementById('rr-apply');
  if (rrApply) rrApply.onclick = () => applyRR(gid);
  const rrCreate = document.getElementById('rr-create');
  if (rrCreate) rrCreate.onclick = async () => {
    const body = rrFormBody();
    if (!body.canal) return toast('Elegí un canal', false);
    if (!body.pairs.length) return toast('Agregá al menos un emoji → rol', false);
    await saveRR(gid);
    const res = await api('/api/guild/' + gid + '/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'publish_panel', panel: 'reaction_roles' }) });
    toast(res.ok ? ('Panel creado en #' + (res.channel || '') + ' ✓') : ('Error: ' + (res.error || '')), !!res.ok);
    if (res.ok) await loadRRMessages(gid, body.canal, null);
  };
  const canal = document.getElementById('rr_canal');
  if (canal) {
    canal.addEventListener('lbchange', () => {
      const cid = lbSelValue('rr_canal');
      loadRRMessages(gid, cid, '');
    });
    const initial = lbSelValue('rr_canal');
    if (initial) loadRRMessages(gid, initial, data.config && data.config.rr_mensaje);
  }
}

function renderSection(sec, data) {
  if (sec.id === 'reaction_roles') return renderRRSection(data);
  if (sec.id === 'autoreaccion') return renderARSection(data);
  const fields = sec.fields.slice();
  let master = '';
  if (fields.length && fields[0].type === 'toggle') {
    const mf = fields.shift();
    const on = !!data.config[mf.key];
    master = `<div class="master-card ${on ? 'on' : ''}">
      <div><div class="mc-t">${esc(mf.label)} <span class="badge ${on ? 'on' : 'off'}">${on ? 'Activado' : 'Desactivado'}</span></div></div>
      <label class="switch"><input type="checkbox" id="f_${mf.key}" ${on ? 'checked' : ''}><span></span></label>
    </div>`;
  }
  const rows = fields.map(f => renderField(f, data)).join('');
  let actions = '';
  if (sec.id === 'stats_voice') {
    actions = `<div class="save-row" style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px"><button class="btn danger" data-act="stats_voice_delete">Borrar canales</button>
       <button class="btn primary" data-act="stats_voice_create">Crear / Activar</button></div>`;
  } else if (sec.id === 'confesiones') {
    actions = `<p class="muted" style="margin-top:14px;font-size:13px">Publicá el panel con el botón anónimo en el canal de envío. Guardá el canal primero.</p>
       <div class="save-row" style="display:flex;justify-content:flex-end;margin-top:8px"><button class="btn primary" data-act="publish_panel" data-panel="confession">🤫 Publicar panel de confesión</button></div>`;
  } else if (sec.id === 'verificacion') {
    actions = `<p class="muted" style="margin-top:14px;font-size:13px">Guardá el canal y el rol primero. «Privatizar» oculta todos los canales a @everyone y se los muestra solo al rol verificado (menos el canal de verificación).</p>
       <div class="save-row" style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px;flex-wrap:wrap">
         <button class="btn danger" data-act="verification_lock">🔒 Privatizar canales y publicar</button>
         <button class="btn primary" data-act="publish_panel" data-panel="verification">✅ Publicar panel</button></div>`;
  }
  const fieldsBox = rows ? `<div class="fields">${rows}</div>` : '';
  return `<section class="section-card" id="sec-${sec.id}">${master}${fieldsBox}${actions}</section>`;
}

/* master-card + dirty tracking en vivo */
document.addEventListener('change', e => {
  const mc = e.target.closest && e.target.closest('.master-card');
  if (mc && e.target.matches('.switch input')) {
    const on = e.target.checked;
    mc.classList.toggle('on', on);
    const b = mc.querySelector('.badge');
    if (b) { b.className = 'badge ' + (on ? 'on' : 'off'); b.textContent = on ? 'Activado' : 'Desactivado'; }
  }
});
/* cualquier cambio dentro del contenido de una sección editable → dirty */
['input', 'change'].forEach(ev => document.addEventListener(ev, e => {
  const m = document.getElementById('main-content');
  if (!m || !m.contains(e.target)) return;
  if (!GDATA || !GDATA.schema) return;
  const sec = GDATA.schema.find(s => s.id === CUR_VIEW);
  if (!sec) return;
  if (!e.target.closest('.field') && !e.target.closest('.master-card')) return;
  markDirty();
}));
function markDirty() { DIRTY = true; showSaveBar(true); setSync('dirty'); }

/* Red de seguridad: si cerrás/recargás el navegador con cambios sin guardar, avisa. */
window.addEventListener('beforeunload', e => {
  if (DIRTY) { e.preventDefault(); e.returnValue = ''; return ''; }
});

/* kv / tag editor */
function kvRow(k = '', v = '') { return `<div class="kv-row"><input class="kv-k" placeholder="palabra" value="${esc(k)}"><input class="kv-v" placeholder="respuesta" value="${esc(v)}"><button type="button" class="btn kv-del">✕</button></div>`; }
function kvEditor(id, obj) { return `<div class="kv" id="${id}">${Object.entries(obj).map(([k, v]) => kvRow(k, v)).join('')}<button type="button" class="btn kv-add">+ Agregar</button></div>`; }
function readKv(el) { const o = {}; el.querySelectorAll('.kv-row').forEach(r => { const k = r.querySelector('.kv-k').value.trim(); if (k) o[k] = r.querySelector('.kv-v').value; }); return o; }
function tagRow(v = '') { return `<div class="kv-row"><input class="tag-v" placeholder="palabra" value="${esc(v)}"><button type="button" class="btn kv-del">✕</button></div>`; }
function tagEditor(id, arr) { return `<div class="kv" id="${id}">${(arr || []).map(v => tagRow(v)).join('')}<button type="button" class="btn tag-add">+ Agregar palabra</button></div>`; }
function readTags(el) { const out = []; el.querySelectorAll('.kv-row').forEach(r => { const v = r.querySelector('.tag-v').value.trim().toLowerCase(); if (v) out.push(v); }); return out; }
document.addEventListener('click', e => {
  if (e.target.classList.contains('kv-add')) { e.target.insertAdjacentHTML('beforebegin', kvRow()); markDirty(); }
  if (e.target.classList.contains('tag-add')) { e.target.insertAdjacentHTML('beforebegin', tagRow()); markDirty(); }
  if (e.target.classList.contains('kv-del')) { e.target.closest('.kv-row').remove(); markDirty(); }
});

/* ---------- leer + guardar ---------- */
function readField(f) {
  const el = document.getElementById('f_' + f.key);
  if (!el) return undefined;
  switch (f.type) {
    case 'toggle': return el.checked;
    // Un número vacío no se manda (el backend lo rechazaba y hacía fallar todo el guardado).
    case 'number': return el.value === '' ? undefined : parseInt(el.value, 10);
    case 'channel': case 'role': case 'select': {
      if (el.classList && el.classList.contains('lb-sel')) {
        const v = lbSelValue(el.id);
        return v === '' ? null : v;
      }
      return el.value === '' ? null : el.value;
    }
    case 'roles': case 'channels': case 'multiselect': case 'commands': return mcSelected(el);
    case 'kvlist': return readKv(el);
    case 'taglist': return readTags(el);
    case 'readonly': return undefined;
    default: return el.value;
  }
}

async function saveCurrent() {
  const sec = GDATA.schema.find(s => s.id === CUR_VIEW);
  if (!sec) return;
  const patch = {};
  sec.fields.forEach(f => { const v = readField(f); if (v !== undefined) patch[f.key] = v; });
  setSync('saving');
  document.getElementById('sb-save').disabled = true;
  const res = await api('/api/guild/' + GID, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) });
  document.getElementById('sb-save').disabled = false;
  if (res.__unauth) return renderLogin();
  if (res.ok) {
    Object.assign(GDATA.config, res.config || {}); applyAppearance(GDATA.config);
    DIRTY = false;
    setSync('clean'); showSaveBar(false); toast('Guardado ✓');
  } else {
    // Los campos válidos SÍ se guardaron; solo quedan pendientes los que fallaron.
    Object.assign(GDATA.config, res.config || {});
    setSync('dirty'); toast('Error: ' + (Object.values(res.errores || {})[0] || 'revisá los campos'), false);
  }
}

function wireSections(gid, data, me) {
  document.querySelectorAll('[data-act]').forEach(btn => btn.onclick = async () => {
    if (btn.dataset.act === 'verification_lock' &&
        !confirm('Esto va a ocultar TODOS los canales a @everyone y dejarlos solo para el rol verificado (menos el canal de verificación). ¿Continuar?')) return;
    const sel = document.getElementById('f_stats_voice_tipos');
    const tipos = sel ? mcSelected(sel) : [];
    btn.disabled = true;
    const res = await api('/api/guild/' + gid + '/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: btn.dataset.act, tipos, panel: btn.dataset.panel }) });
    btn.disabled = false;
    const noReload = ['publish_panel', 'verification_lock'];
    if (res.ok && btn.dataset.act === 'publish_panel') {
      toast(res.channel ? ('Panel publicado en #' + res.channel + ' ✓') : 'Panel publicado ✓', true);
    } else if (res.ok && btn.dataset.act === 'verification_lock') {
      toast('Listo ✓ · ' + (res.count || 0) + ' canales privatizados' + (res.channel ? ' · panel en #' + res.channel : ''), true);
    } else {
      toast(res.ok ? 'Listo ✓' : ('Error: ' + (res.error || '')), !!res.ok);
    }
    if (res.ok && !noReload.includes(btn.dataset.act)) openGuild(gid, me);
  });
  wireRR(gid, data);
  wireAR(gid, data);
}

window.addEventListener('DOMContentLoaded', start);

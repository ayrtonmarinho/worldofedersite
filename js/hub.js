/**
 * hub.js — Lobby do Eder
 * Preparado para integração com AWS Lambda + DynamoDB.
 * Enquanto os endpoints não existem, usa MOCK_DATA como fallback automático.
 */

const API = 'https://ac53afc98d.execute-api.sa-east-1.amazonaws.com/prod';
const CHAR_SHEET_URL = 'charactersheet.html';

// ═══════════════════════════════════════════════════════════
//  MOCK DATA (fallback enquanto Lambda não tem os endpoints)
// ═══════════════════════════════════════════════════════════
const MOCK_USERS = [
  { id: 'u_admin',  nome: 'Admin',   senha: 'admin123',   role: 'admin'   },
  { id: 'u_mstr1',  nome: 'Denyver', senha: 'mestre123',  role: 'mestre'  },
  { id: 'u_play1',  nome: 'Ayrton',  senha: 'jogador123', role: 'jogador' },
  { id: 'u_play2',  nome: 'Caio',    senha: 'jogador456', role: 'jogador' },
];

const MOCK_MESAS = [
  {
    id: 'm1',
    titulo: 'A Tríade Perdida',
    mestre_id: 'u_mstr1',
    mestre_nome: 'Denyver',
    archive_link: 'archive_from_eder.html',
    slots: [
      {
        id: 's1',
        jogador_id: 'u_play1', jogador_nome: 'Ayrton',
        personagem_id: null,   personagem_nome: null,
        ficha_liberada: true,  experiencia: 450, nivel: 5
      },
      {
        id: 's2',
        jogador_id: 'u_play2', jogador_nome: 'Caio',
        personagem_id: null,   personagem_nome: null,
        ficha_liberada: false, experiencia: 0, nivel: 1
      },
      {
        id: 's3',
        jogador_id: null, jogador_nome: null,
        personagem_id: null, personagem_nome: null,
        ficha_liberada: false, experiencia: 0, nivel: 1
      },
    ]
  }
];

// ═══════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════
let currentUser = null;
let allMesas    = [];
let adminView   = 'admin'; // 'admin' | 'mestre' | 'jogador'

// ═══════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
  loadSavedUser();
  setupLoginForm();
  setupViewSwitcher();

  if (currentUser) {
    await loadMesas();
  }

  renderPage();
});

// ═══════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════
function loadSavedUser() {
  try {
    const saved = localStorage.getItem('woe_user');
    if (saved) currentUser = JSON.parse(saved);
  } catch(e) { currentUser = null; }
}

function setupLoginForm() {
  document.getElementById('login_button').addEventListener('click', doLogin);
  ['username', 'password'].forEach(id => {
    document.getElementById(id).addEventListener('keydown', e => {
      if (e.key === 'Enter') doLogin();
    });
  });
}

async function doLogin() {
  const nome  = document.getElementById('username').value.trim();
  const senha = document.getElementById('password').value;
  const warn  = document.getElementById('warning_login');

  if (!nome || !senha) { warn.textContent = 'Preencha todos os campos.'; return; }

  warn.textContent = '...';
  const ok = await login(nome, senha);

  if (ok) {
    warn.textContent = '';
    document.getElementById('password').value = '';
    await loadMesas();
    renderPage();
  } else {
    warn.textContent = 'Usuário ou senha inválidos.';
  }
}

async function login(nome, senha) {
  // Tenta API real
  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome, senha })
    });
    if (res.ok) {
      const data = await res.json();
      currentUser = data.user;
      if (data.token) localStorage.setItem('woe_token', data.token);
      localStorage.setItem('woe_user', JSON.stringify(currentUser));
      return true;
    }
  } catch(e) { /* API não disponível, usa mock */ }

  // Fallback mock
  const found = MOCK_USERS.find(
    u => u.nome.toLowerCase() === nome.toLowerCase() && u.senha === senha
  );
  if (found) {
    currentUser = { id: found.id, nome: found.nome, role: found.role };
    localStorage.setItem('woe_user', JSON.stringify(currentUser));
    return true;
  }
  return false;
}

function logout() {
  currentUser = null;
  allMesas    = [];
  localStorage.removeItem('woe_user');
  localStorage.removeItem('woe_token');
  renderPage();
}

// ═══════════════════════════════════════════════════════════
//  MESAS
// ═══════════════════════════════════════════════════════════
async function loadMesas() {
  const token = localStorage.getItem('woe_token');

  try {
    const res = await fetch(`${API}/mesas`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (res.ok) { allMesas = await res.json(); return; }
  } catch(e) { /* fallback */ }

  // Mock filtrado por role
  if (currentUser.role === 'admin') {
    allMesas = JSON.parse(JSON.stringify(MOCK_MESAS));
  } else if (currentUser.role === 'mestre') {
    allMesas = JSON.parse(JSON.stringify(
      MOCK_MESAS.filter(m => m.mestre_id === currentUser.id)
    ));
  } else {
    allMesas = JSON.parse(JSON.stringify(
      MOCK_MESAS.filter(m => (m.slots || []).some(s => s.jogador_id === currentUser.id))
    ));
  }
}

async function apiCall(path, options = {}) {
  const token = localStorage.getItem('woe_token');
  try {
    return await fetch(`${API}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(options.headers || {})
      }
    });
  } catch(e) { return null; }
}

// ═══════════════════════════════════════════════════════════
//  RENDER PAGE
// ═══════════════════════════════════════════════════════════
function renderPage() {
  const loginSection  = document.getElementById('login-section');
  const lobbySection  = document.getElementById('lobby-section');
  const toolsSection  = document.getElementById('tools-section');
  const userBadge     = document.getElementById('user-badge');

  if (currentUser) {
    loginSection.classList.add('hidden');
    lobbySection.classList.remove('hidden');
    toolsSection.classList.remove('hidden');
    renderUserBadge(userBadge);
    renderLobby();
  } else {
    loginSection.classList.remove('hidden');
    lobbySection.classList.add('hidden');
    toolsSection.classList.add('hidden');
    userBadge.innerHTML = '';
    userBadge.classList.add('hidden');
  }
}

// ─── User Badge ──────────────────────────────────────────
function renderUserBadge(container) {
  const ROLES = {
    admin:   { label: '<i class="fa-solid fa-crown"></i> Admin',           cls: 'role-admin'   },
    mestre:  { label: '<i class="fa-solid fa-chess-king"></i> Mestre',     cls: 'role-mestre'  },
    jogador: { label: '<i class="fa-solid fa-dice-d20"></i> Jogador',      cls: 'role-jogador' },
  };
  const r = ROLES[currentUser.role] || ROLES.jogador;
  container.innerHTML = `
    <span class="role-tag ${r.cls}">${r.label}</span>
    <span class="user-name">${esc(currentUser.nome)}</span>
    <button class="btn-logout" onclick="logout()">
      <i class="fa-solid fa-right-from-bracket"></i> Sair
    </button>
  `;
  container.classList.remove('hidden');
}

// ─── View Switcher (Admin) ───────────────────────────────
function setupViewSwitcher() {
  document.getElementById('view-switcher').addEventListener('click', e => {
    const btn = e.target.closest('.view-btn');
    if (!btn) return;
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    adminView = btn.dataset.view;
    renderLobby();
  });
}

// ─── Lobby ───────────────────────────────────────────────
function renderLobby() {
  const content  = document.getElementById('lobby-content');
  const switcher = document.getElementById('view-switcher');

  if (currentUser.role === 'admin') {
    switcher.classList.remove('hidden');
    renderViewByRole(adminView, content);
  } else {
    switcher.classList.add('hidden');
    renderViewByRole(currentUser.role, content);
  }
}

function renderViewByRole(role, container) {
  container.innerHTML = '';
  if      (role === 'admin')   renderAdminDashboard(container);
  else if (role === 'mestre')  renderMestreView(container);
  else                         renderJogadorView(container);
}

// ═══════════════════════════════════════════════════════════
//  VISÃO: JOGADOR
// ═══════════════════════════════════════════════════════════
function renderJogadorView(container) {
  const uid     = currentUser.id;
  const myMesas = allMesas.filter(m => (m.slots || []).some(s => s.jogador_id === uid));

  if (myMesas.length === 0) {
    container.innerHTML = `
      <div class="lobby-empty">
        <i class="fa-solid fa-scroll"></i>
        <p>Você ainda não participa de nenhuma mesa.</p>
        <p class="empty-sub">Aguarde um mestre te adicionar a uma mesa.</p>
      </div>`;
    return;
  }

  const grid = createElement('div', 'mesa-cards-grid');
  myMesas.forEach(mesa => {
    const slot = (mesa.slots || []).find(s => s.jogador_id === uid);
    grid.appendChild(buildJogadorCard(mesa, slot));
  });
  container.appendChild(grid);
}

function buildJogadorCard(mesa, slot) {
  const card = createElement('div', 'mesa-card jogador-card');
  card.innerHTML = `
    <div class="mesa-card-header">
      <span class="mesa-icon">⚔</span>
      <div>
        <div class="mesa-title">${esc(mesa.titulo)}</div>
        <div class="mesa-sub">Mestre: ${esc(mesa.mestre_nome)}</div>
      </div>
    </div>
    <div class="mesa-card-body">
      <div class="slot-info">
        <span class="info-label">Personagem</span>
        <span class="info-val">${esc(slot.personagem_nome || '—')}</span>
      </div>
      <div class="slot-info">
        <span class="info-label">Nível</span>
        <span class="info-val">${slot.nivel || 1}</span>
      </div>
      <div class="slot-info">
        <span class="info-label">Experiência</span>
        <span class="info-val">${slot.experiencia || 0} XP</span>
      </div>
      <div class="ficha-status ${slot.ficha_liberada ? 'liberada' : 'bloqueada'}">
        ${slot.ficha_liberada ? '✓ Ficha liberada para edição' : '🔒 Ficha bloqueada (somente leitura)'}
      </div>
    </div>
    <div class="mesa-card-footer">
      <button class="btn-mesa ${slot.ficha_liberada ? '' : 'disabled'}"
        onclick="openFicha('${mesa.id}','${slot.id}','jogador')"
        ${!slot.ficha_liberada ? 'title="O mestre ainda não liberou edição"' : ''}>
        📋 ${slot.ficha_liberada ? 'Editar Ficha' : 'Ver Ficha'}
      </button>
      <button class="btn-mesa btn-secondary"
        onclick="window.open('${esc(mesa.archive_link || 'archive_from_eder.html')}?mesa=${mesa.id}','_blank')">
        📖 Arquivo
      </button>
    </div>`;
  return card;
}

// ═══════════════════════════════════════════════════════════
//  VISÃO: MESTRE
// ═══════════════════════════════════════════════════════════
function renderMestreView(container) {
  const mestreId = currentUser.role === 'admin' ? null : currentUser.id;
  const myMesas  = mestreId ? allMesas.filter(m => m.mestre_id === mestreId) : allMesas;

  const header = createElement('div', 'mestre-header');
  header.innerHTML = `
    <button class="btn-primary" onclick="showCreateMesaModal()">
      <i class="fa-solid fa-plus"></i> Nova Mesa
    </button>`;
  container.appendChild(header);

  if (myMesas.length === 0) {
    container.innerHTML += `
      <div class="lobby-empty">
        <i class="fa-solid fa-table"></i>
        <p>Nenhuma mesa criada ainda.</p>
        <p class="empty-sub">Clique em "Nova Mesa" para começar.</p>
      </div>`;
    return;
  }

  myMesas.forEach(mesa => container.appendChild(buildMesaPanel(mesa)));
}

function buildMesaPanel(mesa) {
  const panel = createElement('div', 'mesa-panel');
  panel.dataset.mesaId = mesa.id;
  panel.innerHTML = `
    <div class="mesa-panel-header">
      <div class="mesa-panel-title">
        <span class="mesa-icon">⚔</span>
        <span>${esc(mesa.titulo)}</span>
        <span style="font-size:.72rem;color:var(--text-secondary);font-family:var(--font-body)">
          — ${(mesa.slots || []).filter(s => s.jogador_id).length}/${(mesa.slots || []).length} slots
        </span>
      </div>
      <div class="mesa-panel-actions">
        <a href="${esc(mesa.archive_link || 'archive_from_eder.html')}?mesa=${mesa.id}"
           class="btn-icon" title="Arquivo" target="_blank">📖</a>
        <button class="btn-icon" onclick="addSlot('${mesa.id}')" title="Adicionar Slot">
          <i class="fa-solid fa-user-plus"></i>
        </button>
        <button class="btn-icon" onclick="showEditMesaModal('${mesa.id}')" title="Editar Mesa">
          <i class="fa-solid fa-pen"></i>
        </button>
        <button class="btn-icon btn-danger" onclick="confirmDeleteMesa('${mesa.id}')" title="Excluir Mesa">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
    </div>
    <div class="mesa-slots" id="slots-${mesa.id}"></div>`;

  buildSlotsInPanel(mesa, panel.querySelector(`#slots-${mesa.id}`));
  return panel;
}

function buildSlotsInPanel(mesa, container) {
  container.innerHTML = '';
  if ((mesa.slots || []).length === 0) {
    container.innerHTML = `
      <div style="padding:.75rem 1.25rem;font-size:.82rem;color:var(--text-secondary)">
        Nenhum slot. Adicione jogadores com o botão <i class="fa-solid fa-user-plus"></i>.
      </div>`;
    return;
  }

  (mesa.slots || []).forEach(slot => {
    const row = createElement('div', 'slot-row');
    row.dataset.slotId = slot.id;

    if (slot.jogador_id) {
      row.innerHTML = `
        <div class="slot-filled">
          <i class="fa-solid fa-user slot-icon"></i>
          <div class="slot-player-info">
            <span class="slot-player-name">${esc(slot.jogador_nome)}</span>
            ${slot.personagem_nome ? `<span class="slot-char-name">· ${esc(slot.personagem_nome)}</span>` : ''}
          </div>
          <div class="slot-badges">
            <span class="badge badge-nivel">Nv. ${slot.nivel || 1}</span>
            <span class="badge badge-xp">${slot.experiencia || 0} XP</span>
            <span class="badge ${slot.ficha_liberada ? 'badge-liberada' : 'badge-bloqueada'}">
              ${slot.ficha_liberada ? '✓ Liberada' : '🔒 Bloqueada'}
            </span>
          </div>
          <div class="slot-actions">
            <button class="btn-slot" onclick="toggleSlotMgmt('${mesa.id}','${slot.id}')">
              <i class="fa-solid fa-gear"></i> Gerenciar
            </button>
            <button class="btn-slot" onclick="openFicha('${mesa.id}','${slot.id}','mestre')">
              <i class="fa-solid fa-scroll"></i> Ficha
            </button>
          </div>
        </div>`;
    } else {
      row.innerHTML = `
        <div class="slot-empty">
          <i class="fa-solid fa-user-slash slot-icon empty-icon"></i>
          <span class="slot-empty-label">Slot vago</span>
          <div class="slot-actions">
            <button class="btn-slot btn-assign" onclick="showAssignModal('${mesa.id}','${slot.id}')">
              <i class="fa-solid fa-user-plus"></i> Associar Jogador
            </button>
            <button class="btn-icon btn-danger" onclick="removeSlot('${mesa.id}','${slot.id}')"
              title="Remover slot">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>
        </div>`;
    }

    container.appendChild(row);

    // Painel de gerenciamento (inicialmente escondido)
    if (slot.jogador_id) {
      const mgmt = createElement('div', 'slot-mgmt-panel hidden');
      mgmt.id = `mgmt-${slot.id}`;
      mgmt.innerHTML = buildMgmtPanel(mesa, slot);
      container.appendChild(mgmt);
    }
  });
}

function buildMgmtPanel(mesa, slot) {
  return `
    <div class="mgmt-inner">
      <div class="mgmt-section">
        <div class="mgmt-title">Progresso</div>
        <div class="mgmt-fields">
          <div class="mgmt-field">
            <label>Experiência</label>
            <div class="mgmt-input-row">
              <input type="number" class="mgmt-input" id="xp-${slot.id}"
                value="${slot.experiencia || 0}" min="0">
              <button class="btn-mgmt"
                onclick="saveSlotField('${mesa.id}','${slot.id}','experiencia',
                  document.getElementById('xp-${slot.id}').value)">
                <i class="fa-solid fa-check"></i>
              </button>
            </div>
          </div>
          <div class="mgmt-field">
            <label>Nível</label>
            <div class="mgmt-input-row">
              <input type="number" class="mgmt-input" id="nivel-${slot.id}"
                value="${slot.nivel || 1}" min="1" max="30">
              <button class="btn-mgmt"
                onclick="saveSlotField('${mesa.id}','${slot.id}','nivel',
                  document.getElementById('nivel-${slot.id}').value)">
                <i class="fa-solid fa-check"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="mgmt-section">
        <div class="mgmt-title">Ficha</div>
        <div class="mgmt-ficha-row">
          <span>Edição:</span>
          <label class="toggle-switch">
            <input type="checkbox" id="toggle-${slot.id}"
              ${slot.ficha_liberada ? 'checked' : ''}
              onchange="toggleFicha('${mesa.id}','${slot.id}',this.checked)">
            <span class="toggle-slider"></span>
          </label>
          <span class="toggle-label" id="tlabel-${slot.id}">
            ${slot.ficha_liberada ? 'Liberada' : 'Bloqueada'}
          </span>
        </div>
        <button class="btn-mgmt-secondary"
          onclick="openFicha('${mesa.id}','${slot.id}','mestre')">
          <i class="fa-solid fa-eye"></i> Ver Ficha do Jogador
        </button>
      </div>

      <div class="mgmt-section">
        <div class="mgmt-title">Adicionar Item</div>
        <div class="mgmt-input-row">
          <select class="mgmt-select" id="item-sel-${slot.id}">
            <option value="">— Selecionar —</option>
          </select>
          <button class="btn-mgmt" onclick="addItemToPlayer('${mesa.id}','${slot.id}')">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
        <div style="margin-top:.35rem;font-size:.65rem;color:var(--text-secondary)">
          Itens serão adicionados ao inventário da ficha do jogador.
        </div>
      </div>

      <div class="mgmt-section mgmt-danger-zone">
        <div class="mgmt-title">Zona de Risco</div>
        <button class="btn-danger-full"
          onclick="removePlayerFromSlot('${mesa.id}','${slot.id}')">
          <i class="fa-solid fa-user-minus"></i> Remover Jogador do Slot
        </button>
      </div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════
//  VISÃO: ADMIN
// ═══════════════════════════════════════════════════════════
function renderAdminDashboard(container) {
  const totalJogadores   = allMesas.reduce((a, m) => a + (m.slots || []).filter(s => s.jogador_id).length, 0);
  const totalLiberadas   = allMesas.reduce((a, m) => a + (m.slots || []).filter(s => s.ficha_liberada).length, 0);

  container.innerHTML = `
    <div class="admin-stats">
      <div class="admin-stat-card">
        <div class="admin-stat-val">${allMesas.length}</div>
        <div class="admin-stat-label">Mesas Ativas</div>
      </div>
      <div class="admin-stat-card">
        <div class="admin-stat-val">${totalJogadores}</div>
        <div class="admin-stat-label">Jogadores</div>
      </div>
      <div class="admin-stat-card">
        <div class="admin-stat-val">${totalLiberadas}</div>
        <div class="admin-stat-label">Fichas Liberadas</div>
      </div>
    </div>
    <div id="admin-mesas-list"></div>`;

  const list = container.querySelector('#admin-mesas-list');
  allMesas.forEach(mesa => list.appendChild(buildMesaPanel(mesa)));
}

// ═══════════════════════════════════════════════════════════
//  ACTIONS — SLOTS
// ═══════════════════════════════════════════════════════════
function toggleSlotMgmt(mesaId, slotId) {
  const panel = document.getElementById(`mgmt-${slotId}`);
  if (!panel) return;

  // Fecha outros painéis
  document.querySelectorAll('.slot-mgmt-panel').forEach(p => {
    if (p.id !== `mgmt-${slotId}`) p.classList.add('hidden');
  });

  const opening = panel.classList.toggle('hidden') === false;
  if (opening) populateItemSelect(`item-sel-${slotId}`);
}

async function populateItemSelect(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel || sel.options.length > 1) return;

  // Tenta buscar itens da API
  try {
    const res = await apiCall('/itens');
    if (res && res.ok) {
      const itens = await res.json();
      itens.forEach(item => sel.appendChild(newOption(item.id, item.nome)));
      return;
    }
  } catch(e) {}

  // Mock
  ['Espada Longa +1','Escudo de Carvalho','Poção de Cura','Manto Sombrio','Amuleto de Proteção']
    .forEach(nome => sel.appendChild(newOption(nome, nome)));
}

function newOption(val, label) {
  const opt = document.createElement('option');
  opt.value = val; opt.textContent = label; return opt;
}

async function saveSlotField(mesaId, slotId, field, value) {
  const mesa = allMesas.find(m => m.id === mesaId);
  if (!mesa) return;
  const slot = (mesa.slots || []).find(s => s.id === slotId);
  if (!slot) return;
  slot[field] = Number(value);

  // API call
  await apiCall(`/mesas/${mesaId}/slots/${slotId}`, {
    method: 'PUT',
    body: JSON.stringify({ [field]: Number(value) })
  });

  showToast(`${field === 'experiencia' ? 'XP' : 'Nível'} atualizado!`);
  // Atualiza badge sem re-renderizar tudo
  const badgeEl = document.querySelector(`[data-slot-id="${slotId}"] .slot-badges`);
  if (badgeEl) {
    const nivelBadge = badgeEl.querySelector('.badge-nivel');
    const xpBadge    = badgeEl.querySelector('.badge-xp');
    if (nivelBadge && field === 'nivel') nivelBadge.textContent = `Nv. ${value}`;
    if (xpBadge    && field === 'experiencia') xpBadge.textContent = `${value} XP`;
  }
}

async function toggleFicha(mesaId, slotId, liberada) {
  const label = document.getElementById(`tlabel-${slotId}`);
  if (label) label.textContent = liberada ? 'Liberada' : 'Bloqueada';

  const mesa = allMesas.find(m => m.id === mesaId);
  if (mesa) {
    const slot = (mesa.slots || []).find(s => s.id === slotId);
    if (slot) slot.ficha_liberada = liberada;
  }

  await apiCall(`/mesas/${mesaId}/slots/${slotId}/unlock`, {
    method: 'PUT',
    body: JSON.stringify({ ficha_liberada: liberada })
  });

  showToast(`Ficha ${liberada ? 'liberada para edição' : 'bloqueada'}!`);

  // Atualiza badge inline
  const badgeEl = document.querySelector(
    `[data-slot-id="${slotId}"] .badge-liberada, [data-slot-id="${slotId}"] .badge-bloqueada`
  );
  if (badgeEl) {
    badgeEl.className = `badge ${liberada ? 'badge-liberada' : 'badge-bloqueada'}`;
    badgeEl.textContent = liberada ? '✓ Liberada' : '🔒 Bloqueada';
  }
}

async function addItemToPlayer(mesaId, slotId) {
  const sel = document.getElementById(`item-sel-${slotId}`);
  if (!sel || !sel.value) { showToast('Selecione um item.', 'error'); return; }
  const itemNome = sel.options[sel.selectedIndex].text;

  await apiCall(`/mesas/${mesaId}/slots/${slotId}/items`, {
    method: 'POST',
    body: JSON.stringify({ item_id: sel.value })
  });

  showToast(`"${itemNome}" adicionado ao inventário!`);
  sel.value = '';
}

async function addSlot(mesaId) {
  const mesa = allMesas.find(m => m.id === mesaId);
  if (!mesa) return;
  if (!mesa.slots) mesa.slots = [];

  const res = await apiCall(`/mesas/${mesaId}/slots`, { method: 'POST' });
  if (res && res.ok) {
    const newSlot = await res.json();
    mesa.slots.push(newSlot);
  } else {
    mesa.slots.push({
      id: `s_${Date.now()}`,
      jogador_id: null, jogador_nome: null,
      personagem_id: null, personagem_nome: null,
      ficha_liberada: false, experiencia: 0, nivel: 1
    });
  }

  renderLobby();
  showToast('Slot adicionado!');
}

function removeSlot(mesaId, slotId) {
  const mesa = allMesas.find(m => m.id === mesaId);
  if (!mesa) return;
  mesa.slots = (mesa.slots || []).filter(s => s.id !== slotId);
  apiCall(`/mesas/${mesaId}/slots/${slotId}`, { method: 'DELETE' });
  renderLobby();
  showToast('Slot removido.');
}

function removePlayerFromSlot(mesaId, slotId) {
  const mesa = allMesas.find(m => m.id === mesaId);
  const slot = mesa?.slots.find(s => s.id === slotId);
  if (!slot) return;

  const nome = slot.jogador_nome;
  Object.assign(slot, {
    jogador_id: null, jogador_nome: null,
    personagem_id: null, personagem_nome: null,
    ficha_liberada: false
  });

  apiCall(`/mesas/${mesaId}/slots/${slotId}/assign`, {
    method: 'DELETE'
  });

  closeModal();
  renderLobby();
  showToast(`${nome} removido do slot.`);
}

// ═══════════════════════════════════════════════════════════
//  ACTIONS — MESAS
// ═══════════════════════════════════════════════════════════
function showCreateMesaModal() {
  const isAdmin = currentUser.role === 'admin';
  openModal(`
    <div class="modal-header">
      <h3>Nova Mesa</h3>
      <button class="btn-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="field-group">
        <label>Título da Mesa</label>
        <input type="text" id="nova-mesa-titulo" class="modal-input" placeholder="Ex: A Tríade Perdida">
      </div>
      ${isAdmin ? `
      <div class="field-group" style="margin-top:.5rem">
        <label>Mestre <span style="color:var(--text-secondary);font-size:.7rem">— opcional, pode associar depois</span></label>
        <div class="mgmt-input-row" style="margin-top:.4rem">
          <input type="text" id="nova-mesa-mestre-search" class="modal-input"
            placeholder="Buscar mestre por nome..." style="flex:1"
            onkeydown="if(event.key==='Enter')searchMestreForMesa()">
          <button class="btn-mgmt" onclick="searchMestreForMesa()">
            <i class="fa-solid fa-magnifying-glass"></i>
          </button>
        </div>
        <div id="nova-mesa-mestre-results"></div>
        <input type="hidden" id="nova-mesa-mestre-id" value="">
        <div id="nova-mesa-mestre-selected"
          style="display:none;margin-top:.35rem;font-size:.8rem;color:var(--accent-gold)"></div>
      </div>` : ''}
      <button class="btn-primary" style="width:100%;justify-content:center;margin-top:.75rem"
        onclick="createMesa()">
        <i class="fa-solid fa-plus"></i> Criar Mesa
      </button>
    </div>`);
  setTimeout(() => document.getElementById('nova-mesa-titulo')?.focus(), 100);
}

async function createMesa() {
  const titulo = document.getElementById('nova-mesa-titulo')?.value.trim();
  if (!titulo) { showToast('Digite um título.', 'error'); return; }

  const mestreId   = document.getElementById('nova-mesa-mestre-id')?.value || '';
  const mestreNome = mestreId
    ? (document.getElementById('nova-mesa-mestre-search')?.value || '')
    : currentUser.nome;

  const novaMesa = {
    id: `m_${Date.now()}`,
    titulo,
    mestre_id:    mestreId || currentUser.id,
    mestre_nome:  mestreNome,
    archive_link: 'archive_from_eder.html',
    slots: []
  };
  allMesas.push(novaMesa);

  const payload = { titulo };
  if (mestreId) payload.mestre_id = mestreId;

  await apiCall('/mesas', { method: 'POST', body: JSON.stringify(payload) });

  closeModal();
  renderLobby();
  showToast(`Mesa "${titulo}" criada!`);
}

function confirmDeleteMesa(mesaId) {
  const mesa = allMesas.find(m => m.id === mesaId);
  if (!mesa) return;
  openModal(`
    <div class="modal-header">
      <h3>Excluir Mesa</h3>
      <button class="btn-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text-secondary);font-size:.9rem">
        Tem certeza que deseja excluir <strong style="color:var(--accent-gold)">${esc(mesa.titulo)}</strong>?
        Esta ação não pode ser desfeita.
      </p>
      <div style="display:flex;gap:.5rem;margin-top:.5rem">
        <button class="btn-danger-full" style="flex:1" onclick="deleteMesa('${mesaId}')">
          <i class="fa-solid fa-trash"></i> Excluir
        </button>
        <button class="btn-slot" style="flex:1;justify-content:center" onclick="closeModal()">Cancelar</button>
      </div>
    </div>`);
}

async function deleteMesa(mesaId) {
  allMesas = allMesas.filter(m => m.id !== mesaId);
  await apiCall(`/mesas/${mesaId}`, { method: 'DELETE' });
  closeModal();
  renderLobby();
  showToast('Mesa excluída.');
}

// ═══════════════════════════════════════════════════════════
//  MODAL — ASSOCIAR JOGADOR
// ═══════════════════════════════════════════════════════════
function showAssignModal(mesaId, slotId) {
  openModal(`
    <div class="modal-header">
      <h3>Associar Jogador</h3>
      <button class="btn-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="field-group">
        <label>Buscar por nome</label>
        <div class="mgmt-input-row">
          <input type="text" id="player-search" class="modal-input"
            placeholder="Nome do jogador..." style="flex:1">
          <button class="btn-mgmt" onclick="searchPlayer('${mesaId}','${slotId}')">
            <i class="fa-solid fa-magnifying-glass"></i>
          </button>
        </div>
      </div>
      <div id="search-results"></div>

      <div class="modal-divider">ou convide por email</div>

      <div class="field-group">
        <label>Email para convite</label>
        <input type="email" id="invite-email" class="modal-input"
          placeholder="jogador@email.com">
        <button class="btn-secondary-full" style="margin-top:.4rem"
          onclick="generateInvite('${mesaId}','${slotId}')">
          <i class="fa-solid fa-envelope"></i> Gerar Link de Convite
        </button>
      </div>
      <div id="invite-result"></div>
    </div>`);

  document.getElementById('player-search')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') searchPlayer(mesaId, slotId);
  });
}

async function searchPlayer(mesaId, slotId) {
  const query   = document.getElementById('player-search')?.value.trim();
  const results = document.getElementById('search-results');
  if (!query || !results) return;

  results.innerHTML = '<div class="lobby-loading"><div class="mini-spinner"></div><span>Buscando...</span></div>';

  let users = [];
  try {
    const res = await apiCall(`/users?search=${encodeURIComponent(query)}&role=jogador`);
    if (res && res.ok) users = await res.json();
  } catch(e) {}

  // Mock fallback
  if (users.length === 0) {
    users = MOCK_USERS.filter(
      u => u.role === 'jogador' && u.nome.toLowerCase().includes(query.toLowerCase())
    );
  }

  if (users.length === 0) {
    results.innerHTML = `<p class="search-empty">Nenhum usuário encontrado. Use o convite por email.</p>`;
    return;
  }

  results.innerHTML = users.map(u => `
    <div class="search-result-row">
      <span class="result-name"><i class="fa-solid fa-user"></i> ${esc(u.nome)}</span>
      <button class="btn-assign-player"
        onclick="confirmAssign('${mesaId}','${slotId}','${u.id}','${esc(u.nome)}')">
        Associar
      </button>
    </div>`).join('');
}

async function confirmAssign(mesaId, slotId, userId, userName) {
  const mesa = allMesas.find(m => m.id === mesaId);
  const slot = mesa?.slots.find(s => s.id === slotId);
  if (!slot) return;

  slot.jogador_id   = userId;
  slot.jogador_nome = userName;

  await apiCall(`/mesas/${mesaId}/slots/${slotId}/assign`, {
    method: 'PUT',
    body: JSON.stringify({ jogador_id: userId })
  });

  closeModal();
  renderLobby();
  showToast(`${userName} associado ao slot!`);
}

async function generateInvite(mesaId, slotId) {
  const email = document.getElementById('invite-email')?.value.trim();
  if (!email) { showToast('Digite um email.', 'error'); return; }

  const base = window.location.href.replace(/[^/]*$/, '');
  const link = `${base}register.html?mesa=${mesaId}&slot=${slotId}&email=${encodeURIComponent(email)}`;
  const result = document.getElementById('invite-result');

  result.innerHTML = `
    <div class="invite-box" style="align-items:center;flex-direction:row;gap:.5rem">
      <div class="mini-spinner"></div>
      <span style="font-size:.78rem;color:var(--text-secondary)">Enviando email...</span>
    </div>`;

  try {
    const res = await apiCall('/auth/invite', {
      method: 'POST',
      body: JSON.stringify({ email, mesa_id: mesaId, slot_id: slotId, base_url: base })
    });

    if (res && res.ok) {
      result.innerHTML = `
        <div class="invite-box">
          <p class="invite-label" style="color:#4caf50">
            <i class="fa-solid fa-circle-check"></i> Email enviado para ${esc(email)}!
          </p>
          <p class="invite-label" style="margin-top:.4rem">Link de backup:</p>
          <input type="text" class="invite-link" value="${esc(link)}" readonly onclick="this.select()">
          <button class="btn-copy"
            onclick="navigator.clipboard.writeText('${esc(link)}').then(()=>showToast('Link copiado!'))">
            <i class="fa-solid fa-copy"></i> Copiar
          </button>
        </div>`;
      showToast(`Convite enviado para ${email}!`);
      return;
    }

    // SES retornou erro mas enviou o link no body — fallback manual
    const data = res ? await res.json().catch(() => ({})) : {};
    const fallbackLink = data.link || link;
    _showInviteFallback(result, email, fallbackLink, 'SES não configurado ou email não verificado.');

  } catch(e) {
    _showInviteFallback(result, email, link, 'Erro de conexão.');
  }
}

function _showInviteFallback(result, email, link, motivo) {
  result.innerHTML = `
    <div class="invite-box">
      <p class="invite-label" style="color:#e57373">
        <i class="fa-solid fa-triangle-exclamation"></i> Email não enviado — ${esc(motivo)}
      </p>
      <p class="invite-label" style="margin-top:.4rem">Compartilhe o link manualmente com ${esc(email)}:</p>
      <input type="text" class="invite-link" value="${esc(link)}" readonly onclick="this.select()">
      <button class="btn-copy"
        onclick="navigator.clipboard.writeText('${esc(link)}').then(()=>showToast('Link copiado!'))">
        <i class="fa-solid fa-copy"></i> Copiar
      </button>
    </div>`;
}

// ═══════════════════════════════════════════════════════════
//  ACTIONS — EDITAR MESA
// ═══════════════════════════════════════════════════════════
function showEditMesaModal(mesaId) {
  const mesa    = allMesas.find(m => m.id === mesaId);
  if (!mesa) return;
  const isAdmin = currentUser.role === 'admin';

  openModal(`
    <div class="modal-header">
      <h3>Editar Mesa</h3>
      <button class="btn-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="field-group">
        <label>Título da Mesa</label>
        <input type="text" id="edit-mesa-titulo" class="modal-input" value="${esc(mesa.titulo)}">
      </div>
      <div class="field-group" style="margin-top:.5rem">
        <label>Mensagem de convite <span style="color:var(--text-secondary);font-size:.7rem">— opcional, substitui o texto padrão do email</span></label>
        <textarea id="edit-mesa-msg" class="modal-input" rows="3"
          placeholder="Ex: Estamos montando uma nova campanha épica! Venha fazer parte desta aventura..."
          style="resize:vertical;font-family:var(--font-body);font-size:.85rem;line-height:1.5">${esc(mesa.mensagem_convite || '')}</textarea>
      </div>
      ${isAdmin ? `
      <div class="field-group" style="margin-top:.5rem">
        <label>Mestre atual: <strong style="color:var(--accent-gold)">${esc(mesa.mestre_nome || '—')}</strong></label>
        <div class="mgmt-input-row" style="margin-top:.5rem">
          <input type="text" id="edit-mesa-mestre-search" class="modal-input"
            placeholder="Buscar novo mestre..." style="flex:1"
            onkeydown="if(event.key==='Enter')searchMestreForEdit()">
          <button class="btn-mgmt" onclick="searchMestreForEdit()">
            <i class="fa-solid fa-magnifying-glass"></i>
          </button>
        </div>
        <div id="edit-mesa-mestre-results"></div>
        <input type="hidden" id="edit-mesa-mestre-id" value="">
        <div id="edit-mesa-mestre-selected"
          style="display:none;margin-top:.35rem;font-size:.8rem;color:var(--accent-gold)"></div>
        ${mesa.mestre_id ? `
        <button class="btn-danger-full" style="margin-top:.5rem"
          onclick="removeMestreFromMesa('${mesaId}')">
          <i class="fa-solid fa-user-minus"></i> Remover Mestre
        </button>` : ''}
      </div>` : ''}
      <button class="btn-primary" style="width:100%;justify-content:center;margin-top:.75rem"
        onclick="saveMesaEdits('${mesaId}')">
        <i class="fa-solid fa-check"></i> Salvar
      </button>
    </div>`);
  setTimeout(() => document.getElementById('edit-mesa-titulo')?.focus(), 100);
}

async function saveMesaEdits(mesaId) {
  const titulo = document.getElementById('edit-mesa-titulo')?.value.trim();
  if (!titulo) { showToast('Digite um título.', 'error'); return; }

  const mestreId  = document.getElementById('edit-mesa-mestre-id')?.value || null;
  const msgConv   = document.getElementById('edit-mesa-msg')?.value.trim() || '';
  const body      = { titulo, mensagem_convite: msgConv };
  if (mestreId) body.mestre_id = mestreId;

  await apiCall(`/mesas/${mesaId}`, { method: 'PUT', body: JSON.stringify(body) });

  const mesa = allMesas.find(m => m.id === mesaId);
  if (mesa) {
    mesa.titulo            = titulo;
    mesa.mensagem_convite  = msgConv;
    if (mestreId) {
      mesa.mestre_id   = mestreId;
      mesa.mestre_nome = document.getElementById('edit-mesa-mestre-search')?.value || '';
    }
  }

  closeModal();
  renderLobby();
  showToast('Mesa atualizada!');
}

async function removeMestreFromMesa(mesaId) {
  await apiCall(`/mesas/${mesaId}`, {
    method: 'PUT',
    body: JSON.stringify({ mestre_id: null })
  });

  const mesa = allMesas.find(m => m.id === mesaId);
  if (mesa) { mesa.mestre_id = ''; mesa.mestre_nome = ''; }

  closeModal();
  renderLobby();
  showToast('Mestre removido da mesa.');
}

async function _searchMestre(inputId, resultsId, selectFn) {
  const query   = document.getElementById(inputId)?.value.trim();
  const results = document.getElementById(resultsId);
  if (!query || !results) return;

  results.innerHTML = '<div style="font-size:.75rem;color:var(--text-secondary);padding:.3rem 0">Buscando...</div>';

  let users = [];
  try {
    const res = await apiCall(`/users?search=${encodeURIComponent(query)}&role=mestre`);
    if (res && res.ok) users = await res.json();
  } catch(e) {}

  if (!users.length) {
    users = MOCK_USERS.filter(
      u => u.role === 'mestre' && u.nome.toLowerCase().includes(query.toLowerCase())
    );
  }

  if (!users.length) {
    results.innerHTML = '<div style="font-size:.75rem;color:var(--text-secondary);padding:.3rem 0">Nenhum mestre encontrado.</div>';
    return;
  }

  results.innerHTML = users.map(u => `
    <div class="search-result-row">
      <span class="result-name"><i class="fa-solid fa-chess-king"></i> ${esc(u.nome)}</span>
      <button class="btn-assign-player"
        onclick="${selectFn}('${u.id}','${esc(u.nome)}')">Selecionar</button>
    </div>`).join('');
}

function searchMestreForMesa() { _searchMestre('nova-mesa-mestre-search', 'nova-mesa-mestre-results', 'selectMestreForMesa'); }
function searchMestreForEdit()  { _searchMestre('edit-mesa-mestre-search', 'edit-mesa-mestre-results', 'selectMestreForEdit'); }

function selectMestreForMesa(id, nome) {
  document.getElementById('nova-mesa-mestre-id').value = id;
  document.getElementById('nova-mesa-mestre-selected').textContent = `✓ ${nome}`;
  document.getElementById('nova-mesa-mestre-selected').style.display = 'block';
  document.getElementById('nova-mesa-mestre-results').innerHTML = '';
  document.getElementById('nova-mesa-mestre-search').value = nome;
}

function selectMestreForEdit(id, nome) {
  document.getElementById('edit-mesa-mestre-id').value = id;
  document.getElementById('edit-mesa-mestre-selected').textContent = `✓ Novo mestre: ${nome}`;
  document.getElementById('edit-mesa-mestre-selected').style.display = 'block';
  document.getElementById('edit-mesa-mestre-results').innerHTML = '';
  document.getElementById('edit-mesa-mestre-search').value = nome;
}

// ═══════════════════════════════════════════════════════════
//  FICHA
// ═══════════════════════════════════════════════════════════
function openFicha(mesaId, slotId, viewAs = 'jogador') {
  window.open(`${CHAR_SHEET_URL}?mesa=${mesaId}&slot=${slotId}&view=${viewAs}`, '_blank');
}

// ═══════════════════════════════════════════════════════════
//  MODAL HELPERS
// ═══════════════════════════════════════════════════════════
function openModal(html) {
  const root = document.getElementById('modal-root');
  root.innerHTML = `
    <div class="modal-overlay" id="modal-overlay" onclick="handleOverlayClick(event)">
      <div class="modal-box">${html}</div>
    </div>`;
}

function closeModal() {
  document.getElementById('modal-root').innerHTML = '';
}

function handleOverlayClick(e) {
  if (e.target.id === 'modal-overlay') closeModal();
}

// ═══════════════════════════════════════════════════════════
//  TOAST
// ═══════════════════════════════════════════════════════════
function showToast(msg, type = 'success') {
  const toast = document.getElementById('hub-toast');
  toast.textContent = msg;
  toast.className = `hub-toast show ${type}`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { toast.className = 'hub-toast'; }, 3000);
}

// ═══════════════════════════════════════════════════════════
//  UTILS
// ═══════════════════════════════════════════════════════════
function esc(str) {
  return String(str || '')
    .replace(/&/g,'&amp;').replace(/"/g,'&quot;')
    .replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function createElement(tag, className) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  return el;
}

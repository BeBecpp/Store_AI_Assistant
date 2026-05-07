/**
 * AI Store Assistant — embeddable widget
 *
 * Security: This file must NEVER contain API keys for OpenAI, Gemini, or the store.
 * Only the public backend base URL is allowed (window.AI_STORE_ASSISTANT_API), e.g. https://api.yourshop.com
 * All secrets stay in the FastAPI process (backend/.env).
 */
(function () {
  const STORAGE_KEY = 'asa_widget_prefs_v1';

  const API_BASE = (window.AI_STORE_ASSISTANT_API || '').trim();

  const root = document.createElement('div');
  root.id = 'asa-chat-root';
  root.innerHTML = `
    <button type="button" class="asa-fab" aria-label="Чат нээх">Чат</button>
    <div class="asa-shell" hidden>
      <section class="asa-panel" aria-live="polite">
        <header class="asa-titlebar" title="Чирээд зөөвөрлөнө">
          <span class="asa-title">Туслах</span>
          <div class="asa-win-actions">
            <button type="button" class="asa-icon-btn asa-btn-min" aria-label="Багасгах">−</button>
            <button type="button" class="asa-icon-btn asa-btn-max" aria-label="Томрох">□</button>
            <button type="button" class="asa-icon-btn asa-btn-close" aria-label="Хаах">×</button>
          </div>
        </header>
        <div class="asa-toolbar">
          <span class="asa-toolbar-label">Хэмжээ</span>
          <button type="button" class="asa-tiny" data-zoom="-1" aria-label="Бичвэр багасгах">A−</button>
          <button type="button" class="asa-tiny" data-zoom="1" aria-label="Бичвэр томруулах">A+</button>
        </div>
        <div class="asa-body">
          <div class="asa-messages"></div>
          <div class="asa-chips"></div>
          <form class="asa-form">
            <textarea rows="2" maxlength="1000" placeholder="Асуултаа бичнэ үү…" required></textarea>
            <button type="submit" class="asa-send">Илгээх</button>
          </form>
        </div>
        <div class="asa-resize" aria-hidden="true" title="Чирээд хэмжээ өөрчилнө"></div>
      </section>
    </div>
  `;
  document.body.appendChild(root);

  const shell = root.querySelector('.asa-shell');
  const panel = root.querySelector('.asa-panel');
  const fab = root.querySelector('.asa-fab');
  const titlebar = root.querySelector('.asa-titlebar');
  const btnMin = root.querySelector('.asa-btn-min');
  const btnMax = root.querySelector('.asa-btn-max');
  const btnClose = root.querySelector('.asa-btn-close');
  const messagesEl = root.querySelector('.asa-messages');
  const chipsEl = root.querySelector('.asa-chips');
  const form = root.querySelector('.asa-form');
  const textarea = form.querySelector('textarea');
  const resizeHandle = root.querySelector('.asa-resize');

  const WELCOME =
    'Сайн байна уу? Сэлбэг, үнэ, үлдэгдэл, байршил талаар асууж болно.';
  const CHIPS = [
    'Prius 30 асахгүй байна',
    'Аккумлятор байгаа юу?',
    'Prius 20 тос хаана байна?',
  ];

  let minimized = false;
  let maximized = false;
  let prevBounds = null;

  const prefs = loadPrefs();
  let msgScale = prefs.fontPx || 14;

  function loadPrefs() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function savePrefs() {
    const r = panel.getBoundingClientRect();
    const p = {
      left: r.left,
      top: r.top,
      width: r.width,
      height: r.height,
      fontPx: msgScale,
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
    } catch {
      /* ignore */
    }
  }

  function applyFont() {
    messagesEl.style.fontSize = `${msgScale}px`;
  }

  function applyInitialLayout() {
    panel.style.position = 'fixed';
    if (prefs.width && prefs.height) {
      panel.style.width = `${Math.min(prefs.width, window.innerWidth - 24)}px`;
      panel.style.height = `${Math.min(prefs.height, window.innerHeight - 100)}px`;
    } else {
      panel.style.width = `${Math.min(380, window.innerWidth - 24)}px`;
      panel.style.height = `${Math.min(520, Math.floor(window.innerHeight * 0.72))}px`;
    }
    if (typeof prefs.left === 'number' && typeof prefs.top === 'number') {
      panel.style.left = `${prefs.left}px`;
      panel.style.top = `${prefs.top}px`;
      panel.style.right = 'auto';
      panel.style.bottom = 'auto';
    } else {
      panel.style.left = 'auto';
      panel.style.top = 'auto';
      panel.style.right = '16px';
      panel.style.bottom = '72px';
    }
    applyFont();
  }

  function fmtMnt(n) {
    try {
      return `${Number(n).toLocaleString('mn-MN')}₮`;
    } catch {
      return `${n}₮`;
    }
  }

  function stockBadge(stock) {
    if (stock <= 0) return { cls: 'oos', label: 'Дууссан' };
    if (stock <= 3) return { cls: 'low', label: 'Бага' };
    return { cls: 'ok', label: 'Байна' };
  }

  function appendBubble(role, html) {
    const wrap = document.createElement('div');
    wrap.className = `asa-bubble asa-${role}`;
    wrap.innerHTML = html;
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setTyping(on) {
    let el = root.querySelector('.asa-typing');
    if (on) {
      if (!el) {
        el = document.createElement('div');
        el.className = 'asa-bubble asa-assistant asa-typing';
        el.textContent = 'Хариулж байна…';
        messagesEl.appendChild(el);
      }
    } else if (el) {
      el.remove();
    }
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderProducts(products) {
    if (!products || !products.length) return '';
    const cards = products
      .map((p) => {
        const st = stockBadge(p.stock);
        const cars = (p.compatible_cars || []).join(', ');
        return `
          <article class="asa-card">
            <h4>${escapeHtml(p.name)}</h4>
            <p class="asa-price">${fmtMnt(p.price)} <span class="asa-currency">${escapeHtml(
              p.currency || 'MNT'
            )}</span></p>
            <p class="asa-stockline"><span class="asa-badge ${st.cls}">${st.label}</span> · ${p.stock} ш</p>
            <p class="asa-meta">${escapeHtml(p.location)}</p>
            <p class="asa-meta">Тохирох: ${escapeHtml(cars || '—')}</p>
            <a class="asa-link" href="${escapeHtml(p.url)}">Дэлгэрэнгүй</a>
          </article>
        `;
      })
      .join('');
    return `<div class="asa-cards">${cards}</div>`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderAssistant(data) {
    const text = escapeHtml(data.reply).replace(/\n/g, '<br/>');
    appendBubble('assistant', `<div class="asa-text">${text}</div>${renderProducts(data.products)}`);
  }

  async function sendMessage(text) {
    setTyping(true);
    try {
      const url = `${API_BASE}/api/chat`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, lang: 'mn' }),
      });
      const raw = await res.text();
      let data;
      try {
        data = JSON.parse(raw);
      } catch {
        throw new Error(raw || 'Invalid JSON');
      }
      if (!res.ok) {
        const det = data.detail || data.message || `Алдаа ${res.status}`;
        throw new Error(typeof det === 'string' ? det : JSON.stringify(det));
      }
      renderAssistant(data);
    } catch (e) {
      const msg = e && e.message ? e.message : 'Алдаа';
      appendBubble(
        'assistant',
        `<div class="asa-text">Холболт амжилтгүй: ${escapeHtml(msg)}. Сервер асаалттай эсэхийг шалгана уу.</div>`
      );
    } finally {
      setTyping(false);
    }
  }

  /* --- Open / welcome --- */
  fab.addEventListener('click', () => {
    shell.hidden = !shell.hidden;
    fab.setAttribute('aria-expanded', shell.hidden ? 'false' : 'true');
    if (!shell.hidden && messagesEl.childElementCount === 0) {
      applyInitialLayout();
      appendBubble('assistant', `<div class="asa-text">${escapeHtml(WELCOME)}</div>`);
      chipsEl.innerHTML = '';
      CHIPS.forEach((c) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'asa-chip';
        b.textContent = c;
        b.addEventListener('click', () => {
          textarea.value = c;
          form.requestSubmit();
        });
        chipsEl.appendChild(b);
      });
    }
  });

  btnClose.addEventListener('click', () => {
    shell.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
    savePrefs();
  });

  btnMin.addEventListener('click', () => {
    minimized = !minimized;
    panel.classList.toggle('asa-minimized', minimized);
    if (minimized) maximized = false;
    panel.classList.remove('asa-maximized');
  });

  btnMax.addEventListener('click', () => {
    if (maximized) {
      maximized = false;
      panel.classList.remove('asa-maximized');
      if (prevBounds) {
        panel.style.width = `${prevBounds.w}px`;
        panel.style.height = `${prevBounds.h}px`;
        panel.style.left = `${prevBounds.l}px`;
        panel.style.top = `${prevBounds.t}px`;
        panel.style.right = 'auto';
        panel.style.bottom = 'auto';
      }
    } else {
      const r = panel.getBoundingClientRect();
      prevBounds = { w: r.width, h: r.height, l: r.left, t: r.top };
      maximized = true;
      minimized = false;
      panel.classList.remove('asa-minimized');
      panel.classList.add('asa-maximized');
    }
  });

  root.querySelectorAll('[data-zoom]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const d = Number(btn.getAttribute('data-zoom'));
      msgScale = Math.min(20, Math.max(12, msgScale + d * 1));
      applyFont();
      savePrefs();
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = textarea.value.trim();
    if (!text) return;
    appendBubble('user', `<div class="asa-text">${escapeHtml(text)}</div>`);
    textarea.value = '';
    await sendMessage(text);
    savePrefs();
  });

  /* --- Drag titlebar --- */
  let drag = null;
  titlebar.addEventListener('mousedown', (e) => {
    if (e.target.closest('button')) return;
    if (maximized) return;
    const rect = panel.getBoundingClientRect();
    drag = { x: e.clientX, y: e.clientY, l: rect.left, t: rect.top };
    panel.style.left = `${rect.left}px`;
    panel.style.top = `${rect.top}px`;
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
    e.preventDefault();
  });

  window.addEventListener('mousemove', (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    const dy = e.clientY - drag.y;
    let nl = drag.l + dx;
    let nt = drag.t + dy;
    nl = Math.max(8, Math.min(nl, window.innerWidth - panel.offsetWidth - 8));
    nt = Math.max(8, Math.min(nt, window.innerHeight - 48));
    panel.style.left = `${nl}px`;
    panel.style.top = `${nt}px`;
  });

  window.addEventListener('mouseup', () => {
    if (drag) {
      drag = null;
      savePrefs();
    }
  });

  /* --- Resize SE corner --- */
  let rz = null;
  resizeHandle.addEventListener('mousedown', (e) => {
    if (maximized) return;
    rz = { x: e.clientX, y: e.clientY, w: panel.offsetWidth, h: panel.offsetHeight };
    e.preventDefault();
    e.stopPropagation();
  });

  window.addEventListener('mousemove', (e) => {
    if (!rz) return;
    const dw = e.clientX - rz.x;
    const dh = e.clientY - rz.y;
    const nw = Math.min(Math.max(280, rz.w + dw), window.innerWidth - 16);
    const nh = Math.min(Math.max(320, rz.h + dh), window.innerHeight - 24);
    panel.style.width = `${nw}px`;
    panel.style.height = `${nh}px`;
  });

  window.addEventListener('mouseup', () => {
    if (rz) {
      rz = null;
      savePrefs();
    }
  });

  window.addEventListener('beforeunload', savePrefs);
})();

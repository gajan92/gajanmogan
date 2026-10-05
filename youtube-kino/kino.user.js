// ==UserScript==
// @name         kino for YouTube
// @namespace    https://github.com/gajan92/gajanmogan
// @version      0.1.0
// @description  Tabbed side panel, chapter frame timeline, comments sorted by moment, description cards, docked player, calm end screen and ambient color for the YouTube watch page. Needs kino.user.css.
// @author       gajan92
// @license      MIT
// @match        https://www.youtube.com/*
// @grant        none
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  const SETTINGS = {
    autoplayOff: true, // switch YouTube's autoplay off once each time YouTube loads
    dockOnScroll: true, // shrink the player into the side column when you scroll past it
    ambient: true, // tint the page with colors sampled from the video
    defaultTab: 'next', // 'next', 'comments' or 'chapters'
    scenesWithoutChapters: 8, // how many equal parts to show when a video has no chapters
  };

  /* ================================================================
     Pure helpers. No DOM here, so they can be tested in Node.
     ================================================================ */

  function formatTime(sec) {
    const total = Math.max(0, Math.floor(Number(sec) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = String(total % 60).padStart(2, '0');
    return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
  }

  function parseTimestamp(text) {
    const m = /(?:^|[^\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])/.exec(' ' + String(text == null ? '' : text));
    if (!m) return null;
    const h = m[1] ? Number(m[1]) : 0;
    const min = Number(m[2]);
    const sec = Number(m[3]);
    if (sec > 59 || (m[1] && min > 59)) return null;
    return h * 3600 + min * 60 + sec;
  }

  function timeFromHref(href) {
    const m = /[?&#]t=([0-9hms]+)/.exec(String(href || ''));
    if (!m) return null;
    const v = m[1];
    if (/^\d+s?$/.test(v)) return parseInt(v, 10);
    const p = /^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/.exec(v);
    if (!p || !(p[1] || p[2] || p[3])) return null;
    return (Number(p[1]) || 0) * 3600 + (Number(p[2]) || 0) * 60 + (Number(p[3]) || 0);
  }

  // Walks a JSON tree and returns the objects that pass `test`, without descending into matches.
  function findAll(root, test, max) {
    const limit = max || 100;
    const out = [];
    const stack = [root];
    const seen = new Set();
    let steps = 0;
    while (stack.length && out.length < limit && steps++ < 600000) {
      const node = stack.pop();
      if (!node || typeof node !== 'object' || seen.has(node)) continue;
      seen.add(node);
      let hit = false;
      try {
        hit = !!test(node);
      } catch (e) {
        hit = false;
      }
      if (hit) {
        out.push(node);
        continue;
      }
      const values = Array.isArray(node) ? node : Object.keys(node).map((k) => node[k]);
      for (let i = values.length - 1; i >= 0; i--) {
        const v = values[i];
        if (v && typeof v === 'object') stack.push(v);
      }
    }
    return out;
  }

  function textOf(t) {
    if (!t) return '';
    if (typeof t === 'string') return t;
    if (t.simpleText) return t.simpleText;
    if (Array.isArray(t.runs)) return t.runs.map((r) => r.text || '').join('');
    if (typeof t.content === 'string') return t.content;
    return '';
  }

  function pickThumb(t) {
    const list = t && Array.isArray(t.thumbnails) ? t.thumbnails : [];
    if (!list.length) return '';
    const sorted = list.slice().sort((a, b) => (a.width || 0) - (b.width || 0));
    const good = sorted.find((x) => (x.width || 0) >= 240) || sorted[sorted.length - 1];
    return good.url || '';
  }

  function cleanChapters(list) {
    const byStart = new Map();
    for (const c of list) {
      if (!c || !c.title || !isFinite(c.start) || c.start < 0) continue;
      const key = Math.round(c.start);
      if (!byStart.has(key)) byStart.set(key, { title: String(c.title).trim(), start: Number(c.start), thumb: c.thumb || '' });
    }
    return Array.from(byStart.values()).sort((a, b) => a.start - b.start);
  }

  function extractChapters(data) {
    if (!data) return [];
    let list = [];
    const bar = findAll(data, (n) => n.multiMarkersPlayerBarRenderer, 1)[0];
    const map = bar && bar.multiMarkersPlayerBarRenderer.markersMap;
    if (Array.isArray(map)) {
      const entry =
        map.find((e) => e.key === 'DESCRIPTION_CHAPTERS') ||
        map.find((e) => e.key === 'AUTO_CHAPTERS') ||
        map.find((e) => e.value && Array.isArray(e.value.chapters));
      if (entry && entry.value && Array.isArray(entry.value.chapters)) {
        list = entry.value.chapters
          .map((c) => c.chapterRenderer)
          .filter(Boolean)
          .map((c) => ({ title: textOf(c.title), start: Number(c.timeRangeStartMillis) / 1000, thumb: pickThumb(c.thumbnail) }));
      }
    }
    if (!list.length) {
      list = findAll(data, (n) => n.chapterRenderer && n.chapterRenderer.timeRangeStartMillis != null, 500)
        .map((n) => n.chapterRenderer)
        .map((c) => ({ title: textOf(c.title), start: Number(c.timeRangeStartMillis) / 1000, thumb: pickThumb(c.thumbnail) }));
    }
    if (!list.length) {
      list = findAll(data, (n) => n.macroMarkersListItemRenderer, 500)
        .map((n) => n.macroMarkersListItemRenderer)
        .map((m) => {
          const ep = m.onTap && m.onTap.watchEndpoint;
          const start = ep && ep.startTimeSeconds != null ? Number(ep.startTimeSeconds) : parseTimestamp(textOf(m.timeDescription));
          return { title: textOf(m.title), start, thumb: pickThumb(m.thumbnail) };
        });
    }
    return cleanChapters(list);
  }

  // "Most replayed" markers. YouTube has used two shapes for these.
  function extractHeat(data) {
    if (!data) return [];
    let out = findAll(data, (n) => typeof n.intensityScoreNormalized === 'number' && n.startMillis != null, 5000).map((m) => ({
      start: Number(m.startMillis),
      dur: Number(m.durationMillis) || 0,
      value: m.intensityScoreNormalized,
    }));
    if (!out.length) {
      out = findAll(data, (n) => n.heatMarkerRenderer, 5000)
        .map((n) => n.heatMarkerRenderer)
        .map((h) => ({
          start: Number(h.timeRangeStartMillis),
          dur: Number(h.markerDurationMillis) || 0,
          value: Number(h.heatMarkerIntensityScoreNormalized),
        }));
    }
    return out.filter((m) => isFinite(m.start) && isFinite(m.value)).sort((a, b) => a.start - b.start);
  }

  // Path in a 1000 x 100 box, drawn over the timeline.
  function heatPath(markers, totalMs) {
    if (!markers || !markers.length || !totalMs) return '';
    return markers
      .map((m, i) => {
        const x = ((m.start + m.dur / 2) / totalMs) * 1000;
        const y = 100 - Math.max(0, Math.min(1, m.value)) * 92;
        return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
      })
      .join(' ');
  }

  // YouTube's preview sprites: "baseUrl|w#h#count#cols#rows#intervalMs#name#sigh|..."
  function parseStoryboard(spec) {
    if (!spec || typeof spec !== 'string') return null;
    const parts = spec.split('|');
    const base = parts.shift();
    const levels = parts
      .map((p, L) => {
        const f = p.split('#');
        return { L, w: +f[0], h: +f[1], count: +f[2], cols: +f[3], rows: +f[4], interval: +f[5], name: f[6] || '', sigh: f[7] || '' };
      })
      .filter((l) => l.w > 0 && l.count > 0 && l.cols > 0 && l.rows > 0);
    if (!base || !levels.length) return null;
    return Object.assign({ base }, levels[levels.length - 1]);
  }

  function storyboardFrame(sb, t, durationSec) {
    const perSheet = sb.cols * sb.rows;
    const interval = sb.interval > 0 ? sb.interval : (durationSec * 1000) / sb.count;
    const i = Math.max(0, Math.min(sb.count - 1, Math.floor((t * 1000) / Math.max(1, interval))));
    const sheet = Math.floor(i / perSheet);
    const k = i % perSheet;
    const framesInSheet = Math.min(perSheet, sb.count - sheet * perSheet);
    const rowsInSheet = Math.max(1, Math.ceil(framesInSheet / sb.cols));
    const col = k % sb.cols;
    const row = Math.floor(k / sb.cols);
    let url = sb.base.split('$L').join(String(sb.L)).split('$N').join(sb.name.split('$M').join(String(sheet)));
    if (sb.sigh) url += (url.indexOf('?') >= 0 ? '&' : '?') + 'sigh=' + encodeURIComponent(sb.sigh);
    const x = sb.cols > 1 ? (col / (sb.cols - 1)) * 100 : 0;
    const y = rowsInSheet > 1 ? (row / (rowsInSheet - 1)) * 100 : 0;
    return { url, size: `${sb.cols * 100}% ${rowsInSheet * 100}%`, position: `${x}% ${y}%` };
  }

  // Turns the description into link cards and short "Label: value" credits.
  function parseDescription(text) {
    const links = [];
    const credits = [];
    if (!text) return { links, credits };
    const urlRe = /https?:\/\/[^\s<>"')\]]+/g;
    const trimSep = (s) => s.replace(/^[\s:\-–—|→»•·>]+/, '').replace(/[\s:\-–—|→»•·>]+$/, '').trim();
    const seen = new Set();
    let prev = '';
    for (const raw of String(text).split(/\r?\n/)) {
      const line = raw.trim();
      if (!line) {
        prev = '';
        continue;
      }
      const urls = line.match(urlRe);
      if (urls) {
        let label = trimSep(line.replace(urlRe, ' ').replace(/\s+/g, ' '));
        if (!label && prev && !/https?:\/\//.test(prev)) label = trimSep(prev);
        for (const u of urls) {
          const url = u.replace(/[.,;:!?]+$/, '');
          if (seen.has(url)) continue;
          let host = '';
          try {
            host = new URL(url).hostname.replace(/^www\./, '');
          } catch (e) {
            continue;
          }
          seen.add(url);
          links.push({ label: (urls.length > 1 ? '' : label) || host, url, host });
        }
      } else if (!/^\(?\d{1,2}:\d{2}/.test(line) && !/^#/.test(line)) {
        const m = /^([A-Za-zÀ-ÿ][\wÀ-ÿ &'’/.+]{0,28}?)\s*[:：]\s+(.{1,90})$/.exec(line);
        if (m && m[1].trim().split(/\s+/).length <= 4) credits.push({ label: m[1].trim(), value: m[2].trim() });
      }
      prev = line;
    }
    return { links: links.slice(0, 8), credits: credits.slice(0, 8) };
  }

  function rgbToHsl(r, g, b) {
    r /= 255;
    g /= 255;
    b /= 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return [0, 0, l];
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h;
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    return [h / 6, s, l];
  }

  function hslToRgb(h, s, l) {
    if (s === 0) return [l * 255, l * 255, l * 255];
    const hue = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    return [hue(p, q, h + 1 / 3) * 255, hue(p, q, h) * 255, hue(p, q, h - 1 / 3) * 255];
  }

  // Picks the most colorful sampled region and lifts it into a readable accent.
  function accentFrom(regions) {
    let best = null;
    for (const [r, g, b] of regions) {
      const [h, s, l] = rgbToHsl(r, g, b);
      const score = s * (1 - Math.abs(2 * l - 1));
      if (!best || score > best.score) best = { h, s, score };
    }
    if (!best || best.score < 0.08) return null;
    const rgb = hslToRgb(best.h, Math.min(1, Math.max(best.s, 0.5)), 0.72);
    return `rgb(${rgb.map((v) => Math.round(v)).join(', ')})`;
  }

  const api = { formatTime, parseTimestamp, timeFromHref, findAll, extractChapters, extractHeat, heatPath, parseStoryboard, storyboardFrame, parseDescription, accentFrom };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
    return;
  }
  if (typeof document === 'undefined') return;

  /* ================================================================
     Page code
     ================================================================ */

  // Violentmonkey runs this in the page, or in a sandbox if the page blocks that. Both work.
  const PAGE = window.wrappedJSObject || window;
  const unwrap = (o) => (o && o.wrappedJSObject) || o;
  const root = document.documentElement;

  const store = {
    get(key, fallback) {
      try {
        const v = localStorage.getItem('kino.' + key);
        return v == null ? fallback : JSON.parse(v);
      } catch (e) {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem('kino.' + key, JSON.stringify(value));
      } catch (e) {
        /* storage blocked: settings just won't stick */
      }
    },
  };

  const state = {
    token: 0,
    videoId: '',
    duration: 0,
    chapters: [],
    isScenes: false,
    heat: [],
    sb: null,
    segs: [],
    lastNav: null,
    tab: store.get('tab', SETTINGS.defaultTab),
    byMoment: store.get('byMoment', true),
    onlyT: store.get('onlyT', false),
    autoplayDone: false,
    ambientBroken: false,
    playerOut: false,
  };

  const origin = new Map();
  const hookedVideos = new WeakSet();

  const $ = (sel, scope) => (scope || document).querySelector(sel);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function waitFor(fn, timeout) {
    const end = Date.now() + (timeout || 10000);
    while (Date.now() < end) {
      const v = fn();
      if (v) return v;
      await sleep(200);
    }
    return null;
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k === 'style') Object.assign(node.style, v);
      else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : String(v));
    }
    for (const c of children.flat()) if (c != null && c !== false) node.append(c);
    return node;
  }

  function svgEl(tag, attrs) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, String(v));
    return node;
  }

  function toPlain(obj) {
    if (!obj) return null;
    try {
      return JSON.parse(PAGE.JSON.stringify(obj));
    } catch (e) {
      return null;
    }
  }

  const isWatch = () => location.pathname === '/watch';
  const currentVideoId = () => new URLSearchParams(location.search).get('v') || '';
  const getFlexy = () => document.querySelector('ytd-watch-flexy');
  const getPlayerNode = () => document.querySelector('#movie_player');
  const getPlayer = () => {
    const n = getPlayerNode();
    return n ? unwrap(n) : null;
  };
  const getVideo = () => document.querySelector('#movie_player video.html5-main-video') || document.querySelector('#movie_player video');
  const adShowing = () => {
    const p = getPlayerNode();
    return !!(p && p.classList.contains('ad-showing'));
  };

  /* ---------- Reading YouTube's data ---------- */

  function dataVideoId(data) {
    if (!data) return '';
    const direct = data.currentVideoEndpoint && data.currentVideoEndpoint.watchEndpoint;
    if (direct && direct.videoId) return direct.videoId;
    const hit = findAll(data, (n) => n.currentVideoEndpoint, 1)[0];
    const ep = hit && hit.currentVideoEndpoint.watchEndpoint;
    return (ep && ep.videoId) || '';
  }

  function getWatchData(vid) {
    const sources = [];
    const nav = unwrap(state.lastNav);
    if (nav && nav.response) {
      const r = unwrap(nav.response);
      sources.push(() => r.response || r);
    }
    const fx = unwrap(getFlexy());
    if (fx) {
      sources.push(() => fx.data);
      sources.push(() => fx.__data && fx.__data.data);
    }
    sources.push(() => PAGE.ytInitialData);
    for (const get of sources) {
      let raw = null;
      try {
        raw = get();
      } catch (e) {
        raw = null;
      }
      if (!raw) continue;
      const plain = toPlain(raw);
      if (plain && dataVideoId(plain) === vid) return plain;
    }
    return null;
  }

  function getPlayerResponse(vid) {
    const p = getPlayer();
    const nav = unwrap(state.lastNav);
    const sources = [
      () => nav && nav.response && unwrap(nav.response).playerResponse,
      () => p && typeof p.getPlayerResponse === 'function' && p.getPlayerResponse(),
      () => PAGE.ytInitialPlayerResponse,
    ];
    for (const get of sources) {
      let raw = null;
      try {
        raw = get();
      } catch (e) {
        raw = null;
      }
      if (!raw) continue;
      const plain = toPlain(raw);
      if (plain && plain.videoDetails && plain.videoDetails.videoId === vid) return plain;
    }
    return null;
  }

  function chaptersFromDom() {
    const list = [];
    document.querySelectorAll('ytd-watch-flexy ytd-macro-markers-list-item-renderer').forEach((item) => {
      const title = item.querySelector('#details h4, h4');
      const time = item.querySelector('#time');
      const img = item.querySelector('img');
      const start = parseTimestamp(time && time.textContent);
      if (title && start != null) list.push({ title: title.textContent.trim(), start, thumb: (img && (img.currentSrc || img.src)) || '' });
    });
    return cleanChapters(list);
  }

  function makeScenes(duration, n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const start = (duration * i) / n;
      out.push({ title: formatTime(start), start, thumb: '' });
    }
    return out;
  }

  /* ---------- Player actions ---------- */

  function seek(t) {
    const p = getPlayer();
    try {
      if (p && typeof p.seekTo === 'function') {
        p.seekTo(t, true);
        return;
      }
    } catch (e) {
      /* fall through to the video element */
    }
    const v = getVideo();
    if (v) v.currentTime = t;
  }

  function play() {
    const p = getPlayer();
    try {
      if (p && typeof p.playVideo === 'function') {
        p.playVideo();
        return;
      }
    } catch (e) {
      /* fall through */
    }
    const v = getVideo();
    if (v) v.play();
  }

  const autoplayToggle = () => document.querySelector('#movie_player .ytp-autonav-toggle-button');
  const autoplayIsOn = () => {
    const t = autoplayToggle();
    return !!t && t.getAttribute('aria-checked') === 'true';
  };

  function setAutoplay(on) {
    const t = autoplayToggle();
    if (!t) return false;
    if (autoplayIsOn() !== on) (t.closest('button') || t).click();
    setTimeout(syncAutoplaySwitch, 200);
    return true;
  }

  function syncAutoplaySwitch() {
    const sw = $('#kino-panel .kino-switch');
    if (!sw) return;
    sw.setAttribute('aria-checked', String(autoplayIsOn()));
    sw.disabled = !autoplayToggle();
  }

  /* ---------- Side panel ---------- */

  const TABS = [
    ['next', 'Up next'],
    ['comments', 'Comments'],
    ['chapters', 'Chapters'],
  ];

  function buildPanel() {
    const tablist = el('div', { class: 'kino-tabs', role: 'tablist', 'aria-label': 'Side panel' });
    const views = el('div', { class: 'kino-views' });
    for (const [id, label] of TABS) {
      tablist.append(
        el('button', {
          type: 'button',
          class: 'kino-tab',
          role: 'tab',
          id: 'kino-tab-' + id,
          'aria-controls': 'kino-view-' + id,
          'aria-selected': 'false',
          tabindex: '-1',
          'data-tab': id,
          text: label,
          onclick: () => setTab(id),
        })
      );
      views.append(el('div', { class: 'kino-view', id: 'kino-view-' + id, role: 'tabpanel', 'aria-labelledby': 'kino-tab-' + id, tabindex: '0', 'data-view': id }));
    }
    tablist.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      const ids = TABS.map((t) => t[0]);
      const i = ids.indexOf(state.tab);
      const next = ids[(i + (e.key === 'ArrowRight' ? 1 : ids.length - 1)) % ids.length];
      setTab(next);
      const btn = $('#kino-tab-' + next);
      if (btn) btn.focus();
      e.preventDefault();
      e.stopPropagation();
    });

    const comments = views.querySelector('#kino-view-comments');
    comments.append(
      el(
        'div',
        { class: 'kino-cbar' },
        el(
          'div',
          { class: 'kino-seg-group', role: 'group', 'aria-label': 'Comment order' },
          el('button', { type: 'button', class: 'kino-seg-btn', 'data-order': 'youtube', 'aria-pressed': 'false', text: 'YouTube order', onclick: () => setByMoment(false) }),
          el('button', {
            type: 'button',
            class: 'kino-seg-btn',
            'data-order': 'moment',
            'aria-pressed': 'false',
            title: 'Sorts the loaded comments by the time they mention',
            text: 'By moment',
            onclick: () => setByMoment(true),
          })
        ),
        el('label', { class: 'kino-check' }, el('input', { type: 'checkbox', class: 'kino-only-t', onchange: (e) => setOnlyT(e.target.checked) }), 'Only with a timestamp')
      ),
      el('div', { class: 'kino-comments-slot' })
    );

    const chapters = views.querySelector('#kino-view-chapters');
    chapters.append(
      el('p', { class: 'kino-note', hidden: true }),
      el('div', { class: 'kino-chapters' }),
      el('button', { type: 'button', class: 'kino-link-btn', hidden: true, text: 'Open the transcript', onclick: openTranscript })
    );

    const foot = el(
      'div',
      { class: 'kino-foot' },
      el('span', { id: 'kino-ap-label', text: 'Autoplay next video' }),
      el('button', { type: 'button', class: 'kino-switch', role: 'switch', 'aria-checked': 'false', 'aria-labelledby': 'kino-ap-label', onclick: () => setAutoplay(!autoplayIsOn()) })
    );

    return el('section', { id: 'kino-panel', 'aria-label': 'Up next, comments and chapters' }, tablist, views, foot);
  }

  function setTab(id) {
    if (!TABS.some((t) => t[0] === id)) id = 'next';
    state.tab = id;
    store.set('tab', id);
    const panel = $('#kino-panel');
    if (!panel) return;
    panel.querySelectorAll('.kino-tab').forEach((b) => {
      const on = b.getAttribute('data-tab') === id;
      b.setAttribute('aria-selected', String(on));
      b.tabIndex = on ? 0 : -1;
    });
    panel.querySelectorAll('.kino-view').forEach((v) => v.classList.toggle('is-active', v.getAttribute('data-view') === id));
    if (id === 'comments') processComments();
  }

  function moveInto(node, target) {
    if (!node || !target || node.parentElement === target) return;
    if (!origin.has(node) && !node.closest('#kino-panel')) origin.set(node, { parent: node.parentElement, next: node.nextSibling });
    target.append(node);
  }

  function restore(node) {
    const o = node && origin.get(node);
    if (!o || !o.parent || !node.closest('#kino-panel')) return;
    o.parent.insertBefore(node, o.next && o.next.parentNode === o.parent ? o.next : null);
  }

  // Puts YouTube's own "Up next" list and comments inside the panel while the page has two columns.
  function placeNodes() {
    const flexy = getFlexy();
    const panel = $('#kino-panel');
    if (!flexy || !panel) return;
    const comments = flexy.querySelector('ytd-comments#comments');
    if (flexy.hasAttribute('is-two-columns_')) {
      const related = flexy.querySelector('#related');
      if (related && !related.closest('#below')) moveInto(related, panel.querySelector('#kino-view-next'));
      moveInto(comments, panel.querySelector('#kino-view-comments .kino-comments-slot'));
      panel.hidden = false;
    } else {
      restore(comments);
      panel.hidden = true;
    }
  }

  let flexyObs = null;
  let flexyObserved = null;
  let placeTimer = 0;
  function observeFlexy(flexy) {
    if (flexyObserved === flexy) return;
    if (flexyObs) flexyObs.disconnect();
    flexyObserved = flexy;
    flexyObs = new MutationObserver(() => {
      clearTimeout(placeTimer);
      placeTimer = setTimeout(() => {
        placeNodes();
        evaluateDock();
      }, 350);
    });
    flexyObs.observe(flexy, { attributes: true, attributeFilter: ['is-two-columns_', 'theater', 'fullscreen'] });
    const secInner = flexy.querySelector('#secondary-inner');
    if (secInner) flexyObs.observe(secInner, { childList: true });
  }

  /* ---------- Comments sorted by moment ---------- */

  function threadInfo(th) {
    const body = th.querySelector('#comment #content-text') || th.querySelector('#content-text');
    if (!body) return { key: '', t: null };
    const key = (body.textContent || '').slice(0, 120);
    let t = null;
    for (const a of body.querySelectorAll('a[href]')) {
      const v = timeFromHref(a.getAttribute('href'));
      if (v != null) {
        t = v;
        break;
      }
    }
    if (t == null) t = parseTimestamp(body.textContent);
    return { key, t };
  }

  function processComments() {
    const panel = $('#kino-panel');
    if (!panel) return;
    panel.classList.toggle('kino-by-moment', state.byMoment);
    panel.classList.toggle('kino-only-t', state.onlyT);
    panel.querySelectorAll('#kino-view-comments ytd-comment-thread-renderer').forEach((th) => {
      const info = threadInfo(th);
      if (th.getAttribute('data-kino-key') !== info.key) {
        th.setAttribute('data-kino-key', info.key);
        th.setAttribute('data-kino-t', info.t == null ? '' : String(info.t));
      }
      const raw = th.getAttribute('data-kino-t');
      const t = raw === '' || raw == null ? null : Number(raw);
      th.classList.toggle('kino-has-t', t != null);
      th.style.order = state.byMoment ? String(t == null ? 1000000 : Math.round(t)) : '';
    });
    panel.querySelectorAll('#kino-view-comments ytd-continuation-item-renderer').forEach((c) => {
      c.style.order = state.byMoment ? '2000000' : '';
    });
  }

  function setByMoment(on, silent) {
    state.byMoment = !!on;
    if (!silent) store.set('byMoment', state.byMoment);
    document.querySelectorAll('#kino-panel .kino-seg-btn').forEach((b) => {
      b.setAttribute('aria-pressed', String((b.getAttribute('data-order') === 'moment') === state.byMoment));
    });
    processComments();
  }

  function setOnlyT(on, silent) {
    state.onlyT = !!on;
    if (!silent) store.set('onlyT', state.onlyT);
    const box = $('#kino-panel .kino-only-t');
    if (box) box.checked = state.onlyT;
    processComments();
  }

  let commentsObs = null;
  let commentsTimer = 0;
  function watchComments() {
    const view = $('#kino-view-comments');
    if (!view || commentsObs) return;
    commentsObs = new MutationObserver(() => {
      clearTimeout(commentsTimer);
      commentsTimer = setTimeout(processComments, 250);
    });
    commentsObs.observe(view, { childList: true, subtree: true });
  }

  function markNear(t) {
    document.querySelectorAll('#kino-view-comments ytd-comment-thread-renderer[data-kino-t]').forEach((th) => {
      const raw = th.getAttribute('data-kino-t');
      th.classList.toggle('kino-near', raw !== '' && Math.abs(Number(raw) - t) <= 20);
    });
  }

  /* ---------- Chapters tab and timeline ---------- */

  function chapterEnd(i) {
    return i + 1 < state.chapters.length ? state.chapters[i + 1].start : state.duration;
  }

  function currentIndex(t) {
    let idx = -1;
    state.chapters.forEach((c, i) => {
      if (c.start <= t + 0.25) idx = i;
    });
    return idx;
  }

  function applyFrame(box, c, at) {
    if (c.thumb) {
      box.style.backgroundImage = 'url("' + c.thumb.replace(/"/g, '%22') + '")';
      return;
    }
    if (state.sb && state.duration) {
      const f = storyboardFrame(state.sb, at, state.duration);
      box.prepend(el('span', { class: 'kino-sb', style: { backgroundImage: 'url("' + f.url + '")', backgroundSize: f.size, backgroundPosition: f.position } }));
    }
  }

  function findTranscriptButton() {
    return document.querySelector('ytd-watch-flexy ytd-video-description-transcript-section-renderer button');
  }

  function openTranscript() {
    const b = findTranscriptButton();
    if (b) b.click();
  }

  function renderChapters() {
    const view = $('#kino-view-chapters');
    if (!view) return;
    const list = view.querySelector('.kino-chapters');
    const note = view.querySelector('.kino-note');
    const transcript = view.querySelector('.kino-link-btn');
    note.hidden = !state.isScenes;
    note.textContent = state.isScenes ? `This video has no chapters, so here it is in ${state.chapters.length} equal parts.` : '';
    list.replaceChildren(
      ...state.chapters.map((c, i) => {
        const thumb = el('span', { class: 'kino-thumb' }, el('span', { class: 'kino-bar' }));
        applyFrame(thumb, c, c.start + Math.min(5, (chapterEnd(i) - c.start) / 2));
        return el(
          'button',
          { type: 'button', class: 'kino-ch', onclick: () => seek(c.start) },
          thumb,
          el(
            'span',
            { class: 'kino-ch-text' },
            el('span', { class: 'kino-ch-meta', text: String(i + 1).padStart(2, '0') + ' · ' + formatTime(c.start) }),
            el('span', { class: 'kino-ch-title', text: c.title })
          )
        );
      })
    );
    if (!state.chapters.length) list.append(el('p', { class: 'kino-note', text: 'Chapters show up once the video has loaded.' }));
    transcript.hidden = !findTranscriptButton();
  }

  function buildTimeline() {
    const track = el('div', { class: 'kino-tl-track', role: 'slider', tabindex: '0', 'aria-label': 'Seek through the video', 'aria-valuemin': '0' });
    track.addEventListener('click', (e) => seek(xToTime(track, e.clientX)));
    track.addEventListener('mousemove', (e) => {
      const hover = track.querySelector('.kino-hover');
      if (!hover) return;
      const t = xToTime(track, e.clientX);
      const c = state.chapters[currentIndex(t)];
      hover.style.left = e.clientX - track.getBoundingClientRect().left + 'px';
      hover.textContent = formatTime(t) + (c && !state.isScenes ? ' · ' + c.title : '');
    });
    track.addEventListener('keydown', (e) => {
      const v = getVideo();
      if (!v) return;
      const step = e.shiftKey ? 30 : 5;
      let t = null;
      if (e.key === 'ArrowRight') t = v.currentTime + step;
      else if (e.key === 'ArrowLeft') t = v.currentTime - step;
      else if (e.key === 'Home') t = 0;
      else if (e.key === 'End') t = Math.max(0, state.duration - 1);
      if (t == null) return;
      seek(Math.max(0, Math.min(state.duration || t, t)));
      e.preventDefault();
      e.stopPropagation();
    });
    return el(
      'section',
      { id: 'kino-timeline', 'aria-label': 'Chapter timeline', hidden: true },
      el('div', { class: 'kino-tl-head' }, el('span', { class: 'kino-tl-caption' }), el('span', { class: 'kino-tl-time' })),
      track
    );
  }

  function renderTimeline() {
    const tl = $('#kino-timeline');
    if (!tl) return;
    const track = tl.querySelector('.kino-tl-track');
    const total = state.duration;
    if (!total || !isFinite(total) || !state.chapters.length) {
      tl.hidden = true;
      state.segs = [];
      return;
    }
    tl.hidden = false;
    track.replaceChildren();
    state.segs = state.chapters.map((c, i) => {
      const end = chapterEnd(i);
      const len = Math.max(1, end - c.start);
      const seg = el('div', { class: 'kino-seg', title: formatTime(c.start) + '  ' + c.title, style: { flexGrow: String(len) } });
      applyFrame(seg, c, c.start + len / 2);
      const dim = el('span', { class: 'kino-seg-dim' });
      seg.append(dim, el('span', { class: 'kino-seg-label' }, el('span', { class: 'kino-seg-num', text: String(i + 1).padStart(2, '0') }), c.title));
      track.append(seg);
      return { el: seg, dim, start: c.start, end };
    });
    if (state.heat.length) {
      const svg = svgEl('svg', { class: 'kino-heat', viewBox: '0 0 1000 100', preserveAspectRatio: 'none', 'aria-hidden': 'true' });
      svg.append(svgEl('path', { d: heatPath(state.heat, total * 1000) }));
      track.append(svg);
    }
    track.append(el('span', { class: 'kino-playhead' }), el('span', { class: 'kino-hover' }));
    track.setAttribute('aria-valuemax', String(Math.round(total)));
    tl.querySelector('.kino-tl-caption').textContent =
      (state.isScenes ? 'No chapters, so this is the video in equal parts' : 'Chapters') + (state.heat.length ? '. The white line shows what people replay most.' : '');
    updateTime();
  }

  function timeToX(t) {
    const segs = state.segs;
    for (let i = 0; i < segs.length; i++) {
      const s = segs[i];
      if (t < s.end || i === segs.length - 1) {
        const f = Math.max(0, Math.min(1, (t - s.start) / Math.max(1, s.end - s.start)));
        return s.el.offsetLeft + f * s.el.offsetWidth;
      }
    }
    return 0;
  }

  function xToTime(track, clientX) {
    const x = clientX - track.getBoundingClientRect().left;
    for (const s of state.segs) {
      const left = s.el.offsetLeft;
      const width = s.el.offsetWidth;
      if (x <= left + width + 1.5) {
        const f = Math.max(0, Math.min(1, (x - left) / Math.max(1, width)));
        return s.start + f * (s.end - s.start);
      }
    }
    return state.duration;
  }

  let lastNear = 0;
  function updateTime() {
    const v = getVideo();
    if (!v || adShowing() || !isWatch()) return;
    const t = v.currentTime || 0;
    const tl = $('#kino-timeline');
    if (tl && !tl.hidden && state.segs.length) {
      const head = tl.querySelector('.kino-playhead');
      if (head) head.style.left = timeToX(t) + 'px';
      state.segs.forEach((s) => {
        const f = Math.max(0, Math.min(1, (t - s.start) / Math.max(1, s.end - s.start)));
        s.dim.style.left = f * 100 + '%';
      });
      const time = tl.querySelector('.kino-tl-time');
      if (time) time.textContent = formatTime(t) + ' / ' + formatTime(state.duration);
      const track = tl.querySelector('.kino-tl-track');
      track.setAttribute('aria-valuenow', String(Math.round(t)));
      track.setAttribute('aria-valuetext', formatTime(t));
    }
    const idx = currentIndex(t);
    document.querySelectorAll('#kino-view-chapters .kino-ch').forEach((b, i) => {
      b.classList.toggle('is-current', i === idx);
      const bar = b.querySelector('.kino-bar');
      const c = state.chapters[i];
      if (bar && c) bar.style.width = Math.max(0, Math.min(1, (t - c.start) / Math.max(1, chapterEnd(i) - c.start))) * 100 + '%';
    });
    if (Date.now() - lastNear > 1000) {
      lastNear = Date.now();
      markNear(t);
    }
  }

  /* ---------- Description links and credits ---------- */

  function renderDetails(description) {
    const flexy = getFlexy();
    const meta = flexy && flexy.querySelector('#below ytd-watch-metadata');
    if (!meta) return;
    let box = $('#kino-details');
    if (!box) box = el('section', { id: 'kino-details', 'aria-label': 'Links and credits from the description' });
    if (box.previousElementSibling !== meta) meta.after(box);
    const { links, credits } = parseDescription(description || '');
    box.replaceChildren();
    box.hidden = !links.length && !credits.length;
    if (links.length) {
      box.append(
        el('h2', { class: 'kino-h', text: 'Links from the description' }),
        el(
          'div',
          { class: 'kino-links' },
          links.map((l) =>
            el('a', { class: 'kino-link', href: l.url, target: '_blank', rel: 'noopener noreferrer' }, el('span', { class: 'kino-link-label', text: l.label }), el('span', { class: 'kino-link-host', text: l.host }))
          )
        )
      );
    }
    if (credits.length) {
      box.append(
        el('h2', { class: 'kino-h', text: 'Credits' }),
        el(
          'dl',
          { class: 'kino-credits' },
          credits.map((c) => el('div', null, el('dt', { text: c.label }), el('dd', { text: c.value })))
        )
      );
    }
  }

  /* ---------- Ambient color ---------- */

  const sampler = document.createElement('canvas');
  sampler.width = 24;
  sampler.height = 14;
  let samplerCtx = null;
  let sampleTimer = 0;

  function ensureAmbient() {
    if (!SETTINGS.ambient) return;
    if (!$('#kino-ambient')) {
      document.body.prepend(
        el('div', { id: 'kino-ambient', 'aria-hidden': 'true' }, el('span', { class: 'kino-blob kino-b1' }), el('span', { class: 'kino-blob kino-b2' }), el('span', { class: 'kino-blob kino-b3' }))
      );
    }
    if (!sampleTimer) sampleTimer = setInterval(sampleColors, 1000);
  }

  function sampleColors() {
    if (state.ambientBroken || document.hidden || !isWatch()) return;
    const v = getVideo();
    if (!v || v.readyState < 2 || adShowing()) return;
    try {
      samplerCtx = samplerCtx || sampler.getContext('2d', { willReadFrequently: true });
      samplerCtx.drawImage(v, 0, 0, 24, 14);
      const d = samplerCtx.getImageData(0, 0, 24, 14).data;
      const regions = [
        [0, 8],
        [8, 16],
        [16, 24],
      ].map(([x0, x1]) => {
        let r = 0;
        let g = 0;
        let b = 0;
        let n = 0;
        for (let y = 0; y < 14; y++) {
          for (let x = x0; x < x1; x++) {
            const i = (y * 24 + x) * 4;
            r += d[i];
            g += d[i + 1];
            b += d[i + 2];
            n++;
          }
        }
        return [r / n, g / n, b / n];
      });
      regions.forEach((c, i) => root.style.setProperty('--kino-amb-' + (i + 1), `rgb(${c.map((x) => Math.round(x)).join(', ')})`));
      const accent = accentFrom(regions);
      if (accent) root.style.setProperty('--kino-accent', accent);
    } catch (e) {
      // The browser refused to read the frame. Keep the fixed colors from the stylesheet.
      state.ambientBroken = true;
    }
  }

  /* ---------- Docked player ---------- */

  let dockObs = null;
  let dockTarget = null;

  function setupDock() {
    if (!SETTINGS.dockOnScroll) return;
    const flexy = getFlexy();
    const placeholder = flexy && flexy.querySelector('#primary-inner > #player');
    if (!placeholder || placeholder === dockTarget) return;
    if (dockObs) dockObs.disconnect();
    dockTarget = placeholder;
    dockObs = new IntersectionObserver(
      (entries) => {
        const e = entries[entries.length - 1];
        state.playerOut = !e.isIntersecting && e.boundingClientRect.bottom < 120;
        evaluateDock();
      },
      { threshold: 0, rootMargin: '-64px 0px 0px 0px' }
    );
    dockObs.observe(placeholder);
  }

  function evaluateDock() {
    const flexy = getFlexy();
    const ok =
      SETTINGS.dockOnScroll &&
      isWatch() &&
      state.playerOut &&
      !!flexy &&
      flexy.hasAttribute('is-two-columns_') &&
      !flexy.hasAttribute('theater') &&
      !flexy.hasAttribute('fullscreen') &&
      !document.fullscreenElement;
    setDocked(ok);
  }

  function setDocked(on) {
    if (root.classList.contains('kino-docked') === on) return;
    root.classList.toggle('kino-docked', on);
    // Lets YouTube's player measure its new box.
    requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
  }

  function ensureUndock() {
    if ($('#kino-undock')) return;
    document.body.append(el('button', { id: 'kino-undock', type: 'button', text: 'Back to the video', onclick: () => window.scrollTo({ top: 0, behavior: 'smooth' }) }));
  }

  /* ---------- End screen ---------- */

  function ensureEnd() {
    const player = getPlayerNode();
    if (!player || player.querySelector('#kino-end')) return;
    player.append(
      el(
        'div',
        { id: 'kino-end' },
        el('p', { class: 'kino-end-kicker', text: 'The end' }),
        el('p', { class: 'kino-end-title', text: 'That was the whole video.' }),
        SETTINGS.autoplayOff ? el('p', { class: 'kino-end-sub', text: 'Nothing plays until you pick something.' }) : null,
        el(
          'div',
          { class: 'kino-end-actions' },
          el('button', {
            type: 'button',
            class: 'kino-btn',
            text: 'Watch again',
            onclick: (e) => {
              e.stopPropagation();
              player.removeAttribute('data-kino-stopped');
              seek(0);
              play();
            },
          }),
          el('button', {
            type: 'button',
            class: 'kino-btn kino-btn-solid',
            text: 'Stop here',
            onclick: (e) => {
              e.stopPropagation();
              player.setAttribute('data-kino-stopped', '');
            },
          })
        )
      )
    );
  }

  function hookVideo() {
    const v = getVideo();
    if (!v || hookedVideos.has(v)) return;
    hookedVideos.add(v);
    v.addEventListener('timeupdate', updateTime);
    v.addEventListener('seeked', updateTime);
    v.addEventListener('play', () => {
      const p = getPlayerNode();
      if (p) p.removeAttribute('data-kino-stopped');
    });
    v.addEventListener('loadedmetadata', () => {
      if (state.duration || adShowing() || !isFinite(v.duration) || !v.duration) return;
      state.duration = v.duration;
      if (!state.chapters.length) {
        state.chapters = makeScenes(state.duration, SETTINGS.scenesWithoutChapters);
        state.isScenes = true;
      }
      renderAll();
    });
  }

  /* ---------- Putting it together ---------- */

  function renderAll() {
    renderTimeline();
    renderChapters();
  }

  function applyData(data, pr) {
    const details = pr && pr.videoDetails;
    const v = getVideo();
    const live = !!(details && details.isLive);
    const length = details ? Number(details.lengthSeconds) || 0 : 0;
    state.duration = live ? 0 : length || (v && !adShowing() && isFinite(v.duration) ? v.duration : 0);
    const spec = pr && pr.storyboards && pr.storyboards.playerStoryboardSpecRenderer && pr.storyboards.playerStoryboardSpecRenderer.spec;
    state.sb = parseStoryboard(spec);
    let chapters = extractChapters(data);
    state.isScenes = false;
    if (!chapters.length && state.duration) {
      chapters = makeScenes(state.duration, SETTINGS.scenesWithoutChapters);
      state.isScenes = true;
    }
    state.chapters = chapters;
    state.heat = extractHeat(data);
    renderAll();
    if (details) renderDetails(details.shortDescription || '');
  }

  async function refresh() {
    const my = ++state.token;
    root.classList.add('kino-js');
    if (!isWatch()) {
      root.classList.remove('kino-watch');
      state.playerOut = false;
      setDocked(false);
      return;
    }
    root.classList.add('kino-watch');
    const vid = currentVideoId();

    const flexy = await waitFor(() => {
      const f = getFlexy();
      return f && f.querySelector('#secondary-inner') && f.querySelector('#below') ? f : null;
    }, 15000);
    if (!flexy || my !== state.token) return;

    ensureAmbient();
    ensureUndock();

    const panel = $('#kino-panel') || buildPanel();
    const secInner = flexy.querySelector('#secondary-inner');
    if (panel.parentElement !== secInner) secInner.append(panel);
    setTab(state.tab);
    setByMoment(state.byMoment, true);
    setOnlyT(state.onlyT, true);
    watchComments();
    observeFlexy(flexy);
    placeNodes();

    const timeline = $('#kino-timeline') || buildTimeline();
    const playerSlot = flexy.querySelector('#primary-inner > #player');
    if (playerSlot && timeline.previousElementSibling !== playerSlot) playerSlot.after(timeline);

    if (!(await waitFor(() => getPlayerNode(), 10000)) || my !== state.token) return;
    ensureEnd();
    hookVideo();
    setupDock();

    if (state.videoId !== vid) {
      state.videoId = vid;
      state.duration = 0;
      state.chapters = [];
      state.heat = [];
      state.sb = null;
      state.segs = [];
      timeline.hidden = true;
      renderChapters();
    }

    for (let i = 0; i < 14 && my === state.token; i++) {
      const pr = getPlayerResponse(vid);
      const data = getWatchData(vid);
      if (pr || data) applyData(data, pr);
      if (pr && data) break;
      await sleep(i < 4 ? 400 : 900);
    }
    if (my !== state.token) return;

    if (!state.chapters.length || state.isScenes) {
      const fromDom = chaptersFromDom();
      if (fromDom.length) {
        state.chapters = fromDom;
        state.isScenes = false;
        renderAll();
      }
    }

    if (SETTINGS.autoplayOff && !state.autoplayDone && (await waitFor(() => autoplayToggle(), 8000))) {
      setAutoplay(false);
      state.autoplayDone = true;
    }
    syncAutoplaySwitch();
  }

  let refreshTimer = 0;
  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(refresh, 120);
  }

  document.addEventListener('yt-navigate-finish', (e) => {
    const ev = unwrap(e);
    state.lastNav = ev && ev.detail;
    scheduleRefresh();
  });
  document.addEventListener('yt-page-data-updated', scheduleRefresh);
  document.addEventListener('fullscreenchange', evaluateDock);
  scheduleRefresh();
})();

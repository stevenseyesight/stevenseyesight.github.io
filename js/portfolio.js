(function () {
  'use strict';

  var HIDE = window.PORTFOLIO_HIDE || [];
  function nameOf(d) { return d.t.split('/').pop().replace(/\.jpg$/i, ''); }
  var DATA = (window.PORTFOLIO || []).filter(function (d) { return HIDE.indexOf(nameOf(d)) === -1; });
  var BATCH = 48;
  var LABELS = { wedding: 'Сватба', engagement: 'Годеж', prom: 'Бал', photoshoot: 'Фотосесия', events: 'Събитие', daily: 'Момент от ежедневието' };

  var grid = document.getElementById('grid');
  var moreBtn = document.getElementById('load-more');
  var filters = document.querySelectorAll('.filter');
  var lb = document.getElementById('lightbox');
  var lbImg = lb.querySelector('.lb-img');
  var overlay = document.getElementById('end-overlay');
  var sentinel = document.getElementById('end-sentinel');

  var cat = 'all', view = [], shown = 0, cols = [], colH = [];

  var ORDER = ['wedding', 'engagement', 'prom', 'photoshoot', 'events', 'daily'];
  function buildView(c) {
    if (c !== 'all') return DATA.filter(function (d) { return d.c === c; });
    var out = [];
    ORDER.forEach(function (k) { out = out.concat(DATA.filter(function (d) { return d.c === k; })); });
    return out;
  }

  function colCount() { return window.matchMedia('(max-width: 820px)').matches ? 2 : 3; }

  function buildCols() {
    grid.innerHTML = '';
    cols = []; colH = [];
    for (var i = 0; i < colCount(); i++) {
      var col = document.createElement('div');
      col.className = 'm-col';
      grid.appendChild(col);
      cols.push(col); colH.push(0);
    }
  }

  function addItems(from, to) {
    for (var i = from; i < to; i++) {
      var it = view[i];
      var k = colH.indexOf(Math.min.apply(null, colH));
      var btn = document.createElement('button');
      btn.className = 'm-item';
      btn.type = 'button';
      btn.dataset.i = i;
      btn.setAttribute('aria-label', 'Отвори снимка: ' + (LABELS[it.c] || ''));
      var img = new Image();
      img.src = it.t;
      img.alt = (LABELS[it.c] || 'Снимка') + ', снимка ' + (i + 1);
      img.width = it.w; img.height = it.h;
      img.loading = 'lazy';
      img.decoding = 'async';
      img.onerror = (function (b) { return function () { b.remove(); }; })(btn);
      btn.appendChild(img);
      cols[k].appendChild(btn);
      colH[k] += it.h / it.w;
    }
  }

  function updateMore() {
    var left = view.length - shown;
    moreBtn.hidden = left <= 0;
    if (left > 0) moreBtn.textContent = 'Зареди още (' + left + ')';
    updateOverlay();
  }

  function loadMore() {
    var next = Math.min(shown + BATCH, view.length);
    addItems(shown, next);
    shown = next;
    updateMore();
  }

  function render() {
    view = buildView(cat);
    shown = 0;
    buildCols();
    loadMore();
  }

  moreBtn.addEventListener('click', loadMore);

  var lastCols = colCount();
  window.addEventListener('resize', function () {
    if (colCount() === lastCols) return;
    lastCols = colCount();
    var keep = shown;
    buildCols();
    addItems(0, keep);
  });

  function applyFilter(c) {
    cat = c;
    filters.forEach(function (f) { f.classList.toggle('is-active', f.dataset.filter === c); });
    try { history.replaceState(null, '', c === 'all' ? location.pathname : '?cat=' + c); } catch (e) {}
    render();
  }
  filters.forEach(function (f) { f.addEventListener('click', function () { applyFilter(f.dataset.filter); }); });

  var q = new URLSearchParams(location.search).get('cat');
  if (q && document.querySelector('.filter[data-filter="' + q + '"]')) applyFilter(q); else render();

  var idx = 0, opener = null;
  function show(i) {
    if (!view.length) return;
    idx = (i + view.length) % view.length;
    lbImg.src = view[idx].f;
    lbImg.alt = LABELS[view[idx].c] || '';
    var pre = new Image(); pre.src = view[(idx + 1) % view.length].f;
  }
  function open(el) {
    opener = el;
    lb.hidden = false;
    document.body.style.overflow = 'hidden';
    show(parseInt(el.dataset.i, 10));
    lb.querySelector('.lb-close').focus();
    updateOverlay();
  }
  function close() {
    lb.hidden = true;
    document.body.style.overflow = '';
    lbImg.removeAttribute('src');
    if (opener && document.body.contains(opener)) opener.focus();
    updateOverlay();
  }
  grid.addEventListener('click', function (e) {
    var el = e.target.closest('.m-item');
    if (el) open(el);
  });
  lb.querySelector('.lb-close').addEventListener('click', close);
  lb.querySelector('.lb-prev').addEventListener('click', function () { show(idx - 1); });
  lb.querySelector('.lb-next').addEventListener('click', function () { show(idx + 1); });
  lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
  document.addEventListener('keydown', function (e) {
    if (lb.hidden) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') show(idx - 1);
    else if (e.key === 'ArrowRight') show(idx + 1);
  });
  var tx = null;
  lb.addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; }, { passive: true });
  lb.addEventListener('touchend', function (e) {
    if (tx === null) return;
    var dx = e.changedTouches[0].clientX - tx; tx = null;
    if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
  });


  var sentinelVisible = false;
  var endBox = document.querySelector('.end-contact');
  var endBtn = endBox && endBox.querySelector('.end-btn');

  function closeEnd() {
    if (!endBox) return;
    endBox.classList.remove('open');
    endBtn.setAttribute('aria-expanded', 'false');
  }

  function updateOverlay() {
    if (!overlay) return;
    var tall = document.documentElement.scrollHeight > window.innerHeight + 200;
    var on = sentinelVisible && shown >= view.length && view.length > 0 && lb.hidden && tall;
    overlay.classList.toggle('show', on);
    if (!on) closeEnd();
  }

  if ('IntersectionObserver' in window && sentinel) {
    new IntersectionObserver(function (entries) {
      sentinelVisible = entries[0].isIntersecting;
      updateOverlay();
    }, { threshold: 0 }).observe(sentinel);
  }
  window.addEventListener('resize', updateOverlay);

  if (endBtn) {
    endBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = !endBox.classList.contains('open');
      endBox.classList.toggle('open', open);
      endBtn.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', function (e) { if (!endBox.contains(e.target)) closeEnd(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeEnd(); });
  }
})();

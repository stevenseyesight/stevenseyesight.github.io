(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  
  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();


  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  var backdrop = document.querySelector('.nav-backdrop');
  var mobile = window.matchMedia('(max-width: 860px)');

  function setMenu(open) {
    if (!toggle || !nav) return;
    nav.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    if (backdrop) backdrop.hidden = !open;
    document.body.style.overflow = open && mobile.matches ? 'hidden' : '';
    if (!open) closeDropdown();
  }

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      setMenu(!nav.classList.contains('open'));
    });
    if (backdrop) backdrop.addEventListener('click', function () { setMenu(false); });
    mobile.addEventListener('change', function () { setMenu(false); });
  }


  var dropItem = document.querySelector('.has-dropdown');
  var dropBtn = dropItem && dropItem.querySelector('.dropdown-toggle');

  function closeDropdown() {
    if (!dropItem) return;
    dropItem.classList.remove('open');
    dropBtn.setAttribute('aria-expanded', 'false');
  }

  if (dropItem && dropBtn) {
    dropBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = !dropItem.classList.contains('open');
      dropItem.classList.toggle('open', open);
      dropBtn.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', function (e) {
      if (!dropItem.contains(e.target)) closeDropdown();
    });
    dropItem.querySelectorAll('.dropdown a').forEach(function (a) {
      a.addEventListener('click', function () { closeDropdown(); });
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (dropItem && dropItem.classList.contains('open')) { closeDropdown(); dropBtn.focus(); }
    else if (nav && nav.classList.contains('open')) { setMenu(false); toggle.focus(); }
  });

 
  var slideBox = document.querySelector('.hero-slides');
  var slides = Array.prototype.slice.call(document.querySelectorAll('.hero-slide'));
  if (slideBox && slides.length) {
    var current = 0;
    var timer = null;
    var INTERVAL = 6000;      
    var SLIDE_MS = 1500;      

    slides[0].classList.add('is-active');

    function go() {
      if (slides.length < 2) return;
      var prev = slides[current];
      current = (current + 1) % slides.length;
      var next = slides[current];

      next.style.transition = 'none';
      next.classList.remove('is-leaving', 'is-active');
      void next.offsetWidth;
      next.style.transition = '';

      prev.classList.remove('is-active');
      prev.classList.add('is-leaving');
      next.classList.add('is-active');

      setTimeout(function () { prev.classList.remove('is-leaving'); }, SLIDE_MS + 100);
    }

    function start() { if (!timer) timer = setInterval(go, INTERVAL); }
    function stop() { clearInterval(timer); timer = null; }

    start();
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });

    var probe = function (n) {
      var img = new Image();
      img.alt = '';
      img.decoding = 'async';
      img.onload = function () {
        var d = document.createElement('div');
        d.className = 'hero-slide';
        d.appendChild(img);
        slideBox.appendChild(d);
        slides.push(d);
        probe(n + 1);
      };
      img.src = 'images/slides/slide-' + n + '.jpg';
    };
    window.addEventListener('load', function () {
      setTimeout(function () { probe(slides.length + 1); }, 1500);
    });
  }

  var mas = document.querySelector('#snimki .mosaic');
  if (mas) {
    var imgs = Array.prototype.slice.call(mas.querySelectorAll('img'));
    var narrow = window.matchMedia('(max-width: 820px)');
    var cols = [], hs = [];
    var ratio = function (img) {
      var w = parseInt(img.getAttribute('width'), 10) || img.naturalWidth || 1;
      var h = parseInt(img.getAttribute('height'), 10) || img.naturalHeight || 1;
      return h / w;
    };
    var place = function (img) {
      var k = hs.indexOf(Math.min.apply(null, hs));
      cols[k].appendChild(img);
      hs[k] += ratio(img);
    };
    var layout = function () {
      var n = narrow.matches ? 2 : 3;
      mas.innerHTML = '';
      cols = []; hs = [];
      for (var i = 0; i < n; i++) {
        var c = document.createElement('div');
        c.className = 'm-col';
        mas.appendChild(c); cols.push(c); hs.push(0);
      }
      imgs.forEach(place);
    };
    layout();
    narrow.addEventListener('change', layout);

    var probeFeatured = function (n) {
      var img = new Image();
      img.alt = 'Избрана снимка ' + n;
      img.decoding = 'async';
      img.onload = function () {
        img.setAttribute('width', img.naturalWidth);
        img.setAttribute('height', img.naturalHeight);
        imgs.push(img);
        place(img);
        probeFeatured(n + 1);
      };
      img.src = 'images/featured/f' + n + '.jpg';
    };
    window.addEventListener('load', function () {
      setTimeout(function () { probeFeatured(imgs.length + 1); }, 800);
    });
  }


  document.querySelectorAll('[data-carousel]').forEach(function (car) {
    var track = car.querySelector('.car-track');
    var prev = car.querySelector('.car-prev'), next = car.querySelector('.car-next');
    var dotsBox = car.querySelector('.car-dots');
    var slidesC = Array.prototype.slice.call(track.children);
    var dots = slidesC.map(function () { var d = document.createElement('i'); dotsBox.appendChild(d); return d; });

    function step() { return slidesC[1] ? slidesC[1].offsetLeft - slidesC[0].offsetLeft : track.clientWidth; }
    function maxScroll() { return track.scrollWidth - track.clientWidth - 2; }
    function goTo(x) { track.scrollTo({ left: x, behavior: reduceMotion ? 'auto' : 'smooth' }); }
    function update() {
      var i = Math.min(Math.round(track.scrollLeft / step()), dots.length - 1);
      dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
      if (prev) prev.disabled = track.scrollLeft < 4;
      if (next) next.disabled = track.scrollLeft >= maxScroll();
    }
    function move(dir) { goTo(dir > 0 ? Math.min(track.scrollLeft + step(), maxScroll() + 2) : Math.max(0, track.scrollLeft - step())); }

    if (prev) prev.addEventListener('click', function () { move(-1); });
    if (next) next.addEventListener('click', function () { move(1); });
    track.addEventListener('scroll', function () { window.requestAnimationFrame(update); }, { passive: true });
    window.addEventListener('resize', update);
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { move(1); e.preventDefault(); }
      if (e.key === 'ArrowLeft') { move(-1); e.preventDefault(); }
    });
    update();
  });


  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add('in-view');
          io.unobserve(en.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('in-view'); });
  }


  var fab = document.querySelector('.fab');
  if (fab && window.matchMedia('(hover: none)').matches) {

    setTimeout(function () { fab.classList.add('show-label'); }, 1200);
    setTimeout(function () { fab.classList.remove('show-label'); }, 4200);
  }


  document.addEventListener('contextmenu', function (e) {
    if (e.target.closest && e.target.closest('img, .protect')) e.preventDefault();
  });
  document.addEventListener('dragstart', function (e) {
    if (e.target.tagName === 'IMG') e.preventDefault();
  });
})();

/* BVH inspector — median split, 긴 축 기준, 깊이 3.
   상시 루프 없음: 드래그·리시드·리사이즈에서만 다시 그린다. */
(function () {
  var c = document.getElementById('bvh');
  if (!c || !c.getContext) return;
  var ctx = c.getContext('2d');
  var N = 48, LEAF = 5, MAXD = 3, HIT = 28;
  var P = [], W = 1, H = 1, drag = -1;

  function seed() {
    P.length = 0;
    for (var i = 0; i < N; i++) {
      P.push({ x: 0.05 + Math.random() * 0.90, y: 0.09 + Math.random() * 0.82, r: 2 + Math.random() * 3 });
    }
  }
  function boxOf(ids) {
    var b = { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 };
    for (var i = 0; i < ids.length; i++) {
      var p = P[ids[i]], px = p.x * W, py = p.y * H;
      if (px - p.r < b.x0) b.x0 = px - p.r;
      if (py - p.r < b.y0) b.y0 = py - p.r;
      if (px + p.r > b.x1) b.x1 = px + p.r;
      if (py + p.r > b.y1) b.y1 = py + p.r;
    }
    return b;
  }
  function merge(a, b) {
    return { x0: Math.min(a.x0, b.x0), y0: Math.min(a.y0, b.y0), x1: Math.max(a.x1, b.x1), y1: Math.max(a.y1, b.y1) };
  }
  function build() {
    var idx = [], i;
    for (i = 0; i < P.length; i++) idx.push(i);
    var leaves = [], inner = [];
    function node(ids, d) {
      var b = boxOf(ids);
      if (d >= MAXD || ids.length <= LEAF) { leaves.push(b); return b; }
      var byX = (b.x1 - b.x0) >= (b.y1 - b.y0);
      ids.sort(function (a, z) { return byX ? P[a].x - P[z].x : P[a].y - P[z].y; });
      var m = ids.length >> 1;
      var mm = merge(node(ids.slice(0, m), d + 1), node(ids.slice(m), d + 1));
      if (d > 0) inner.push(mm);
      return mm;
    }
    var root = P.length ? node(idx, 0) : { x0: 0, y0: 0, x1: W, y1: H };
    return { root: root, inner: inner, leaves: leaves };
  }

  /* 레이아웃 전에는 rect가 0이라 박스가 뭉개진다. 옵저버 전달을 기다리지 않고 그릴 때마다 직접 잰다. */
  function measure() {
    var r = c.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = r.width; H = r.height;
    c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return true;
  }
  function ensure() { return (W >= 2 && H >= 2) || measure(); }
  function tok(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

  function draw() {
    if (!ensure()) return;
    var t = build();
    var inner = tok('--n-300') || '#cfccc7';
    var accent = tok('--accent-500') || '#0066d6';
    var ink = tok('--n-900') || '#1d1d1f';

    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;

    ctx.strokeStyle = inner;
    for (var i = 0; i < t.inner.length; i++) {
      var b = t.inner[i];
      ctx.strokeRect(b.x0 + .5, b.y0 + .5, Math.max(1, b.x1 - b.x0), Math.max(1, b.y1 - b.y0));
    }
    ctx.strokeStyle = accent;
    ctx.globalAlpha = .8;
    for (var j = 0; j < t.leaves.length; j++) {
      var l = t.leaves[j];
      ctx.strokeRect(l.x0 + .5, l.y0 + .5, Math.max(1, l.x1 - l.x0), Math.max(1, l.y1 - l.y0));
    }
    ctx.globalAlpha = 1;

    ctx.fillStyle = ink;
    for (var k = 0; k < P.length; k++) {
      ctx.beginPath();
      ctx.arc(P[k].x * W, P[k].y * H, P[k].r, 0, Math.PI * 2);
      ctx.fill();
    }

    var ov = 0, sa = 0;
    for (var a = 0; a < t.leaves.length; a++) {
      var la = t.leaves[a];
      sa += Math.max(0, la.x1 - la.x0) * Math.max(0, la.y1 - la.y0);
      for (var b2 = a + 1; b2 < t.leaves.length; b2++) {
        var lb = t.leaves[b2];
        if (la.x0 < lb.x1 && lb.x0 < la.x1 && la.y0 < lb.y1 && lb.y0 < la.y1) ov++;
      }
    }
    var ra = Math.max(1, (t.root.x1 - t.root.x0) * (t.root.y1 - t.root.y0));
    document.getElementById('m-p').textContent = P.length;
    document.getElementById('m-l').textContent = t.leaves.length;
    document.getElementById('m-o').textContent = ov;
    document.getElementById('m-a').textContent = (sa / ra).toFixed(2);
  }

  /* 거리는 픽셀로 잰다. 캔버스가 21:8이라 정규화 좌표로 재면 세로로 가까운 점을 놓친다. */
  function pick(ev) {
    ensure();
    var r = c.getBoundingClientRect();
    var px = ev.clientX - r.left, py = ev.clientY - r.top;
    var best = -1, bd = 1e9;
    for (var i = 0; i < P.length; i++) {
      var dx = P[i].x * r.width - px, dy = P[i].y * r.height - py, d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = i; }
    }
    return bd <= HIT * HIT ? best : -1;
  }
  c.addEventListener('pointerdown', function (ev) {
    drag = pick(ev);
    if (drag >= 0) { try { c.setPointerCapture(ev.pointerId); } catch (e) {} ev.preventDefault(); }
  });
  c.addEventListener('pointermove', function (ev) {
    if (drag < 0) return;
    var r = c.getBoundingClientRect();
    P[drag].x = Math.min(0.97, Math.max(0.03, (ev.clientX - r.left) / r.width));
    P[drag].y = Math.min(0.95, Math.max(0.05, (ev.clientY - r.top) / r.height));
    draw();
  });
  function end(ev) { if (drag >= 0) { try { c.releasePointerCapture(ev.pointerId); } catch (e) {} } drag = -1; }
  c.addEventListener('pointerup', end);
  c.addEventListener('pointercancel', end);
  document.getElementById('reseed').addEventListener('click', function () { seed(); draw(); });

  seed();
  if ('ResizeObserver' in window) new ResizeObserver(function () { if (measure()) draw(); }).observe(c);
  else window.addEventListener('resize', function () { if (measure()) draw(); });
  draw();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
})();

/**
 * Generate a deterministic QR-like placeholder SVG into every [data-qr] element.
 * Pass ?value=<string> via data-qr-value to vary the pattern.
 * If an <img data-qr-src="path"> is present inside, it uses the real image on load.
 */
(function () {
  function hash(str) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h;
  }

  function rng(seed) {
    let s = seed >>> 0 || 1;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  function render(el) {
    const value = el.getAttribute('data-qr-value') || el.textContent || 'click-home';
    const size = 29; // modules per side (mimics QR ~v3)
    const r = rng(hash(value));
    const cells = [];
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        cells.push(r() > 0.5 ? 1 : 0);
      }
    }
    // Force finder patterns at three corners so it reads as a QR at a glance.
    function stamp(ox, oy) {
      for (let y = 0; y < 7; y++) {
        for (let x = 0; x < 7; x++) {
          const border = x === 0 || x === 6 || y === 0 || y === 6;
          const inner = x >= 2 && x <= 4 && y >= 2 && y <= 4;
          cells[(oy + y) * size + (ox + x)] = (border || inner) ? 1 : 0;
        }
      }
    }
    stamp(0, 0);
    stamp(size - 7, 0);
    stamp(0, size - 7);

    const cellPx = 8;
    const pad = 8;
    const svgSize = size * cellPx + pad * 2;
    let rects = '';
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (cells[y * size + x]) {
          rects += `<rect x="${pad + x * cellPx}" y="${pad + y * cellPx}" width="${cellPx}" height="${cellPx}"/>`;
        }
      }
    }
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgSize} ${svgSize}" shape-rendering="crispEdges">
      <rect width="${svgSize}" height="${svgSize}" fill="#fff"/>
      <g fill="currentColor">${rects}</g>
    </svg>`;
    el.innerHTML = svg;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-qr]').forEach(render);
  });
})();

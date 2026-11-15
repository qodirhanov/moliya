// Tema sahifa chizilishidan oldin qo'yiladi (oq-qora miltillash bo'lmasligi uchun) — shu sabab <head> da
// sinxron yuklanadi. Alohida faylda: Content-Security-Policy sahifa ichidagi (inline) skriptlarni bajarmaydi
(function () {
  // Xotira yopiq bo'lsa (maxfiy rejim, bloklangan sayt ma'lumotlari) getItem xato otadi — standart mavzu ishlatiladi
  var saved = null;
  try { saved = localStorage.getItem('moliyaTheme'); } catch (e) { /* tizim mavzusi */ }
  var theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  // Rang mavzusi sahifa chizilishidan oldin qo'yiladi (ro'yxat app.js dagi PALETTES bilan bir xil).
  // Tanlanmagan bo'lsa — standart "oltin"; "moy" — klassik moy-yashil (atributsiz, style.css :root ranglari)
  // Standart mavzu "oltin" bo'lganda avvalgi tanlov bir marta unga almashtiriladi (keyin Sozlamalarda yana o'zgartirish mumkin)
  try {
    if (localStorage.getItem('moliyaPaletteVersion') !== '2') {
      localStorage.setItem('moliyaPalette', 'oltin');
      localStorage.setItem('moliyaPaletteVersion', '2');
    }
  } catch (e) { /* xotira yopiq bo'lsa standart mavzu ishlatiladi */ }
  var palette = 'oltin';
  try { palette = localStorage.getItem('moliyaPalette') || 'oltin'; } catch (e) { /* standart mavzu */ }
  if (['oltin', 'zumrad', 'firuza', 'lojuvard', 'zaytun', 'olcha'].indexOf(palette) !== -1) {
    document.documentElement.setAttribute('data-palette', palette);
  }
  // Brauzer paneli rangi (theme-color): rejimga qarab; rejim keyin almashsa ham yangilanadi (moliya-ranglar.css dagi --bg bilan bir xil)
  var meta = document.querySelector('meta[name="theme-color"]');
  function syncThemeColor() {
    if (meta) meta.setAttribute('content', document.documentElement.getAttribute('data-theme') === 'dark' ? '#000000' : '#EDEDED');
  }
  syncThemeColor();
  try { new MutationObserver(syncThemeColor).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }); } catch (e) { /* eski brauzer */ }

  // i18n.js endi defer bilan yuklanadi (sahifa chizilishini to'xtatmasin). O'zbekchadan boshqa til tanlangan bo'lsa
  // sahifa tarjima tugaguncha yashiriladi (style.css: html.i18n-pending) — aks holda o'zbekcha matn bir lahza ko'rinadi.
  // Faqat i18n.js ulangan sahifada (skript tegida data-i18n). i18n.js yuklanmay qolsa ham 3 soniyadan keyin ochiladi
  var me = document.currentScript;
  if (me && me.hasAttribute('data-i18n')) {
    var lang = 'uz';
    try { lang = localStorage.getItem('moliyaLang') || 'uz'; } catch (e) { /* o'zbekcha */ }
    if (lang !== 'uz' && ['tg', 'kk', 'ky', 'ru', 'en', 'tr'].indexOf(lang) !== -1) {
      var root = document.documentElement;
      root.classList.add('i18n-pending');
      setTimeout(function () { root.classList.remove('i18n-pending'); }, 3000);
    }
  }
})();

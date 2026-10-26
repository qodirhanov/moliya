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
})();

// INTERFEYS TILI (Sozlamalar → Til). Ilova matni o'zbekcha yozilgan; boshqa til tanlansa sahifadagi matnlar
// lug'at bo'yicha almashtiriladi. Lug'at: static/js/i18n/<til>.js — AVTOMATIK; tarjimalarni i18n/translations.js da
// o'zgartiring, keyin `python manage.py build_i18n`. {0}, {1} — o'zgaruvchan qism (ism, summa, sana).
// MutationObserver app.js chizgan yangi matnlarni ham ushlaydi, shuning uchun app.js dagi matnlarni o'zgartirish shart emas.
// defer bilan yuklanadi; boshqa tilda theme-init.js sahifani tarjima tugaguncha yashiradi (o'zbekcha matn miltillamaydi)
(function () {
  var STORAGE_KEY = 'moliyaLang';
  var LANGS = ['uz', 'tg', 'kk', 'ky', 'ru', 'en', 'tr'];
  var COLS = ['ru', 'en', 'tr', 'kk', 'ky', 'tg'];

  var lang = 'uz';
  try { lang = localStorage.getItem(STORAGE_KEY) || 'uz'; } catch (e) { /* xotira yopiq — o'zbekcha */ }
  if (LANGS.indexOf(lang) === -1) lang = 'uz';
  document.documentElement.setAttribute('lang', lang);

  // Oy nomlari: [to'liq, sanada (kelishikda), qisqa]
  var MONTHS = {
    uz: [['Yanvar','Fevral','Mart','Aprel','May','Iyun','Iyul','Avgust','Sentabr','Oktabr','Noyabr','Dekabr'],
         ['yanvar','fevral','mart','aprel','may','iyun','iyul','avgust','sentabr','oktabr','noyabr','dekabr'],
         ['yan','fev','mar','apr','may','iyn','iyl','avg','sen','okt','noy','dek']],
    ru: [['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'],
         ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'],
         ['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек']],
    en: [['January','February','March','April','May','June','July','August','September','October','November','December'],
         ['January','February','March','April','May','June','July','August','September','October','November','December'],
         ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']],
    tr: [['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'],
         ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'],
         ['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara']],
    kk: [['Қаңтар','Ақпан','Наурыз','Сәуір','Мамыр','Маусым','Шілде','Тамыз','Қыркүйек','Қазан','Қараша','Желтоқсан'],
         ['қаңтар','ақпан','наурыз','сәуір','мамыр','маусым','шілде','тамыз','қыркүйек','қазан','қараша','желтоқсан'],
         ['қаң','ақп','нау','сәу','мам','мау','шіл','там','қыр','қаз','қар','жел']],
    ky: [['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'],
         ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь'],
         ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']],
    tg: [['Январ','Феврал','Март','Апрел','Май','Июн','Июл','Август','Сентябр','Октябр','Ноябр','Декабр'],
         ['январ','феврал','март','апрел','май','июн','июл','август','сентябр','октябр','ноябр','декабр'],
         ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']]
  };

  // Lug'at alohida faylda: static/js/i18n/<til>.js (manba — i18n/translations.js, `python manage.py build_i18n`).
  // theme-init.js uni <head> da yuklashni boshlaydi; o'zbekchada lug'at yuklanmaydi

  var col = COLS.indexOf(lang);
  var exact = Object.create(null);   // o'zbekcha matn -> tarjima
  var patterns = [];                 // { re, out } — {0} li kalitlar
  var ready = false;                 // lug'at kelib, tarjima boshlandimi (o'zbekchada doim false — tarjima yo'q)

  // dict — { o'zbekcha matn: shu tildagi tarjima } (static/js/i18n/<til>.js dagi MOLIYA_I18N)
  function loadDict(dict) {
    Object.keys(dict).forEach(function (key) {
      var out = dict[key];
      if (!out) return;
      if (key.indexOf('{0}') === -1) { exact[key] = out; return; }
      var src = key.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace(/\{(\d)\}/g, '(.+?)');
      patterns.push({ re: new RegExp('^' + src + '$'), out: out, literal: key.replace(/\{\d\}/g, '').length });
    });
    // Aniqroq naqsh (o'zgarmas qismi uzunroq) birinchi tekshiriladi: "Valyuta: {0} · Yaratilgan: {1}" > "Valyuta: {0}"
    patterns.sort(function (a, b) { return b.literal - a.literal; });
  }

  function translate(text, depth) {
    var hit = exact[text];
    if (hit !== undefined) return hit;
    if (depth > 2) return text;
    for (var i = 0; i < patterns.length; i++) {
      var m = patterns[i].re.exec(text);
      if (!m) continue;
      return patterns[i].out.replace(/\{(\d)\}/g, function (_, n) {
        var part = m[Number(n) + 1];
        return part === undefined ? '' : translate(part, depth + 1);
      });
    }
    return text;
  }

  // Bo'sh joylar saqlanadi: "\n  Chiqish\n" -> "\n  Выйти\n"
  function tr(value) {
    if (!ready || !value) return value;
    var core = value.replace(/\s+/g, ' ').trim();
    if (!core || !/[A-Za-z]/.test(core)) return value;
    var out = translate(core, 0);
    if (out === core) return value;
    var lead = value.match(/^\s*/)[0], trail = value.match(/\s*$/)[0];
    return (lead ? ' ' : '') + out + (trail ? ' ' : '');
  }

  var ATTRS = ['placeholder', 'title', 'aria-label'];
  // Ichidagi matn tarjima qilinmaydigan teglar (textarea matni — foydalanuvchi yozgani; placeholder esa tarjima qilinadi)
  var SKIP_TEXT_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1 };

  function skipped(el) {
    return !el || el.tagName === 'svg' || el.isContentEditable || (el.closest && el.closest('[data-no-i18n]'));
  }

  function translateText(node) {
    var parent = node.parentElement;
    if (skipped(parent) || SKIP_TEXT_TAGS[parent.tagName]) return;
    var out = tr(node.data);
    if (out !== node.data) node.data = out;
  }

  function translateAttrs(el) {
    if (skipped(el)) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var v = el.getAttribute(ATTRS[i]);
      if (v) {
        var out = tr(v);
        if (out !== v) el.setAttribute(ATTRS[i], out);
      }
    }
  }

  function translateTree(root) {
    if (root.nodeType === 3) { translateText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9) return;
    if (root.nodeType === 1) translateAttrs(root);
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var n;
    while ((n = walker.nextNode())) {
      if (n.nodeType === 3) translateText(n); else translateAttrs(n);
    }
  }

  function start() {
    if (ready || !window.MOLIYA_I18N) return;
    loadDict(window.MOLIYA_I18N);
    ready = true;
    // Tarjimaning o'zi ham mutatsiya chiqaradi, lekin tarjima qilingan matn lug'atda yo'q — qayta o'zgarmaydi
    new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var r = records[i];
        if (r.type === 'childList') {
          for (var j = 0; j < r.addedNodes.length; j++) translateTree(r.addedNodes[j]);
        } else if (r.type === 'characterData') {
          translateText(r.target);
        } else if (r.type === 'attributes') {
          translateAttrs(r.target);
        }
      }
    }).observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
    translateTree(document.documentElement);
    // Tarjima tugadi — theme-init.js yashirgan sahifa ko'rsatiladi
    document.documentElement.classList.remove('i18n-pending');
  }

  if (col !== -1) {
    // Lug'at odatda shu fayldan oldin keladi; kechiksa — lug'at fayli o'zi __moliyaI18nReady() ni chaqiradi.
    // Kelguncha i18n.t() o'zbekcha matnni qaytaradi; DOM dagisi lug'at kelganda baribir tarjima qilinadi
    window.__moliyaI18nReady = start;
    start();
  } else {
    document.documentElement.classList.remove('i18n-pending');
  }

  // Sana: uz "20-oktabr, 2026", ru "20 октября 2026", en "October 20, 2026"
  function formatDate(day, month, opts) {
    opts = opts || {};
    var m = MONTHS[lang];
    var name = opts.short ? m[2][month] : m[1][month];
    var s;
    if (lang === 'uz' || lang === 'ky') s = day + '-' + name;
    else if (lang === 'en') s = name + ' ' + day;
    else s = day + ' ' + name;
    if (opts.year) s += (lang === 'uz' || lang === 'ky' || lang === 'en' ? ', ' : ' ') + opts.year;
    return s;
  }

  function setLang(value) {
    if (LANGS.indexOf(value) === -1 || value === lang) return;
    try { localStorage.setItem(STORAGE_KEY, value); } catch (e) { /* faqat shu safarga */ }
    // app.js chizgan matnlar (sanalar, ro'yxatlar) yangi tilda qayta chizilishi uchun sahifa qayta yuklanadi
    location.reload();
  }

  window.i18n = {
    lang: lang,
    langs: LANGS,
    t: function (text) { return tr(text); },
    months: MONTHS[lang][0],
    formatDate: formatDate,
    setLang: setLang
  };
})();

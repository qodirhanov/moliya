// Admin panel → Yordam → suhbat: foydalanuvchining yangi xabarlarini har necha soniyada so'rab, ro'yxatga qo'shadi.
// Javob oddiy forma bilan yuboriladi (sahifa qayta ochiladi), shuning uchun bu yerda faqat o'qish
(function () {
  var log = document.getElementById('supportLog');
  if (!log) return;
  var POLL_MS = 5000;
  var MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];
  var lastId = Number(log.dataset.lastId) || 0;

  function scrollToEnd() { log.scrollTop = log.scrollHeight; }

  // panel_tags.uz_date bilan bir xil: "23-oktabr, 2026, 14:05"
  function uzDate(iso) {
    var d = new Date(iso);
    var pad = function (n) { return String(n).padStart(2, '0'); };
    return d.getDate() + '-' + MONTHS[d.getMonth()] + ', ' + d.getFullYear() + ', ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function append(m) {
    var empty = document.getElementById('supportEmpty');
    if (empty) empty.remove();
    var row = document.createElement('div');
    row.className = 'chat-msg ' + (m.from_admin ? 'is-mine' : 'is-theirs');
    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = m.text; // textContent — foydalanuvchi matni HTML sifatida ishlamaydi (CSS: white-space: pre-wrap)
    var time = document.createElement('div');
    time.className = 'chat-time';
    time.textContent = uzDate(m.created_at);
    row.appendChild(bubble);
    row.appendChild(time);
    log.appendChild(row);
  }

  function poll() {
    if (document.hidden) return;
    fetch(log.dataset.pollUrl + '?after=' + lastId, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.messages.length) return;
        var atEnd = log.scrollHeight - log.scrollTop - log.clientHeight < 60;
        data.messages.forEach(function (m) { if (m.id > lastId) { append(m); lastId = m.id; } });
        if (atEnd) scrollToEnd();
      })
      .catch(function () { /* tarmoq uzilgan — keyingi urinishda */ });
  }

  scrollToEnd();
  setInterval(poll, POLL_MS);

  var form = document.getElementById('supportReplyForm');
  var textarea = form && form.querySelector('textarea');
  if (textarea) {
    textarea.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); form.requestSubmit(); }
    });
    // Ikki marta bosilsa javob ikki marta yozilmasin
    form.addEventListener('submit', function () { form.querySelector('button[type="submit"]').disabled = true; });
  }
})();

// Admin panel → Xabar yuborish: "Bitta foydalanuvchiga" tanlanganda login maydoni ochiladi,
// hammaga yuborish va o'chirishdan oldin tasdiq so'raladi (sahifada inline skript yo'q — CSP)
(function () {
  var form = document.getElementById('noticeForm');
  if (form) {
    var group = document.getElementById('noticeToGroup');
    var to = document.getElementById('noticeTo');
    var sync = function () {
      var single = form.elements.target.value === 'user';
      group.hidden = !single;
      to.required = single;
      if (single && !to.value) to.focus();
    };
    Array.prototype.forEach.call(form.elements.target, function (r) { r.addEventListener('change', sync); });
    sync();
    form.addEventListener('submit', function (e) {
      if (form.elements.target.value !== 'all') return;
      if (!window.confirm('Xabar barcha foydalanuvchilarga (' + form.dataset.activeUsers + ' ta faol) yuborilsinmi?')) e.preventDefault();
    });
  }
  document.querySelectorAll('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (!window.confirm(f.dataset.confirm)) e.preventDefault();
    });
  });
})();

/* QuickFood — cloche de notifications en temps réel (Socket.IO) */
(function () {
  const script = document.currentScript;
  const userId = script && script.dataset.userId;
  const bellBtn = document.getElementById('qf-bell-btn');
  const bellDot = document.getElementById('qf-bell-dot');
  const panel = document.getElementById('qf-notif-panel');
  if (!bellBtn || !panel) return;

  function renderList(items) {
    if (!items || !items.length) {
      panel.innerHTML = '<div class="qf-notif-item text-center text-muted">Aucune notification</div>';
      return;
    }
    panel.innerHTML = items.map(function (n) {
      return '<a href="' + (n.link || '#') + '" class="qf-notif-item ' + (n.is_read ? '' : 'unread') +
        '" data-id="' + n.id + '">' +
        '<div class="qf-notif-title">' + n.title + '</div>' +
        '<div>' + (n.message || '') + '</div>' +
        '<div class="qf-notif-time">' + (n.created_at || '') + '</div></a>';
    }).join('');
  }

  function updateDot(count) {
    if (count > 0) {
      bellDot.style.display = 'flex';
      bellDot.textContent = count > 9 ? '9+' : count;
    } else {
      bellDot.style.display = 'none';
    }
  }

  function fetchNotifications() {
    fetch('/notifications/').then(function (r) { return r.json(); }).then(function (data) {
      updateDot(data.unread_count || 0);
      renderList(data.items || []);
    }).catch(function () {});
  }

  bellBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) {
      fetchNotifications();
      setTimeout(function () {
        fetch('/notifications/read-all', { method: 'POST' }).then(function () { updateDot(0); });
      }, 1500);
    }
  });
  document.addEventListener('click', function () { panel.classList.remove('open'); });

  fetchNotifications();

  if (window.io && userId) {
    const socket = io();
    socket.on('connect', function () { socket.emit('join_user_room', { user_id: userId }); });
    socket.on('new_notification', function () { fetchNotifications(); });
  }
})();

/* Smart Home style theme: dark/light mode + sidebar collapse/mobile toggle.
   Purely presentational — does not touch any hospital business logic. */
(function () {
    var root = document.documentElement;
    var THEME_KEY = 'hamro-theme';
    var SIDEBAR_KEY = 'hamro-sidebar-collapsed';

    function applyTheme(theme) {
        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
            root.setAttribute('data-bs-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
            root.setAttribute('data-bs-theme', 'light');
        }
        document.querySelectorAll('.theme-toggle-btn i').forEach(function (icon) {
            icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
        });
    }

    var savedTheme = localStorage.getItem(THEME_KEY) ||
        (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(savedTheme);

    document.addEventListener('DOMContentLoaded', function () {
        // Theme toggle
        document.querySelectorAll('.theme-toggle-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var current = (root.getAttribute('data-bs-theme') === 'dark' || root.getAttribute('data-theme') === 'dark') ? 'dark' : 'light';
                var next = current === 'dark' ? 'light' : 'dark';
                localStorage.setItem(THEME_KEY, next);
                applyTheme(next);
            });
        });

        // Sidebar collapse (desktop)
        var sidebar = document.querySelector('.app-sidebar');
        var collapseBtn = document.querySelector('.app-sidebar-toggle');
        if (sidebar && collapseBtn) {
            if (localStorage.getItem(SIDEBAR_KEY) === '1') {
                sidebar.classList.add('collapsed');
            }
            collapseBtn.addEventListener('click', function () {
                sidebar.classList.toggle('collapsed');
                localStorage.setItem(SIDEBAR_KEY, sidebar.classList.contains('collapsed') ? '1' : '0');
            });
        }

        // Sidebar mobile toggle
        var mobileToggle = document.querySelector('.app-mobile-toggle');
        var overlay = document.querySelector('.app-sidebar-overlay');
        function closeMobileSidebar() {
            if (sidebar) sidebar.classList.remove('mobile-open');
            document.body.classList.remove('sidebar-mobile-open');
        }
        if (mobileToggle && sidebar) {
            mobileToggle.addEventListener('click', function () {
                sidebar.classList.toggle('mobile-open');
                document.body.classList.toggle('sidebar-mobile-open');
            });
        }
        if (overlay) {
            overlay.addEventListener('click', closeMobileSidebar);
        }

        // Enable Bootstrap tooltips anywhere in the app
        if (window.bootstrap && window.bootstrap.Tooltip) {
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
                new bootstrap.Tooltip(el);
            });
        }
    });
})();

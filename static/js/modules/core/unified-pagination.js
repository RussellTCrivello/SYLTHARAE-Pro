/**
 * Jump-to-page + Show More for server-rendered (template) pagination.
 *
 * Wires every ``.unified-pagination-jump-btn`` and
 * ``.unified-pagination-show-more-btn`` inside a root. Safe to run more than
 * once (each control is tagged after wiring). Soft navigation swaps
 * ``#mainContent`` without re-executing this file, so we also re-wire on
 * ``syltharae:soft-nav`` — otherwise Show More looks present but does nothing.
 *
 * Moved out of an inline <script> so the Content-Security-Policy can forbid
 * inline script (RES-CSP-01).
 */
(function (window, document) {
    'use strict';

    function wireJumpButtons(root) {
        root.querySelectorAll('.unified-pagination-jump-btn[data-endpoint]').forEach(function (jumpBtn) {
            if (jumpBtn.hasAttribute('data-jump-wired')) return;
            var jumpInput = document.getElementById(
                'jumpToPageInput-' + jumpBtn.getAttribute('data-endpoint'));
            if (!jumpInput) return;
            jumpBtn.setAttribute('data-jump-wired', '');

            var handleJump = function () {
                var targetPage = parseInt(jumpInput.value, 10);
                var totalPages = parseInt(jumpInput.getAttribute('data-total-pages'), 10) || 1;

                if (isNaN(targetPage) || targetPage < 1) {
                    targetPage = 1;
                } else if (targetPage > totalPages) {
                    targetPage = totalPages;
                }

                var url = new URL(window.location.href);
                url.searchParams.set('page', targetPage);
                if (window.swapNavigate) { window.swapNavigate(url.toString()); }
                else { window.location.href = url.toString(); }
            };

            jumpBtn.addEventListener('click', handleJump);
            jumpInput.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    handleJump();
                }
            });
        });
    }

    function wireShowMoreButtons(root) {
        root.querySelectorAll('.unified-pagination-show-more-btn').forEach(function (showMoreBtn) {
            if (showMoreBtn.hasAttribute('data-show-more-wired')) return;
            showMoreBtn.setAttribute('data-show-more-wired', '');

            showMoreBtn.addEventListener('click', function () {
                // Prefer the unified-table Load More control when it is present
                // and actually shown — one append path, not two competing ones.
                var utBlock = document.querySelector('[data-ut-load-more]');
                var utVisible = utBlock && !utBlock.hidden
                    && utBlock.offsetParent !== null
                    && window.getComputedStyle(utBlock).display !== 'none';
                var utLoadMoreBtn = utVisible ? utBlock.querySelector('button') : null;
                if (utLoadMoreBtn) {
                    utLoadMoreBtn.click();
                    return;
                }

                var targetPage = parseInt(showMoreBtn.getAttribute('data-next-page'), 10) || 2;
                var totalPages = parseInt(showMoreBtn.getAttribute('data-total-pages'), 10) || 1;
                var url = new URL(window.location.href);
                url.searchParams.set('page', targetPage);
                showMoreBtn.disabled = true;
                var icon = showMoreBtn.querySelector('i');
                if (icon) icon.className = 'spinner-border spinner-border-sm me-1';

                fetch(url.toString(), {
                    headers: { 'X-Requested-With': 'fetch' },
                    credentials: 'same-origin',
                })
                    .then(function (res) {
                        if (!res.ok) throw new Error('HTTP ' + res.status);
                        return res.text();
                    })
                    .then(function (html) {
                        var doc = new DOMParser().parseFromString(html, 'text/html');
                        var incomingRows = doc.querySelectorAll(
                            '#emailTableBody tr, .unified-table tbody tr, table.table tbody tr, table tbody tr');
                        var targetBody = document.getElementById('emailTableBody')
                            || document.querySelector(
                                '#mainContent .unified-table tbody, #mainContent table.table tbody, #mainContent table tbody')
                            || document.querySelector(
                                '.unified-table tbody, table.table tbody, table tbody');
                        if (targetBody && incomingRows.length) {
                            // Prefer rows from the same table body id when present.
                            var preferred = doc.querySelectorAll('#emailTableBody tr');
                            var rows = preferred.length ? preferred : incomingRows;
                            // If still the broad selector, take only the first matching tbody's rows.
                            if (!preferred.length && rows.length) {
                                var firstBody = rows[0].parentElement;
                                rows = firstBody ? firstBody.querySelectorAll('tr') : rows;
                            }
                            rows.forEach(function (row) {
                                targetBody.appendChild(document.importNode(row, true));
                            });
                            var shownEl = document.getElementById('showingCount');
                            if (shownEl) {
                                shownEl.textContent = String(targetBody.querySelectorAll('tr').length);
                            }
                            // Keep selection toolbars in step after newly appended rows.
                            if (typeof window.updateBulkButtons === 'function') {
                                window.updateBulkButtons();
                            }
                        }
                        var newNextPage = targetPage + 1;
                        showMoreBtn.setAttribute('data-next-page', String(newNextPage));
                        showMoreBtn.setAttribute('data-current-page', String(targetPage));
                        if (newNextPage > totalPages) {
                            var wrap = showMoreBtn.closest('.unified-pagination-show-more');
                            if (wrap) wrap.style.display = 'none';
                        }
                        var container = showMoreBtn.closest('.unified-pagination-container');
                        if (container) {
                            container.setAttribute('data-current-page', String(targetPage));
                        }
                    })
                    .catch(function (err) {
                        console.error('Show More failed:', err);
                    })
                    .finally(function () {
                        showMoreBtn.disabled = false;
                        if (icon) icon.className = 'bi bi-arrow-down-circle me-1';
                    });
            });
        });
    }

    function wireUtLoadMoreSync() {
        if (window.__utLoadMoreSyncWired) return;
        window.__utLoadMoreSyncWired = true;
        document.addEventListener('ut:loadmore', function (e) {
            var detail = e.detail || {};
            var total = detail.total || 0;
            var shown = detail.shown || 0;
            if (shown >= total) {
                document.querySelectorAll('.unified-pagination-show-more-btn').forEach(function (btn) {
                    var wrap = btn.closest('.unified-pagination-show-more');
                    if (wrap) wrap.style.display = 'none';
                });
            }
        });
    }

    /**
     * Wire jump + Show More controls under ``root`` (defaults to document).
     * Idempotent: already-wired controls are skipped.
     */
    function initUnifiedPaginationControls(root) {
        var scope = root && root.querySelectorAll ? root : document;
        wireJumpButtons(scope);
        wireShowMoreButtons(scope);
        wireUtLoadMoreSync();
    }

    window.initUnifiedPaginationControls = initUnifiedPaginationControls;

    initUnifiedPaginationControls(document);

    document.addEventListener('syltharae:soft-nav', function () {
        initUnifiedPaginationControls(document.getElementById('mainContent') || document);
    });
}(window, document));

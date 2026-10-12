/**
 * Shared shell preparation on every route (full load or soft-nav).
 * Ensures declarative handlers and FMAS/file globals exist before page init.
 */

import { attachWindowGlobals } from '../../managers/function-manager.js';
import { initDocumentActions } from '../documents/document-actions.js';

/**
 * @param {string} pageType - from universal-initializer detectPageType()
 */
export async function preparePageShell(pageType) {
    attachWindowGlobals();
    initDocumentActions();

    const needsFileModal =
        pageType === 'archives'
        || pageType === 'files-list'
        || pageType === 'file-detail'
        || pageType === 'search-advanced'
        || pageType === 'search-enhanced'
        || pageType === 'search';

    if (needsFileModal && typeof window.showFileDetails !== 'function') {
        const bust = window.__swapReinit ? '?swap=' + window.__swapReinit : '';
        try {
            await import('../../file-management-system.js' + bust);
        } catch (error) {
            console.warn('Shell bridge: file-management-system unavailable', error);
        }
        attachWindowGlobals();
    }

    if (pageType === 'files-list') {
        try {
            const mod = await import('../file-operations/file-management.js');
            const FileManagement = mod.default || mod;
            if (FileManagement && typeof FileManagement.applyFilters === 'function') {
                const bound = FileManagement.applyFilters.bind(FileManagement);
                window.applyFileFilters = bound;
                if (document.getElementById('filesTable')) {
                    window.applyFilters = bound;
                }
            }
        } catch (_error) { /* files-list module wires its own exports */ }
    } else if (pageType === 'archives') {
        if (window.fms?.ui?.filters?.applyFilters) {
            window.applyFilters = window.fms.ui.filters.applyFilters;
        }
    }
}

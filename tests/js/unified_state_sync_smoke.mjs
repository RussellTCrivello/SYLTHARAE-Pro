/**
 * One state, every control: Show More, the registration range, the numbered
 * pager, Prev/Next/First/Last and the jump input all follow one state record.
 *
 * The view starts on page 2 of 5 (5 rows a page, 23 rows in all): rows 6-10.
 * Show More walks it to the end, one batch a page, and every control must
 * agree after each batch. A batch that brings nothing must not move the page.
 *
 *   node tests/js/unified_state_sync_smoke.mjs
 */
import { installDom, treeFromHtml } from './_dom_stub.mjs';

const checks = [];
function check(name, ok, detail) {
    checks.push([name, ok === true]);
    console.log(`${ok === true ? 'ok  ' : 'FAIL'} ${name}`);
    if (ok !== true) console.log(`     detail: ${detail ?? ''}`);
}
const wait = () => new Promise((resolve) => setTimeout(resolve, 20));

const { documentRoot, globalThisRef } = installDom();
globalThisRef.location = new URL('http://localhost/keywords?page=2&per_page=5&sort=name&order=asc');
globalThisRef.URL = URL;
globalThisRef.DOMParser = class { parseFromString(html) { return treeFromHtml(html); } };

// Each batch the server would render: 5 rows for pages 3 and 4, 3 for page 5.
// `nextBatch` lets a test answer with an empty batch instead.
const served = [];
let nextBatch = null;
function batchHtml(count, start) {
    let rows = '';
    for (let i = 0; i < count; i += 1) rows += `<tr><td>r${start + i}</td></tr>`;
    return `<div data-unified-table='{"mode":"server"}'><table id="keywordsTable"><tbody>${rows}</tbody></table></div>`;
}
globalThisRef.fetch = (url) => {
    served.push(String(url));
    const page = Number(new URL(String(url)).searchParams.get('page'));
    const override = nextBatch;
    nextBatch = null;
    const body = override ?? (page === 3 ? batchHtml(5, 11) : page === 4 ? batchHtml(5, 16) : batchHtml(3, 21));
    return Promise.resolve({ ok: true, status: 200, text: async () => body });
};

// The server's markup: nav links with hooks, numbered items marked as
// numbered, and the hidden prototypes the engine clones.
function navItem(hook, href, text) {
    return `<li class="unified-pagination-item"><a class="unified-pagination-link" data-ut-nav="${hook}" href="${href}">${text}</a></li>`;
}
function numberedItem(n, href) {
    return `<li data-ut-numbered class="unified-pagination-item"><a class="unified-pagination-link" href="${href}">${n}</a></li>`;
}
const pagerList = [
    navItem('first', '/keywords?page=1', 'First'),
    navItem('previous', '/keywords?page=1', 'Prev'),
    numberedItem(1, '/keywords?page=1'),
    `<li data-ut-numbered class="unified-pagination-item active"><span class="unified-pagination-link active" aria-current="page">2</span></li>`,
    numberedItem(3, '/keywords?page=3'),
    numberedItem(4, '/keywords?page=4'),
    navItem('next', '/keywords?page=3', 'Next'),
    navItem('last', '/keywords?page=5', 'Last'),
].join('');
const prototypes = `<ul hidden data-ut-protos>
  <li class="unified-pagination-item" data-ut-proto="page"><a class="unified-pagination-link" href="#" data-ut-page-link></a></li>
  <li class="unified-pagination-item active" data-ut-proto="current"><span class="unified-pagination-link active" aria-current="page" data-ut-page-link></span></li>
  <li class="unified-pagination-item disabled" data-ut-proto="gap"><span class="unified-pagination-ellipsis">...</span></li>
</ul>`;

documentRoot.appendChild(treeFromHtml(`
<div id="mainContent">
  <div data-unified-table='{"mode":"server","pageParam":"page"}'>
    <div class="ut-toolbar">
      <div class="ut-info">Showing <span data-ut-first>6</span>&ndash;<span data-ut-last>10</span> of <span data-ut-total>23</span></div>
    </div>
    <table id="keywordsTable"><tbody id="rowsBody">
      ${batchHtml(5, 6).replace(/^.*<tbody>|<\/tbody>.*$/g, '')}
    </tbody></table>
  </div>
  <div class="pagination-container" id="pagination">
    <div class="unified-pagination-container" data-endpoint="keywords_list"
         data-current-page="2" data-total-pages="5" data-page-size="5">
      <div class="unified-pagination-info"><span class="pagination-text">Page <span data-ut-page>2</span> of <span data-ut-pages>5</span></span></div>
      <div class="unified-pagination-controls">
        <div class="ut-load-more" data-ut-load-more data-table-id="keywordsTable"
             data-page="2" data-total-pages="5" data-total="23" data-shown="5"
             data-page-size="5" data-first-row="6">
          <button type="button" class="btn">Show More</button>
          <span class="ut-load-more-info">Showing <span data-ut-first>6</span>&ndash;<span data-ut-last>10</span> of <span data-ut-total>23</span></span>
          <span class="ut-load-more-error" data-ut-load-error hidden>retry</span>
        </div>
        <nav><ul class="unified-pagination-list" data-ut-pager-list>${pagerList}</ul>${prototypes}</nav>
        <div class="unified-pagination-jump">
          <input class="unified-pagination-jump-input" data-ut-jump value="2" data-total-pages="5" max="5">
        </div>
      </div>
    </div>
  </div>
</div>`));

await import('../../static/js/modules/ui/unified-table.js');

const block = documentRoot.querySelector('[data-ut-load-more]');
const pager = documentRoot.querySelector('.unified-pagination-container');
const wrapperInfo = documentRoot.querySelector('.ut-info');
const text = (selector, scope = documentRoot) => (scope.querySelector(selector) || {}).textContent;
const numberLinks = () => Array.from(pager.querySelectorAll('.unified-pagination-list .unified-pagination-link'))
    .filter((node) => /^\d+$/.test(node.textContent.trim()) && node.tagName === 'A')
    .map((node) => node.textContent.trim());
const activeNumber = () => (pager.querySelector('.unified-pagination-link.active') || {}).textContent;
const linkFor = (label) => Array.from(pager.querySelectorAll('.unified-pagination-link'))
    .find((node) => node.textContent.trim() === label);

// Batch 1: page 2 -> 3.
block.querySelector('button').dispatch('click');
await wait();
check('the batch asks for page 3 of the same view (sort and page size ride along)',
      served.length === 1 && served[0].includes('page=3') && served[0].includes('per_page=5')
      && served[0].includes('sort=name') && served[0].includes('order=asc'), served[0]);
check('the block moved to page 3 with 10 rows shown', block.getAttribute('data-page') === '3'
      && block.getAttribute('data-shown') === '10', `${block.getAttribute('data-page')}/${block.getAttribute('data-shown')}`);
check('the range reads 6-15 in the pager and in the toolbar',
      text('[data-ut-last]', pager) === '15' && text('[data-ut-last]', wrapperInfo) === '15'
      && text('[data-ut-first]', pager) === '6', text('[data-ut-last]', pager));
check('the pager says page 3 of 5', text('[data-ut-page]', pager) === '3' && text('[data-ut-pages]', pager) === '5');
check('the numbered links follow the page (window 1-5, page 3 active)',
      activeNumber() === '3' && numberLinks().join(',') === '1,2,4,5', `${activeNumber()} / ${numberLinks()}`);
check('Prev points at page 2, Next at page 4, Last at page 5',
      linkFor('Prev').getAttribute('href').includes('page=2')
      && linkFor('Next').getAttribute('href').includes('page=4')
      && linkFor('Last').getAttribute('href').includes('page=5'));
check('every page link keeps the sort (no lost view state)',
      linkFor('2').getAttribute('href').includes('sort=name') && linkFor('2').getAttribute('href').includes('per_page=5'),
      linkFor('2').getAttribute('href'));
check('the jump input shows page 3', pager.querySelector('.unified-pagination-jump-input').value === '3');
check('the pager container says page 3', pager.getAttribute('data-current-page') === '3');
check('the control is still offered (more pages)', block.hidden === false);

// Batch 2: an empty batch must not move the page.
nextBatch = batchHtml(0, 0);
block.querySelector('button').dispatch('click');
await wait();
check('an empty batch does not advance the page', block.getAttribute('data-page') === '3',
      block.getAttribute('data-page'));
check('an empty batch leaves the shown count alone', block.getAttribute('data-shown') === '10', block.getAttribute('data-shown'));
check('an empty batch hides the control (nothing more to load)', block.hidden === true);
check('the pager still says page 3 after an empty batch', pager.getAttribute('data-current-page') === '3',
      pager.getAttribute('data-current-page'));

// The control was hidden by the empty batch; the view is complete from here.
// Reset the state to page 3 with a visible control to continue the walk.
block.hidden = false;
block.setAttribute('data-page', '3');
block.setAttribute('data-shown', '10');
block.setAttribute('data-total-pages', '5');
pager.setAttribute('data-current-page', '3');

block.querySelector('button').dispatch('click');
await wait();
check('the walk continues to page 4 (15 shown)', block.getAttribute('data-page') === '4'
      && block.getAttribute('data-shown') === '15', block.getAttribute('data-shown'));
check('the numbered links move with it: window 2-5 plus page 1, page 4 active',
      activeNumber() === '4' && numberLinks().join(',') === '1,2,3,5', `${activeNumber()} / ${numberLinks()}`);

// Last batch: page 5 brings 3 rows; the range closes at 23.
block.querySelector('button').dispatch('click');
await wait();
check('the last batch brings page 5 (18 shown of 23)', block.getAttribute('data-page') === '5'
      && block.getAttribute('data-shown') === '18', block.getAttribute('data-shown'));
check('the range closes at 6-23', text('[data-ut-last]', pager) === '23' && text('[data-ut-last]', wrapperInfo) === '23');
check('the pager shows the last page: 1, ellipsis, 3-5 with page 5 active',
      activeNumber() === '5' && numberLinks().join(',') === '1,3,4', `${activeNumber()} / ${numberLinks()}`);
check('Next and Last are disabled on the last page',
      linkFor('Next').classList.contains('disabled') && linkFor('Next').getAttribute('aria-disabled') === 'true'
      && linkFor('Last').classList.contains('disabled'));
check('the control hides itself at the end', block.hidden === true);
check('the page list does not duplicate a number', new Set(numberLinks()).size === numberLinks().length,
      numberLinks().join(','));

const failed = checks.filter(([, ok]) => !ok).length;
console.log(`\n${checks.length - failed}/${checks.length} checks passed`);
process.exit(failed ? 1 : 0);

const fs = require('fs');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync(process.argv[2], 'utf8');
const errors = [];
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  beforeParse(window) {
    window.addEventListener('error', e => errors.push(String(e.error && e.error.stack || e.message)));
  }
});
const d = dom.window.document;
console.log('JS ERRORS:', errors.length ? errors.join('\n---\n') : '(none)');
console.log('player cards rendered:', d.querySelectorAll('#board .pc').length);
console.log('arch badges (🎭):', d.body.innerHTML.includes('🎭'));
console.log('grudge badges (💢):', d.body.innerHTML.includes('💢'));
console.log('log lines rendered:', d.querySelectorAll('#logbox div').length);
console.log('deck columns:', d.querySelectorAll('#deckgrid .deckcol').length);
console.log('seed label:', (d.getElementById('seedlbl')||{}).textContent);

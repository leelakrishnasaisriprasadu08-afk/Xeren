const fs = require('fs');

console.log('--- Verifying Showroom Chat Agent Files ---');

const html = fs.readFileSync('workspace/generated_sites/index.html', 'utf8');
const htm = fs.readFileSync('workspace/generated_sites/index.htm', 'utf8');
const css = fs.readFileSync('workspace/generated_sites/styles.css', 'utf8');
const js = fs.readFileSync('workspace/generated_sites/script.js', 'utf8');
const serverJs = fs.readFileSync('workspace/generated_sites/server.js', 'utf8');
const appPy = fs.readFileSync('workspace/generated_sites/app.py', 'utf8');

const requiredIds = [
  'chat-launcher-btn',
  'apex-chat-modal',
  'chat-messages',
  'chat-form',
  'chat-input',
  'chat-send-btn',
  'chat-typing-indicator',
  'chat-mic-btn',
  'chat-reset-btn',
  'chat-close-btn'
];

requiredIds.forEach(id => {
  if (!html.includes('id="' + id + '"')) throw new Error('index.html missing #' + id);
  if (!htm.includes('id="' + id + '"')) throw new Error('index.htm missing #' + id);
});
console.log('✓ All 10 DOM IDs verified in index.html & index.htm');

const requiredStyles = ['.apex-chat-widget', '.chat-launcher-btn', '.apex-chat-modal', '.chat-msg', '.chat-chip', '.chat-typing-indicator'];
requiredStyles.forEach(s => {
  if (!css.includes(s)) throw new Error('styles.css missing ' + s);
});
console.log('✓ All CSS classes verified in styles.css');

const requiredJs = ['initChatAgent', 'appendMessage', 'executeShowroomAction', 'generateLocalAIResponse', 'handleChatSubmit'];
requiredJs.forEach(fn => {
  if (!js.includes(fn)) throw new Error('script.js missing ' + fn);
});
console.log('✓ All JS chat agent functions verified in script.js');

if (!serverJs.includes('/api/chat')) throw new Error('server.js missing /api/chat route');
console.log('✓ Node server.js /api/chat endpoint verified');

if (!appPy.includes('/api/chat')) throw new Error('app.py missing /api/chat route');
console.log('✓ Python app.py /api/chat endpoint verified');

console.log('\nAll Showroom Chat Agent verifications PASSED successfully!');

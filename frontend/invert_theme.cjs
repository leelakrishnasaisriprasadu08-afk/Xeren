const fs = require('fs');
const path = require('path');

const replacements = [
  // Hardcoded dark backgrounds
  { from: /#0d1117/gi, to: '#ffffff' },
  { from: /#0f172a/gi, to: '#f8fafc' },
  { from: /#1e293b/gi, to: '#f1f5f9' },
  { from: /#111827/gi, to: '#ffffff' },
  { from: /#000000/g, to: '#ffffff' },
  { from: /#050811/g, to: '#ffffff' },
  { from: /#0a0f1d/g, to: '#f8fafc' },

  // Hardcoded borders and subtle backgrounds
  { from: /rgba\(255,\s*255,\s*255,\s*0\.0/g, to: 'rgba(0, 0, 0, 0.0' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.1/g, to: 'rgba(0, 0, 0, 0.1' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.2/g, to: 'rgba(0, 0, 0, 0.2' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.3/g, to: 'rgba(0, 0, 0, 0.3' },
  
  // Hardcoded text
  { from: /color:\s*#ffffff/gi, to: 'color: #0f172a' },
  { from: /color:\s*#fff;/gi, to: 'color: #0f172a;' },
  { from: /color:\s*white;/gi, to: 'color: #0f172a;' },
  { from: /color:\s*#f1f5f9/gi, to: 'color: #0f172a' },
  { from: /color:\s*#e2e8f0/gi, to: 'color: #1e293b' },
  { from: /color:\s*#94a3b8/gi, to: 'color: #475569' },
  { from: /color:\s*#cbd5e1/gi, to: 'color: #334155' },

  // SVG Strokes and Fills (except green)
  { from: /stroke="#ffffff"/gi, to: 'stroke="#0f172a"' },
  { from: /stroke="white"/gi, to: 'stroke="#0f172a"' },
  { from: /fill="#ffffff"/gi, to: 'fill="#0f172a"' },
  { from: /fill="white"/gi, to: 'fill="#0f172a"' }
];

function processDirectory(directory) {
  const files = fs.readdirSync(directory);
  for (const file of files) {
    const fullPath = path.join(directory, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      processDirectory(fullPath);
    } else if (fullPath.endsWith('.tsx') || fullPath.endsWith('.css')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      let changed = false;
      for (const { from, to } of replacements) {
        if (from.test(content)) {
          content = content.replace(from, to);
          changed = true;
        }
      }
      if (changed) {
        fs.writeFileSync(fullPath, content, 'utf8');
        console.log('Updated', fullPath);
      }
    }
  }
}

processDirectory('./src');
console.log('Done.');

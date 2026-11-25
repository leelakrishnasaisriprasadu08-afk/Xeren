const fs = require('fs');
const path = require('path');

const replacements = [
  // Background colors
  { from: /rgba\(13,\s*17,\s*23/g, to: 'rgba(255, 255, 255' },
  { from: /rgba\(15,\s*23,\s*42/g, to: 'rgba(255, 255, 255' },
  { from: /rgba\(10,\s*16,\s*31/g, to: 'rgba(255, 255, 255' },
  { from: /rgba\(22,\s*34,\s*62/g, to: 'rgba(240, 240, 240' },
  { from: /rgba\(24,\s*36,\s*68/g, to: 'rgba(245, 245, 245' },
  { from: /rgba\(0,\s*0,\s*0/g, to: 'rgba(255, 255, 255' }, // Sometimes pure black is used as bg

  // Glows / Text
  { from: /#050811/gi, to: '#ffffff' },
  { from: /#0a0f1d/gi, to: '#f8fafc' },
  { from: /#0f172a/gi, to: '#f8fafc' },
  { from: /#1e293b/gi, to: '#f1f5f9' },

  // Text colors specifically where they might have been white
  { from: /color:\s*rgba\(255,\s*255,\s*255,\s*0\.7\)/gi, to: 'color: rgba(0, 0, 0, 0.7)' },
  { from: /color:\s*rgba\(255,\s*255,\s*255,\s*0\.5\)/gi, to: 'color: rgba(0, 0, 0, 0.5)' },
  { from: /color:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/gi, to: 'color: rgba(0, 0, 0, 0.9)' },
  { from: /background:\s*#000000/g, to: 'background: #ffffff' },
  { from: /background-color:\s*#000000/g, to: 'background-color: #ffffff' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.0/g, to: 'rgba(0, 0, 0, 0.0' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.1/g, to: 'rgba(0, 0, 0, 0.1' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.2/g, to: 'rgba(0, 0, 0, 0.2' },
  { from: /rgba\(255,\s*255,\s*255,\s*0\.3/g, to: 'rgba(0, 0, 0, 0.3' },
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

// solve_waf.js - 解析 AnyRouter WAF acw_sc__v2 cookie
// 核心思路：WAF 脚本会设置 document.cookie 然后 reload
// 我们拦截 cookie setter 拿到值后立即退出，避免反调试死循环

const fs = require('fs');

const scriptFile = process.argv[2];
const scriptContent = fs.readFileSync(scriptFile, 'utf8');

// 5秒强制退出保护
const exitTimer = setTimeout(() => {
  console.log('{}');
  process.exit(0);
}, 5000);

const cookieMap = new Map();

const document = {
  set cookie(val) {
    const mainPart = val.split(';')[0];
    const eqIndex = mainPart.indexOf('=');
    if (eqIndex > 0) {
      const key = mainPart.slice(0, eqIndex).trim();
      const value = mainPart.slice(eqIndex + 1).trim();
      cookieMap.set(key, value);
    }
    // cookie 设置后立即输出并退出，避免后续的 reload 和反调试代码
    if (cookieMap.size > 0) {
      clearTimeout(exitTimer);
      console.log(JSON.stringify(Object.fromEntries(cookieMap)));
      process.exit(0);
    }
  },
  get cookie() {
    return [...cookieMap.entries()].map(([k, v]) => `${k}=${v}`).join('; ');
  },
  location: {
    reload() {
      // reload 被调用说明 cookie 已经设置完成
      if (cookieMap.size > 0) {
        clearTimeout(exitTimer);
        console.log(JSON.stringify(Object.fromEntries(cookieMap)));
        process.exit(0);
      }
    },
    href: 'https://anyrouter.top/',
    hostname: 'anyrouter.top',
    pathname: '/',
    protocol: 'https:',
    search: '',
    hash: '',
  },
};

const location = document.location;

try {
  eval(scriptContent);
} catch (err) {
  // ignore
}

// 如果到这里了，检查是否有 cookie
clearTimeout(exitTimer);
if (cookieMap.size > 0) {
  console.log(JSON.stringify(Object.fromEntries(cookieMap)));
} else {
  console.log('{}');
}

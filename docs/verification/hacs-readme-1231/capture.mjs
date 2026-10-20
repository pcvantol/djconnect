import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {chromium} from '/private/tmp/djc-api-browser-tools-prepared-v1/node_modules/playwright/index.mjs';
const sha=process.argv[2];
const output='/private/tmp/djc-readme1231-browser-'+sha.slice(0,8);
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Users/pcvantol/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'});
const records=[];
try {
for(const name of ['README.md','info.md'])for(const width of [320,375,390])for(const theme of ['light','dark']) {
 const page=await browser.newPage({viewport:{width,height:800},colorScheme:theme,deviceScaleFactor:1});
 const response=await page.goto(`https://github.com/pcvantol/djconnect/blob/${sha}/${name}`,{waitUntil:'domcontentloaded',timeout:60000});
 assert.equal(response.status(),200);
 const article=page.locator('article.markdown-body');
 await article.waitFor({timeout:30000});
 await article.locator('img[alt="DJConnect"]').evaluate(async n=>{await n.decode()});
 const result=await article.evaluate(n=>({text:n.innerText,width:n.clientWidth,scrollWidth:n.scrollWidth,htmlTheme:document.documentElement.getAttribute('data-color-mode'),image:[...n.querySelectorAll('img')].map(i=>({src:i.src,width:i.width,height:i.height,naturalWidth:i.naturalWidth})),links:[...n.querySelectorAll('a')].map(a=>a.href),overflow:[...n.querySelectorAll('*')].filter(x=>x.getBoundingClientRect().right>n.getBoundingClientRect().right+2).map(x=>x.tagName)}));
 assert(result.text.includes('Your music. Your DJ.'));
 assert(result.links.some(x=>x.startsWith('https://my.home-assistant.io/redirect/hacs_repository/')));
 assert.equal(result.image[0].width,64);assert.equal(result.image[0].height,64);assert(result.image[0].naturalWidth>0);
 assert(result.scrollWidth<=result.width+2,JSON.stringify(result));
 await page.screenshot({path:`${output}/${name}-${width}-${theme}.png`,fullPage:true});
 records.push({name,width,theme,url:page.url(),status:response.status(),...result});
 await page.close();
}
 const page=await browser.newPage(); const r=await page.goto('https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration',{waitUntil:'domcontentloaded'});
 records.push({kind:'public HACS redirect landing only',status:r.status(),url:page.url(),text:await page.locator('body').innerText()});await page.close();
} finally {await browser.close();await fs.writeFile(output+'/results.json',JSON.stringify({source_sha:sha,scope:'Actual GitHub blob Markdown rendering; NOT installed HACS or HA frontend acceptance',records},null,2));}
console.log(JSON.stringify({output,cases:records.length}));

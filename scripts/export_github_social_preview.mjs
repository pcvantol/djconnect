/** Export existing approved Brand V2 assets as a GitHub preview. No publication. */
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {chromium} from 'playwright';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sourceCommit='7e14e5970b3f68d33d243ae6bab2b281fad59bb2';
const asset='assets/djconnect/brand-v2/wordmark-primary-dark.png';
const manifestPath='assets/djconnect/brand-v2/manifest.json';
const sha=data=>createHash('sha256').update(data).digest('hex');
const blob=name=>execFileSync('git',['show',`${sourceCommit}:${name}`],{cwd:root,maxBuffer:5*1024*1024});
const args=process.argv.slice(2);
const option=name=>{const i=args.indexOf(name);return i<0?undefined:args[i+1];};
const output=option('--output');
const executablePath=option('--browser-executable');
if(!output)throw new Error('Explicit output directory required; this does not publish settings.');
const wordmark=blob(asset),brandManifest=blob(manifestPath);
const record=JSON.parse(brandManifest).files[asset];
if(sha(wordmark)!==record.sha256||record.width!==2048||record.height!==512||record.theme!=='dark')throw new Error('Approved source mismatch');
const svg=`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1280" height="640" viewBox="0 0 1280 640">
<defs><radialGradient id="cyan"><stop stop-color="#12356a"/><stop offset="1" stop-color="#12356a" stop-opacity="0"/></radialGradient><radialGradient id="violet"><stop stop-color="#32205b"/><stop offset="1" stop-color="#32205b" stop-opacity="0"/></radialGradient></defs>
<rect width="1280" height="640" fill="#091126"/><ellipse cx="60" cy="320" rx="720" ry="540" fill="url(#cyan)"/><ellipse cx="1250" cy="300" rx="760" ry="600" fill="url(#violet)"/>
<image x="128" y="192" width="1024" height="256" xlink:href="data:image/png;base64,${wordmark.toString('base64')}"/>
</svg>\n`;
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
let png,rendererVersion;
try{
 rendererVersion=browser.version();
 const page=await browser.newPage({viewport:{width:1280,height:640},deviceScaleFactor:1});
 await page.route(/https?:\/\//,route=>route.abort());
 await page.setContent(`<html><head><style>html,body{margin:0;width:1280px;height:640px;overflow:hidden}img{display:block;width:1280px;height:640px}</style></head><body><img src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}" alt=""></body></html>`);
 await page.locator('img').evaluate(image=>image.decode());
 png=await page.screenshot({type:'png',omitBackground:false});
 if(png.length>=1000000||png.readUInt32BE(16)!==1280||png.readUInt32BE(20)!==640)throw new Error('Preview dimensions/size rejected');
}finally{await browser.close();}
const files={'social-preview-v2.svg':Buffer.from(svg),'social-preview-v2.png':png};
for(const [name,bytes] of Object.entries(files))await writeFile(path.join(output,name),bytes,{flag:'wx'});
const manifest={schema_version:1,brand_version:2,producer_repository:'pcvantol/djconnect',
 approved_brand_source_commit:sourceCommit,approved_brand_manifest_sha256:sha(brandManifest),
 wordmark_source:{path:asset,sha256:sha(wordmark),width:2048,height:512},
 recipe_sha256:sha(await readFile(fileURLToPath(import.meta.url))),
 rendering:{engine:'Chromium',version:rendererVersion,device_scale_factor:1,color_profile:'sRGB'},
 width:1280,height:640,format:'PNG',background:'opaque navy; approved transparent wordmark composited without additional border',
 brand_placement:{x:128,y:192,width:1024,height:256},crop_policy:'Keep the entire centered wordmark and tagline; do not enlarge or crop to the glass icon.',
 tagline:'Your music. Your DJ.',usage:'Same exact PNG for supported DJConnect repository social previews; settings upload/readback is a separate operation.',
 acceptance:'LOCAL_EXPORT_REVIEW_ONLY; not proof of GitHub settings, protected delivery or consumer adoption',
 files:Object.fromEntries(Object.entries(files).map(([name,bytes])=>[name,{sha256:sha(bytes),bytes:bytes.length}]))};
await writeFile(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({png_sha256:manifest.files['social-preview-v2.png'].sha256,bytes:png.length,width:1280,height:640,source_commit:sourceCommit,settings:'NOT_CHANGED'}));

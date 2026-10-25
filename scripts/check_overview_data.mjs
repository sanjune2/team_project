import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { readOverview, ovList, ovSuggestion, ovHeadline, ovShort, ovDetail } from '../frontend/src/utils/overview.js';
const root=new URL('../frontend/public/reference/',import.meta.url);
const files=(await fs.readdir(root)).filter(f=>f!=='index.json'&&f.endsWith('.json'));
assert.equal(files.length,12);
for(const file of files){
 const result=JSON.parse(await fs.readFile(new URL(file,root),'utf8'));const ov=readOverview(result);
 assert.ok(ov);assert.ok(ovList(ov,'left')?.length);assert.ok(ovList(ov,'right')?.length);
 assert.equal(Boolean(ovSuggestion(ov)),!file.endsWith('_all.json'));
 for(const c of ov.categories){
  assert.deepEqual(ovDetail(ov,c.category),c.groups.length?c.groups.slice(0,5).map(g=>g.detail):null);
  for(const s of ['positive','negative']){
   assert.equal(ovHeadline(ov,c.category,s),c.headline[s]);
   const expected=c.groups.filter(g=>g.sentiment===s).slice(0,3).map(g=>g.short);
   assert.deepEqual(ovShort(ov,c.category,s),expected.length?expected:null);
  }
 }
}
console.log(JSON.stringify({files:12,frontend_reader_checks:'passed',new_api_calls:0}));

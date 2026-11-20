const test = require('node:test');
const assert = require('node:assert/strict');
const {groupTransfers,summarize} = require('../public/transfer-groups.js');
const file = (key,size,offset,state='sending',groupId='folder') => ({key,path:key,groupId,groupName:'Minha pasta',size,offset,state});
test('pasta mostra uma linha e usa bytes totais, não média por arquivo',()=>{
  const groups=groupTransfers([file('a',10,10,'done'),file('b',90,0)]);
  assert.equal(groups.length,1); assert.equal(summarize(groups[0]).percent,10);
});
test('nomes iguais em envios diferentes mantêm grupos separados',()=>assert.equal(groupTransfers([file('a',1,0,'queued','one'),file('b',1,0,'queued','two')]).length,2));
test('100 por cento somente após confirmação de todos os arquivos',()=>{
  const group=groupTransfers([file('a',10,10)])[0]; assert.equal(summarize(group).percent,99);
  group.items[0].state='done'; assert.equal(summarize(group).percent,100);
});
test('arquivos vazios não produzem NaN e concluem corretamente',()=>{
  const group=groupTransfers([file('a',0,0,'done'),file('b',0,0,'queued')])[0];assert.equal(summarize(group).percent,50);group.items[1].state='done';assert.equal(summarize(group).percent,100);
});
test('cancelados somem; concluídos permanecem',()=>assert.equal(groupTransfers([file('a',10,10,'done'),file('b',10,1,'cancelled')])[0].items.length,1));
test('pausa e velocidade combinam todos os membros',()=>{
  const group=groupTransfers([{...file('a',10,3),speed:20},{...file('b',20,5),speed:30}])[0];assert.equal(summarize(group).speed,50);group.items.forEach(f=>f.state='paused');assert.equal(summarize(group).state,'paused');assert.equal(summarize(group).speed,0);
});

(function(root) {
  'use strict';
  function groupTransfers(transfers) {
    const groups = new Map();
    for (const t of transfers) {
      if (t.state === 'cancelled') continue;
      const id = t.groupId || t.key;
      if (!groups.has(id)) groups.set(id, {id, name:t.groupName || t.path, folder:!!t.groupId, items:[]});
      groups.get(id).items.push(t);
    }
    return [...groups.values()];
  }
  function summarize(group) {
    const items = group.items;
    const size = items.reduce((sum,t) => sum + t.size,0);
    const sent = items.reduce((sum,t) => sum + Math.min(t.size,t.state === 'done' ? t.size : (t.offset || 0) + (t.loaded || 0)),0);
    const done = items.filter(t => t.state === 'done').length;
    const state = done === items.length ? 'done' : items.some(t => t.state === 'sending') ? 'sending' : items.some(t => t.state === 'queued') ? 'queued' : items.some(t => t.state === 'error') ? 'error' : items.some(t => t.state === 'reselect') ? 'reselect' : 'paused';
    const speed = items.filter(t => t.state === 'sending').reduce((sum,t) => sum + (t.speed || 0),0);
    const percent = state === 'done' ? 100 : Math.min(99,Math.floor((size ? sent/size : done/items.length) * 100));
    return {size,sent,done,count:items.length,state,speed,percent,error:items.find(t => t.error && t.state === 'error')?.error};
  }
  const api = {groupTransfers,summarize};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TransferGroups = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

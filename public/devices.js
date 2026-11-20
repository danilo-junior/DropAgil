'use strict';
// Browsers participate only while this page stays open. Native apps use notifications.
let receivingHere = false, destinationBusy = false;
const destinationBox = document.createElement('section');
destinationBox.className = 'destination-box';
destinationBox.innerHTML = '<label for="sendDestination">Enviar para</label><select id="sendDestination"><option value="">Rede • todos os dispositivos</option></select><button id="refreshDestinations" class="button secondary">Atualizar</button><button id="receiveHere" class="button secondary">Receber neste dispositivo</button><small>Para aparecer na lista, ative o recebimento no outro aparelho. O computador central precisa ficar ligado.</small><div id="incomingFiles"></div>';
$('dropzone').before(destinationBox);
async function updateDestinations() {
  if (destinationBusy) return;
  destinationBusy = true;
  try {
    const result = receivingHere
      ? await post('/api/devices', {name: $('deviceName').value || (status?.local ? 'Computador principal' : 'Navegador do celular')})
      : await api('/api/devices');
    const select = $('sendDestination'), selected = select.value;
    const entries = [{id:'', name:'Rede • todos os dispositivos'}, ...result.devices];
    if (selected && !entries.some(d => d.id === selected)) entries.push({id:selected,name:'Destino selecionado • indisponível agora'});
    select.replaceChildren(...entries.map(d => { const option = document.createElement('option'); option.value = d.id; option.textContent = d.name; return option; }));
    select.value = selected;
    if (receivingHere) await renderInbox();
  } catch (e) { /* Login and temporary network loss are handled by the main page. */ }
  finally { destinationBusy = false; }
}
$('refreshDestinations').onclick = updateDestinations;
$('receiveHere').onclick = () => {
  receivingHere = !receivingHere;
  $('receiveHere').textContent = receivingHere ? 'Parar de receber nesta página' : 'Receber neste dispositivo';
  if (receivingHere) toast('Disponível para receber. Mantenha esta página aberta; os pedidos aparecerão aqui.');
  else $('incomingFiles').replaceChildren();
  updateDestinations();
};
async function renderInbox() {
  const {items} = await api('/api/inbox');
  const box = $('incomingFiles');
  if (box.dataset.items === JSON.stringify(items)) return;
  box.dataset.items = JSON.stringify(items); box.replaceChildren();
  for (const file of items) {
    const row = document.createElement('div'); row.className = 'incoming-row';
    const label = document.createElement('span'); label.textContent = `${file.sender || 'Dispositivo'} → ${file.path} (${bytes(file.size)})`; row.append(label);
    const accept = document.createElement('button'); accept.className = 'button primary'; accept.textContent = file.status === 'accepted' ? 'Baixar novamente' : 'Aceitar e baixar';
    accept.onclick = async () => {
      accept.disabled = true;
      try {
        await post(`/api/inbox/${file.id}`, {action:'accept'});
        const link = document.createElement('a'); link.href = `/api/inbox/${file.id}/download`; link.download = ''; row.append(link); link.click(); link.remove();
        toast('Download solicitado. Depois de terminar, use “Limpar entrega” para liberar a cópia temporária.');
        box.dataset.items = ''; await renderInbox();
      } catch (e) { toast(e.message); }
      finally { accept.disabled = false; }
    };
    const reject = document.createElement('button'); reject.className = 'button secondary danger'; reject.textContent = file.status === 'accepted' ? 'Limpar entrega' : 'Recusar';
    reject.onclick = async () => {
      if (!confirm(file.status === 'accepted' ? 'O download já terminou? Apagar a cópia temporária desta entrega?' : `Recusar o recebimento de “${file.path}”?`)) return;
      try { await post(`/api/inbox/${file.id}`, {action:'reject'}); box.dataset.items = ''; await renderInbox(); } catch(e) { toast(e.message); }
    };
    row.append(accept,reject); box.append(row);
  }
}
setInterval(updateDestinations, 5000);
updateDestinations();

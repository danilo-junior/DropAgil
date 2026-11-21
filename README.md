# DropAgíl

O DropAgíl transfere arquivos e pastas entre computadores, celulares e navegadores na mesma rede local. O computador Windows funciona como central: guarda os arquivos enviados para a rede e encaminha entregas privadas. Não exige conta nem nuvem. A central precisa estar ligada durante envios, downloads e atualizações Android.

## Onde usar

| Interface | Funções |
| --- | --- |
| Aplicativo Windows (DropAgil.exe) | Bandeja, envio pelo Explorador, recebimento, arquivos da rede, dispositivos e conexão. Não precisa de Python para uso diário. |
| Aplicativo Android (DropAgil-Android.apk) | Envio pelo app ou pelo menu Compartilhar, recebimento por notificação, navegação e downloads. Requer Android 10 ou superior. |
| Página local | Envio, recebimento, downloads e gerenciamento pelo navegador, sem instalar aplicativo no aparelho visitante. |

O pacote DropAgil-Windows.zip contém o EXE, o APK, os metadados de atualização e os atalhos de instalação. **Mantenha DropAgil-Android.apk e DropAgil-Android.version.json ao lado do EXE** para oferecer o app e suas atualizações aos celulares.

## Instalar no Windows

1. Extraia a pasta DropAgil do ZIP para um local gravável e definitivo, por exemplo C:\DropAgil. Evite movê-la depois de parear aparelhos: nela ficam Recebidos e os dados de pareamento.
2. Abra DropAgil.exe ou Iniciar-DropAgil.bat. Na primeira abertura normal, o programa registra automaticamente o início com o seu usuário do Windows e os dois comandos do botão direito. Instalar-Windows.bat também registra a integração e inicia o programa.
3. Procure o ícone perto do relógio e abra Transferências. Fechar ou esconder a janela mantém o aplicativo na bandeja.
4. Se o Firewall do Windows perguntar, permita acesso em **redes privadas**. O PC pode usar cabo e o celular Wi-Fi, desde que estejam na mesma rede e o roteador permita comunicação entre eles.
5. Na aba Conexão, veja endereço, QR Code e código de acesso da central. No próprio PC, a página fica em http://localhost:8787. Em outros aparelhos, use o endereço de rede mostrado pelo DropAgíl; localhost no celular aponta para o próprio celular.

O DropAgíl inicia **após o login do Windows**, oculto na bandeja. Ele não roda antes da tela de login. Para desativar o início automático e remover os atalhos do Explorador, execute Remover-Integracao-Windows.bat. Essa escolha fica salva: abrir o app depois não reativa a integração. Para ativá-la novamente, execute Instalar-Windows.bat ou use Conexão e ajustes → Ativar / atualizar integração.

## Instalar no Android

1. Obtenha DropAgil-Android.apk no pacote Windows ou na página da central, em Conectar dispositivo → Baixar aplicativo Android.
2. Abra o APK no celular e confirme a instalação. Se o Android pedir permissão para instalar arquivos dessa origem, autorize nas configurações exibidas.
3. Abra o DropAgíl, informe o endereço completo do PC e o código mostrado na aba Conexão, depois toque em Conectar computador. O pareamento fica salvo.
4. Permita as notificações. Após o pareamento, o recebimento vem **ativado por padrão** e uma notificação indica que o celular está disponível. O botão de recebimento na aba Transferir permite desligá-lo e religá-lo.

Depois de reiniciar o celular ou atualizar o APK, o Android tenta iniciar o **serviço de recebimento** automaticamente, sem abrir a tela do app. A disponibilidade depende das permissões de notificação e das regras de bateria e execução do aparelho. Se você usar Forçar parada, abra o app novamente. Se desativar o recebimento, essa escolha será respeitada. O computador central precisa estar ligado para o celular aparecer na rede.

## Funções

### Enviar para a rede

Escolha **Rede** como destino. Os arquivos chegam a Recebidos no PC e aparecem em Arquivos da rede para os aparelhos conectados. O envio copia os arquivos e preserva os originais. Pastas mantêm a estrutura e aparecem como uma linha na fila. Nomes repetidos recebem um sufixo, sem substituir o arquivo existente.

- **Windows:** use Enviar arquivos ou Enviar pasta na aba Transferências. No Explorador, clique com o botão direito e escolha DropAgíl — Enviar para a rede. O atalho não abre a janela principal; uma notificação informa conclusão ou falha.
- **Android:** selecione arquivos ou pasta na aba Transferir. Pela Galeria, Arquivos ou outro app, use Compartilhar → DropAgíl. Se o aparelho já estiver pareado, escolha o destino na janela compacta e acompanhe o envio pela notificação.
- **Navegador:** arraste arquivos para a página ou use Escolher arquivos e Enviar pasta. A seleção de pastas depende do navegador.

### Enviar para um aparelho específico

Escolha um dispositivo disponível em **Enviar para**. A entrega fica em uma área privada da central e **não aparece em Arquivos da rede**. O destinatário recebe um pedido e precisa Aceitar ou Recusar. No Windows, a janela compacta Receber pelo DropAgíl? fica à frente dos outros programas. No Android, as ações aparecem na notificação e na tela aberta por ela. No navegador, ative Receber neste dispositivo e mantenha a página aberta.

No Explorador do Windows, DropAgíl — Enviar para dispositivo… abre só uma pequena janela de escolha. No Windows 11, os comandos podem estar em Mostrar mais opções. Arquivos aceitos no Windows e Android vão para Downloads/DropAgil; no Android, cada recebimento usa uma subpasta para evitar sobrescritas. No navegador, o download é entregue ao próprio navegador; depois use Limpar entrega.

### Arquivos da rede e QR rápido

Em Arquivos da rede, navegue pelas pastas, busque pelo nome, baixe arquivos e exclua cópias compartilhadas. A exclusão pede confirmação e é permanente para a cópia da rede; não apaga o arquivo original usado no envio. Pastas são baixadas como ZIP. O Windows mostra progresso e permite cancelar o download. No Android, o gerenciador de downloads acompanha o arquivo, que vai para Downloads.

Para entregar **um arquivo** a um visitante sem instalar ou configurar o DropAgíl, escolha QR rápido no aplicativo Windows ou na página. Qualquer pessoa com o QR Code ou link, na mesma rede, pode baixar somente aquele arquivo. O link expira em **uma hora** e pode ser encerrado antes. O PC precisa permanecer ligado. Para uma pasta, gere um ZIP; o QR rápido não é oferecido diretamente para pastas.

### Filas, dispositivos e conexão

- As filas mostram progresso, bytes e tempo. Pausar, Retomar e Cancelar tudo atuam somente na fila daquele cliente. Cancelar preserva arquivos já concluídos.
- Linhas concluídas somem da fila após 30 segundos, sem apagar os arquivos. Falhas e itens pausados continuam visíveis.
- A lista Dispositivos mostra aparelhos disponíveis. Renomeie-os no Windows, no Android ou na página; o nome é salvo na central e aparece para todos.
- Conexão mostra endereço, QR Code e código de acesso. Os aplicativos Windows e Android também têm Abrir página para abrir a interface local no navegador.
- Você pode colocar arquivos diretamente em Recebidos no PC e atualizar a lista. Assim evita uma segunda cópia de arquivos grandes.

## Atualizar

### Windows

1. Obtenha o novo DropAgil-Windows.zip. Faça backup da pasta atual, principalmente Recebidos e .dropagil. Se você compila APKs, preserve também .dropagil/android-debug.keystore.
2. Saia da bandeja. A central pode continuar rodando; se ainda houver processos DropAgil.exe no Gerenciador de Tarefas, encerre-os antes de substituir o EXE.
3. Copie **o conteúdo da pasta DropAgil dentro do ZIP** sobre a pasta de instalação existente, substituindo os arquivos do pacote. Preserve Recebidos e .dropagil para manter arquivos e pareamentos.
4. Abra o novo EXE ou reinicie o Windows. Se necessário, atualize os atalhos na aba Conexão ou execute Instalar-Windows.bat.

### Android pela rede

1. Na pasta da central Windows em execução, coloque juntos o novo DropAgil-Android.apk e DropAgil-Android.version.json. O ZIP Windows atualizado já contém ambos.
2. Deixe PC e celular na mesma rede, com o app Android pareado com a central.
3. Abra o DropAgíl no celular. Desde a versão **4.2**, ele consulta a central a cada abertura. Se houver um código de versão maior, baixa o APK, confere tamanho, SHA-256, pacote e assinatura e solicita a instalação ao Android.
4. Na primeira atualização, permita Instalar apps desconhecidos para o DropAgíl se o Android pedir. Alguns aparelhos também pedem confirmação; outros podem concluir sem intervenção. Reabra o app e confira a versão na aba Conexão.

Se não aparecer atualização, confira o endereço salvo no celular, a conexão com a central e se os dois arquivos estão ao lado do EXE usado. Versões anteriores à 4.2 precisam receber o APK manualmente uma vez. **Conserve a mesma chave de assinatura**: outro certificado não atualiza um app já instalado.

## Rede, armazenamento e limites

- A central usa a porta **8787**. Redes de visitantes, isolamento Wi-Fi, VPN e firewall podem bloquear o acesso. Não é preciso encaminhar portas no roteador.
- O código de seis dígitos muda a cada inicialização da central. As sessões da página expiram após 24 horas ou ao reiniciar. Pareamentos dos aplicativos persistem e podem ser revogados.
- O tráfego é **HTTP local, sem criptografia de transporte**. Use uma rede de confiança e não exponha a porta à internet. Quem tiver um link QR rápido válido poderá baixar o arquivo indicado.
- Envios usam blocos de até **8 MiB** e admitem retomada. No navegador, após fechar a página, selecione os mesmos arquivos no mesmo navegador e endereço, sem mudar os originais. Apagar dados do navegador pode perder a associação. Downloads individuais aceitam HTTP Range; ZIPs em fluxo recomeçam se interrompidos.
- O tamanho máximo prático depende de espaço em disco, sistema de arquivos, navegador e aparelho. FAT32 não aceita arquivos acima de 4 GB; use NTFS ou exFAT. Não apague .dropagil durante uma transferência.
- Android e navegadores podem limitar trabalho em segundo plano. Mantenha a página aberta em envios longos. O PC deve permanecer ligado e sem suspensão.

## Compilar pelo código-fonte

Para Windows, use Python 3.11 ou superior. Para Android, use também JDK 21. A preparação Android baixa uma vez as ferramentas oficiais do SDK; a instalação das dependências de build requer internet.

    python -m pip install -r requirements-build.txt
    python build_windows.py
    python android/tools/prepare_sdk.py
    python android/tools/build.py
    python package_release.py

O build gera DropAgil-Android.apk e DropAgil-Android.version.json na raiz. Mudanças em fontes ou recursos Android elevam o código da versão; recompilar os mesmos arquivos mantém o código. A assinatura local fica em .dropagil/android-debug.keystore. Faça backup dessa chave para continuar atualizando celulares já instalados. Ela não entra no pacote de código.

Para rodar somente a central pelo código, instale requirements.txt e execute python server.py. Nesse modo, --port e --data-dir permitem mudar porta e diretório dos dados. Para testar:

    python -m unittest discover -s tests -v
    node --check public/app.js
    node --test tests/test_groups.cjs

Veja [android/README.md](android/README.md) para detalhes de permissões, notificações e compilação Android.

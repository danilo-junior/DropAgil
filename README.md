# DropAgíl

Arquivos e pastas entre computador e celular, pela rede local. Interface em português, sem conta e sem serviços externos. O computador funciona como central: envios para **Rede** ficam em `Recebidos`. Envios para um **dispositivo** aguardam o aceite do destinatário em uma área separada, sem aparecer na lista pública.

## Versão 4 — aplicativo desktop

- **DropAgil.exe**: aplicativo Windows independente, sem precisar instalar Python. Telas nativas de transferências, arquivos, dispositivos e conexão com QR Code. Para usar, extraia o pacote Windows em uma pasta gravável e abra o executável; mantenha essa pasta no mesmo lugar após configurar o início automático.
- **Arquivos da rede** no desktop: navegação, busca, download em blocos com progresso, cancelamento e exclusão com confirmação. Pastas são baixadas em ZIP.
- **Dois comandos no botão direito**, em arquivos e pastas: **DropAgíl — Enviar para a rede** inicia diretamente; **DropAgíl — Enviar para dispositivo…** abre somente a escolha dos aparelhos. No Windows 11, aparecem também em Mostrar mais opções. Atualize a integração em Conexão e ajustes ou execute Instalar-Windows.bat.
- **Renomear dispositivos**: no desktop, aba Dispositivos; no Android, aba Conexão; na página, botão Renomear dispositivo. O nome fica salvo na central e é mostrado para toda a rede. Para renomear este navegador, deixe Rede selecionado e ative o recebimento.
- **Limpeza da fila após 30 segundos** no Windows, Android e navegador. Somente linhas concluídas são retiradas; arquivos enviados, envios pausados e falhas são preservados.
- **Recebimento Android ativado por padrão** para celulares pareados, depois de conceder notificações. Abre automaticamente ao iniciar o app, após atualização do APK e após reiniciar o Android quando permitido pelo sistema. Desativar manualmente é respeitado. Após fechamento forçado, abra o aplicativo novamente.
- **Aceitar / Recusar no aviso compacto, expandido e flutuante**. Um toque na notificação abre uma confirmação com botões grandes. Android, configurações de notificação, tela bloqueada, Não Perturbe e regras do fabricante ainda controlam a exibição; o app não força tela cheia nem permissões de sobreposição.

### Gerar os aplicativos

```powershell
python -m pip install -r requirements-build.txt
python build_windows.py
python android/tools/prepare_sdk.py
python android/tools/build.py
```

O executável é gerado na raiz do projeto. Coloque o APK na mesma pasta para disponibilizá-lo pelo computador. Dados, chaves de assinatura, arquivos recebidos, caches e binários de build não entram no Git. Conserve a chave Android local para atualizar a instalação existente.

## Novidades da versão 3

- Identidade visual compartilhada no Android e na central Windows, com botão **Abrir página** em ambos.
- Android com abas Transferir, Arquivos e Conexão. Ao compartilhar pela galeria, uma pequena janela permite escolher o destino; o envio segue pela notificação, sem abrir a tela principal quando já estiver pareado e com notificações permitidas.
- **Enviar para**: escolha Rede ou um dispositivo disponível. O servidor no computador intermedeia a transferência e precisa permanecer ligado.
- No Android de destino, ative **Receber arquivos neste celular**. Toque **Aceitar** ou **Recusar** na notificação. Os downloads vão para `Downloads/DropAgil`, em subpastas por arquivo para evitar sobrescritas. Após fechar à força, abra o app novamente; o recebimento automático respeita as limitações do Android.
- No Windows, a bandeja fica disponível para receber e pede confirmação antes de salvar em Downloads/DropAgil. Os dois comandos do menu de contexto separam o envio à rede do envio a um dispositivo.
- No navegador, use **Receber neste dispositivo** e mantenha a página aberta. Aceite pelo cartão que aparecer. Depois do download, use **Limpar entrega**; o navegador não informa com segurança ao site quando o download terminou.
- A cópia temporária de uma entrega direta é removida ao recusar ou após confirmação de download dos apps nativos. Entregas sem resposta permanecem no computador aguardando o destinatário.
- **Apagar** arquivos/pastas pela página ou pelo Android, com confirmação de exclusão permanente. Apaga somente a cópia da rede. Pastas com uploads pendentes são protegidas; conclua ou cancele os uploads primeiro.

## Recursos de transferência

- Pastas enviadas sem ZIP aparecem em **uma única linha**, com porcentagem calculada pelo total de bytes, contador de arquivos concluídos e controles da pasta inteira.
- **Tempo decorrido**, tempo total ao concluir e estimativa restante. O tempo decorrido conta o período desde o início do envio, incluindo pausas; a estimativa depende da velocidade recente.
- **Cancelar tudo** para parar rapidamente a fila do navegador, a fila do Windows ou a fila do app Android. Cada controle atua na fila daquele cliente e preserva os arquivos já concluídos.
- **Windows:** bandeja perto do relógio, janela de progresso com botão Esconder e envio de arquivos/pastas pelo botão direito.
- **Android nativo:** instalação do APK, envio pela Galeria > Compartilhar > DropAgíl, seleção de múltiplos arquivos, pastas e downloads no próprio app.

## Windows: instalar uma vez

Execute **Instalar-Windows.bat**. A instalação registra o DropAgíl para iniciar **ao entrar no seu usuário do Windows**, sem precisar abrir o site. Não é um serviço que roda antes da tela de login. O registro é por usuário e não pede administrador.

No Explorador, selecione um arquivo ou pasta e use **Enviar via DropAgíl** no botão direito. No Windows 11, pode estar em **Mostrar mais opções**. A janela mostra nome, progresso e tempo; **Esconder** mantém o envio em segundo plano. Na bandeja, use Transferências, Enviar arquivos, Enviar pasta, Arquivos da rede ou Abrir pasta Recebidos.

Os originais são preservados. O envio do Windows faz uma cópia para `Recebidos`; portanto precisa de espaço livre. Arquivos que já estão em `Recebidos` já estão compartilhados e não precisam de nova cópia.

**Iniciar-DropAgil.bat** abre a bandeja manualmente se necessário. **Remover-Integracao-Windows.bat** remove o início automático e o menu de contexto, mantendo os arquivos. A opção Sair da bandeja pausa a fila nativa; a central de arquivos pode continuar em execução.

## Android: compartilhar direto da Galeria

Instale **DropAgil-Android.apk** (Android 10 ou superior). Ele também está disponível na página **Conectar dispositivo > Baixar aplicativo Android**. Na primeira abertura, informe endereço e código da central e toque em Conectar computador. Depois selecione fotos ou vídeos na Galeria, toque Compartilhar > **DropAgíl** e escolha **Rede** ou o aparelho de destino.

O pareamento persiste após reiniciar a central. Se o endereço IP do computador mudar, atualize a configuração do aplicativo. Dentro do app, abra Arquivos da rede para baixar diretamente para Downloads. Consulte `android/README.md` para detalhes, permissões e limitações do Android.

## Começar no Windows

1. Tenha Python **3.11 ou superior** instalado, com a opção **Add Python to PATH**.
2. Opcional, para QR Code: abra o terminal nesta pasta e execute `python -m pip install -r requirements.txt`. Essa instalação requer internet; o uso diário não.
3. Execute **Instalar-Windows.bat** para a experiência completa de bandeja, ou `python server.py` no terminal para usar só a central.
4. No computador, abra **http://localhost:8787**. A seção **Conectar dispositivo** mostra endereço, QR Code e código de acesso.
5. Conecte o celular ao Wi-Fi do mesmo roteador, abra o endereço exibido (por exemplo `http://192.168.1.10:8787`) e digite o código. **localhost no celular não é o computador.**
6. Se o Windows perguntar, permita o Python em **redes privadas**. Não é necessário encaminhar portas no roteador.

PC por cabo e celular por Wi-Fi funcionam juntos: ambos precisam estar na mesma rede com comunicação entre os clientes permitida. Redes de visitantes e isolamento de clientes podem impedir o acesso. Se existirem vários endereços, escolha o IP da placa ligada ao roteador, e não um adaptador de VPN ou máquina virtual. Se o IP mudar, reinicie o servidor e use o endereço atualizado.

## Enviar e receber

- **Celular → PC:** selecione arquivos no celular. Eles chegam à pasta `Recebidos`, ao lado de `server.py`.
- **PC → celular:** selecione arquivos na página do PC; depois baixe em **Arquivos da rede** no celular.
- **Sem duplicar arquivos grandes no PC:** mova os arquivos/pastas pelo Explorador para `Recebidos` e atualize a lista. Também é possível iniciar o sistema com `--data-dir` em outro disco. O programa compartilha apenas a subpasta `Recebidos` desse diretório.
- **Pastas:** a estrutura dos arquivos selecionados é preservada; para baixar a pasta inteira, use **ZIP**. Ele é gerado durante o download, sem criar uma segunda cópia temporária. Pastas vazias não são enviadas pelo seletor do navegador. A seleção de pastas no celular depende do navegador; enviar um ZIP é uma alternativa.
- Arquivos com nomes repetidos recebem um sufixo, sem substituir os existentes. Nomes incompatíveis com Windows são recusados com uma mensagem.
- Para excluir arquivos ou pastas concluídos, use **Apagar** na página ou no Android. É uma exclusão permanente da cópia da rede, com confirmação. Para organizar pastas, também pode usar o Explorador no computador.

## Arquivos grandes e retomada

- Envios em blocos de **8 MiB**, até **dois arquivos simultâneos**. O servidor copia em blocos de até 1 MiB para disco, sem carregar o arquivo inteiro na RAM. O navegador mantém somente o bloco atual por envio.
- Pausa, retomada, progresso, velocidade estimada e tentativas automáticas após falha.
- Se a página fechar ou o servidor reiniciar, selecione os **mesmos arquivos ou a mesma pasta** no mesmo navegador e endereço. O identificador salvo no navegador retoma o ponto confirmado no disco. Mantenha o arquivo original intacto: a associação usa caminho, tamanho e data de modificação, não um hash completo do arquivo.
- Se apagar os dados do navegador, mudar de endereço ou usar modo privado, os identificadores de retomada podem se perder. Partes pendentes ficam em `.dropagil` até serem canceladas. Não apague essa pasta com o servidor rodando.
- Downloads individuais suportam HTTP Range para retomada por navegadores/gerenciadores compatíveis. A interface delega o download ao navegador, sem montar um Blob do arquivo inteiro. Downloads ZIP em fluxo precisam recomeçar se interrompidos.
- Sem limite comercial por arquivo. O limite real depende do espaço livre, sistema de arquivos, navegador e dispositivo. Use NTFS/exFAT para arquivos maiores que 4 GB; FAT32 não suporta esses arquivos.
- A checagem inicial de espaço não reserva disco. Envios concorrentes ou outros programas podem consumir o espaço; nesse caso o envio para com aviso e pode ser retomado após liberar espaço.
- Deixe o navegador do celular aberto e a tela ligada durante envios longos: Android/iOS podem suspender abas em segundo plano. O PC precisa permanecer ligado, sem suspensão.
- A velocidade exibida é uma estimativa por bloco; a velocidade real depende de Wi-Fi, cabo, roteador e disco. Não há garantia de taxa fixa.

## Acesso

O código de seis dígitos muda a cada inicialização. Sessões expiram após 24 horas ou ao reiniciar o servidor. Há limite de tentativas de código. Acesso por localhost entra automaticamente e mostra o código; outros dispositivos precisam informá-lo. Quem tem o código pode acessar os arquivos compartilhados, portanto use apenas sua rede de confiança.

O tráfego usa **HTTP local, sem criptografia de transporte**. O código controla o acesso, mas não substitui HTTPS contra alguém monitorando a rede. Não publique este servidor na internet e não faça encaminhamento de portas. Arquivos recebidos só são servidos como download; a aplicação não executa seu conteúdo. Não há telemetria, fontes remotas ou CDN.

## Opções

```powershell
python server.py --port 8787
python server.py --port 8787 --data-dir "D:\DropAgil"
```

No modo terminal, Ctrl+C encerra a central. No modo bandeja, o sistema inicia ao entrar no Windows. Para instalar dependências depois: `python -m pip install -r requirements.txt`.

## Verificação automatizada

```powershell
python -m unittest discover -s tests -v
node --check public/app.js
node --test tests/test_groups.cjs
```

Os testes usam diretórios temporários e porta aleatória, sem alterar arquivos reais. Cobrem autenticação, proteção de caminhos, streaming, upload interrompido, retomada após recriar o estado do servidor, arquivos vazios, nomes repetidos, ZIP e downloads parciais. O teste de posições acima de 4 GB usa um arquivo simulado para não ocupar o disco; não substitui uma transferência real de vários gigabytes entre seus dispositivos.

A versão 2 acrescenta testes do agrupamento e progresso por bytes, upload de pasta pelo cliente Windows e pareamento Android persistente/revogável. O APK é compilado, sua assinatura é verificada e os filtros de compartilhamento são conferidos no manifesto compilado. O fluxo da Galeria ainda precisa ser conferido no celular físico do usuário.

A versão 3 também valida entrega privada entre três identidades, aceite obrigatório, recusa, isolamento do destinatário, download parcial, limpeza das cópias temporárias e recebimento retomável no Windows. O fluxo de notificações ainda precisa ser testado em Android físico.

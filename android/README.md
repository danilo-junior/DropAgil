# DropAgíl Android

Aplicativo nativo para **Android 10 ou superior**, sem navegador embutido. O APK é `DropAgil-Android.apk` na raiz do projeto. Foi compilado com ferramentas oficiais do Android SDK e assinado para instalação local. Não é uma publicação na Play Store.

## Primeira conexão

1. No computador, abra DropAgíl > Conectar dispositivo para ver o endereço e o código atuais.
2. Instale `DropAgil-Android.apk` no celular. Se o Android solicitar autorização para instalar esse arquivo, faça essa autorização manualmente.
3. Abra o aplicativo, informe o endereço completo (exemplo: `http://192.168.1.146:8787`) e o código. Toque em **Conectar computador**.
4. Se quiser acompanhar o progresso pelas notificações, permita as notificações do aplicativo.

O pareamento é salvo. Não precisa digitar o código a cada envio ou a cada reinício do computador. Se o IP do PC mudar, atualize o endereço e conecte novamente; uma reserva de IP no roteador evita mudanças. O aplicativo só permite configurar endereços locais.

## Galeria → Compartilhar → DropAgíl

Na Galeria, Google Fotos ou app Arquivos:

1. Selecione uma foto, vídeo ou vários arquivos.
2. Toque em **Compartilhar**.
3. Escolha **DropAgíl**. Pode ser necessário abrir a lista completa de aplicativos de compartilhamento na primeira vez.

Com o computador já pareado e notificações permitidas, aparece somente a seleção rápida de destino: **Rede** ou um dispositivo disponível. Depois da escolha, a tela fecha e o envio segue na notificação. Sem pareamento/permissão, a tela de configuração é aberta. Não há uma segunda seleção de arquivos nem é necessário abrir o site. O aplicativo aparece como destino para `ACTION_SEND` e `ACTION_SEND_MULTIPLE`, com qualquer tipo de arquivo (`*/*`).

Fotos armazenadas somente na nuvem podem precisar ser baixadas pelo app da Galeria antes de ele conceder acesso ao DropAgíl. Caso o app de origem não forneça tamanho ou acesso legível, salve o arquivo no aparelho e compartilhe pelo app Arquivos.

## Receber de outro aparelho

Na aba Transferir, toque **Receber arquivos neste celular**. O celular aparece como destino pelo nome do modelo e mantém uma notificação de disponibilidade. O computador central precisa continuar ligado. Ao chegar uma entrega, toque **Aceitar** para baixar ou **Recusar** para apagar a cópia temporária do servidor. Os arquivos são salvos em `Downloads/DropAgil`, cada um em sua subpasta para evitar sobrescritas. O gerenciador de downloads mostra o progresso e a conclusão.

O serviço de recebimento usa o tipo Android `connectedDevice` para comunicação com o computador pela rede local. É ativado pelo usuário e pode ser desativado na notificação. Não reinicia automaticamente após reboot ou fechamento forçado. Restrições de bateria/Doze do fabricante podem atrasar a chegada de pedidos. Se não aparecer, abra o app e reative o recebimento.

## Dentro do app

- **Abrir página**: abre a página local do computador no navegador.
- **Apagar**: remove arquivos/pastas da rede após confirmação.
- **Enviar para**: Rede ou um aparelho com recebimento ativado.
- **Enviar arquivos**: seletor nativo com múltipla seleção.
- **Enviar pasta**: seletor de pastas do Android, preservando a estrutura dos arquivos.
- **Transferências**: uma linha por seleção/pasta, percentual total, bytes, tempo decorrido e estimativa restante.
- **Pausar / Retomar / Cancelar tudo**: controles da fila deste celular. Cancelar preserva arquivos já concluídos no computador.
- **Arquivos da rede**: navegação por pastas e downloads nativos para a pasta Downloads. O gerenciador de downloads do Android acompanha o progresso; pastas são baixadas em ZIP.

O serviço de envio usa blocos de 8 MiB e notificação de progresso. Pode continuar com o app em segundo plano, conforme as regras de bateria e execução do Android/fabricante. A notificação de serviço é controlada pelo Android, não é possível prometer sua ocultação em todos os aparelhos. O botão “Esconder” da versão Windows não tem essa restrição.

Ao pausar, o bloco em andamento pode terminar antes da parada. O Android pode limitar o tempo contínuo de serviços de transferência; o app trata o aviso de tempo limite pausando a fila. Ao reabrir, toque em Retomar. Se o Android revogar a permissão temporária de um arquivo vindo da Galeria, será necessário compartilhá-lo novamente. Arquivos escolhidos pelo seletor do próprio DropAgíl usam permissão persistente quando o provedor permite.

## Compilar

Requer JDK 21 e Python 3.11+, com acesso à internet para obter o SDK uma vez:

```powershell
python android/tools/prepare_sdk.py
python android/tools/build.py
```

As ferramentas são baixadas do repositório oficial do Google e têm checksum conferido. `JAVA_HOME` pode apontar para o JDK. A chave de instalação local permanece em `.dropagil/android-debug.keystore`; conserve essa chave para gerar atualizações instaláveis sobre a versão existente. Ela não é incluída no pacote de código entregue.

## Validação

APK compilado e assinatura verificada. Os filtros de compartilhamento são inspecionados no manifesto compilado. O servidor tem testes de pareamento persistente, uploads em blocos, retomada e integridade. A instalação e o fluxo real da Galeria precisam ser conferidos no aparelho Android do usuário; não foram validados em um telefone físico nesta entrega.

<!-- languages -->
[English](../update-and-remove.md) · [Русский](../ru/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · **Português** · [Deutsch](../de/update-and-remove.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Atualizar e remover

## Atualizar

O SMTV procura uma versão nova uma vez por dia (dá para desligar isso). Quando há uma, ele mostra **Version … is
available** (a versão … está disponível): clique em **Update** (Atualizar).

- O SMTV fecha, se atualiza e abre de novo sozinho, normalmente em menos de um minuto.
- Se um pedido estiver rodando, a atualização espera ele terminar — ou clique em **Stop the jobs and update** (parar
  as tarefas e atualizar); **Continue** (Continuar) retoma as tarefas da mesma etapa depois.
- Se a versão nova não abrir, a anterior volta sozinha.
- As versões novas são assinadas pelos autores do SMTV; o SMTV confere a assinatura antes de instalar.

Tudo sobre atualizações fica em **Settings → Computer check → Updates** (Configurações → Verificação do computador →
Atualizações).

Baixou o SMTV para Windows ou Mac? **Update** (Atualizar) baixa o instalador novo, confere e abre: termine a
instalação por lá (no Mac, arraste o SMTV novo para Aplicativos e clique em **Substituir** (Replace)). A cópia do
Windows que veio do ZIP não se atualiza sozinha: baixe o ZIP novo na [página da versão](https://github.com/streammomenttv/smtv/releases/latest).

Instalou o SMTV de outro jeito? No Docker, uma versão nova é uma imagem nova; veja [para usuários avançados](../../advanced.md#docker).

## Remover

**Settings → Computer check → Remove SMTV from this computer** (remover o SMTV deste computador; o botão **Remove…**)
remove o programa e o ícone do SMTV. Os seus clipes ficam — marque **Also remove clips, jobs, settings and keys**
(remover também clipes, tarefas, configurações e chaves) para removê-los também.

Baixou o SMTV para Windows ou Mac? Remova o programa em si do jeito do sistema (o botão acima remove só os clipes e as
configurações, se você marcar):

- **Windows:** **Configurações → Aplicativos → Aplicativos instalados → SMTV → Desinstalar** (Settings → Apps →
  Installed apps → SMTV → Uninstall). A cópia do ZIP: apague a pasta dela.
- **Mac:** arraste o **SMTV** de **Aplicativos** (Applications) para o **Lixo** (Trash).

Instalou com uma linha no terminal? Sem a janela, em um terminal:

```bash
smtv uninstall
```

Adicione `--data` para remover também os clipes e as configurações. Programas que você mesmo instalou (Ollama, LM
Studio) ficam: remova-os como qualquer outro programa.

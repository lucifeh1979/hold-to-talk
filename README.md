# Hold to Talk

[English](#english) | [Português](#português)

## English

Push-to-talk dictation for any Windows app. Hold a key (or click the floating mic button), speak, release, and the text is pasted where your cursor was.

### Setup

1. Install Python 3.
2. Create an OpenAI API key and put it in the `OPENAI_API_KEY` environment variable.
3. Run `hold-to-talk.bat`. It installs what it needs on the first run.

### Use

Hold **Right Ctrl**, speak, release. A high beep means recording, a middle beep means transcribing, and a low beep means nothing was heard or something failed.

Or click the **green dot** in the corner of the screen, speak, and click it again. It turns red while recording and never steals the focus. Drag it to move it.

- The text goes to the window that was in front when you started, even if you switch windows while it transcribes. Your clipboard is put back afterwards.
- Pressing another key while holding Ctrl (Ctrl+C, Ctrl+V...) cancels: shortcuts keep working.
- Speak as long as you want: long recordings are cut at your pauses so nothing gets summarized or dropped.
- Speaking again before the last text arrived is fine: they come out in order.

Keep the window open while you use it. Closing it turns dictation off.

### Options

Set these as environment variables:

| Variable | Default | Example |
|---|---|---|
| `HOLD_TO_TALK_KEY` | `right ctrl` | `f9` |
| `HOLD_TO_TALK_LANG` | automatic | `en`, `pt` |
| `HOLD_TO_TALK_WORDS` | none | `key, commit, deploy, GitHub` |
| `HOLD_TO_TALK_SEND_KEY` | none | `left ctrl` |
| `HOLD_TO_TALK_BUTTON` | `1` | `0` turns the button off |

`HOLD_TO_TALK_WORDS` lists words it tends to get wrong, such as English terms in the middle of Portuguese speech. If a transcription comes back empty or too short, it tries again without the list.

`HOLD_TO_TALK_SEND_KEY` is a second key that pastes **and presses Enter** in a terminal (handy with Claude Code or Codex). The main key only pastes, so you can fix the text before sending.

If the key is missing or refused, the window says what to do and dictation does not start.

### Good to know

- Windows only.
- Audio goes to the OpenAI transcription API (`gpt-4o-transcribe`), at about US$ 0.006 per minute, billed to your key.
- At startup it tests each microphone and uses the one with the strongest signal. Keep some sound in the room if it picks the wrong one.
- To type into a program running as administrator, run this as administrator too.
- If the internet drops, it gives up after about 25 seconds instead of freezing the next dictations.

## Português

Ditado por voz em qualquer programa do Windows. Segura uma tecla (ou clica no botão de microfone), fala, solta, e o texto é colado onde estava o cursor.

### Instalação

1. Instale o Python 3.
2. Crie uma chave da API da OpenAI e coloque na variável de ambiente `OPENAI_API_KEY`.
3. Rode o `hold-to-talk.bat`. Ele instala o que precisa na primeira vez.

### Como usar

Segure o **Ctrl direito**, fale e solte. Bipe agudo é gravando, bipe médio é transcrevendo, e bipe grave quer dizer que não ouviu nada ou que algo falhou.

Ou clique na **bolinha verde** no canto da tela, fale e clique de novo. Ela fica vermelha enquanto grava e nunca rouba o foco. Arraste pra mudar de lugar.

- O texto vai pra janela que estava na frente quando você começou, mesmo se trocar de janela enquanto transcreve. O que estava copiado volta depois.
- Apertar outra tecla segurando o Ctrl (Ctrl+C, Ctrl+V...) cancela: os atalhos continuam funcionando.
- Fale o tempo que quiser: fala longa é cortada nas suas pausas, pra nada sair resumido ou cortado.
- Falar de novo antes do texto anterior chegar não mistura: sai na ordem.

Deixe a janela aberta enquanto usa. Fechar a janela desliga o ditado.

### Opções

Defina como variáveis de ambiente:

| Variável | Padrão | Exemplo |
|---|---|---|
| `HOLD_TO_TALK_KEY` | `right ctrl` | `f9` |
| `HOLD_TO_TALK_LANG` | automático | `pt`, `en` |
| `HOLD_TO_TALK_WORDS` | nenhuma | `key, commit, deploy, GitHub` |
| `HOLD_TO_TALK_SEND_KEY` | nenhuma | `left ctrl` |
| `HOLD_TO_TALK_BUTTON` | `1` | `0` desliga o botão |

`HOLD_TO_TALK_WORDS` lista palavras que ele costuma errar, como termos em inglês no meio da fala em português. Se a transcrição vier vazia ou curta demais, ele tenta de novo sem a lista.

`HOLD_TO_TALK_SEND_KEY` é uma segunda tecla que cola **e dá Enter** no terminal (bom com Claude Code ou Codex). A tecla principal só cola, pra você corrigir antes de mandar.

Se a chave faltar ou for recusada, a janela explica o que fazer e o ditado não começa.

### Bom saber

- Só para Windows.
- O áudio vai para a API de transcrição da OpenAI (`gpt-4o-transcribe`), a cerca de US$ 0,006 por minuto, cobrado na sua chave.
- Ao abrir, ele testa cada microfone e usa o de sinal mais forte. Se escolher o errado, deixe algum som no ambiente ao abrir.
- Para digitar em programa aberto como administrador, rode este também como administrador.
- Se a internet cair, ele desiste em uns 25 segundos em vez de travar os próximos ditados.

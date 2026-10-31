# Hold to Talk

[English](#english) | [Português](#português)

## English

Push-to-talk dictation for any Windows app. Hold a key, speak, release, and the text is typed where your cursor is.

### Setup

1. Install Python 3.
2. Create an OpenAI API key and put it in the `OPENAI_API_KEY` environment variable.
3. Run `hold-to-talk.bat`. It installs what it needs on the first run.

### Use

Hold **Right Ctrl**, speak, release. A high beep means recording, a middle beep means transcribing, and a low beep means nothing was heard or something failed. The text also stays in your clipboard.

Keep the window open while you use it. Closing it turns dictation off.

### Options

Set these as environment variables:

| Variable | Default | Example |
|---|---|---|
| `HOLD_TO_TALK_KEY` | `right ctrl` | `f9` |
| `HOLD_TO_TALK_LANG` | automatic | `en`, `pt` |
| `HOLD_TO_TALK_WORDS` | none | `key, commit, deploy, GitHub` |

`HOLD_TO_TALK_WORDS` lists words it tends to get wrong, such as English terms in the middle of Portuguese speech.

If the key is missing or refused, the window says what to do and dictation does not start.

### Good to know

- Windows only.
- Audio goes to the OpenAI transcription API (`gpt-4o-transcribe`), at about US$ 0.006 per minute, billed to your key.
- At startup it tests each microphone and uses the one with the strongest signal. Keep some sound in the room if it picks the wrong one.
- To type into a program running as administrator, run this as administrator too.

## Português

Ditado por voz em qualquer programa do Windows. Segura uma tecla, fala, solta, e o texto é digitado onde estiver o cursor.

### Instalação

1. Instale o Python 3.
2. Crie uma chave da API da OpenAI e coloque na variável de ambiente `OPENAI_API_KEY`.
3. Rode o `hold-to-talk.bat`. Ele instala o que precisa na primeira vez.

### Como usar

Segure o **Ctrl direito**, fale e solte. Bipe agudo é gravando, bipe médio é transcrevendo, e bipe grave quer dizer que não ouviu nada ou que algo falhou. O texto também fica copiado.

Deixe a janela aberta enquanto usa. Fechar a janela desliga o ditado.

### Opções

Defina como variáveis de ambiente:

| Variável | Padrão | Exemplo |
|---|---|---|
| `HOLD_TO_TALK_KEY` | `right ctrl` | `f9` |
| `HOLD_TO_TALK_LANG` | automático | `pt`, `en` |
| `HOLD_TO_TALK_WORDS` | nenhuma | `key, commit, deploy, GitHub` |

`HOLD_TO_TALK_WORDS` lista palavras que ele costuma errar, como termos em inglês no meio da fala em português.

Se a chave faltar ou for recusada, a janela explica o que fazer e o ditado não começa.

### Bom saber

- Só para Windows.
- O áudio vai para a API de transcrição da OpenAI (`gpt-4o-transcribe`), a cerca de US$ 0,006 por minuto, cobrado na sua chave.
- Ao abrir, ele testa cada microfone e usa o de sinal mais forte. Se escolher o errado, deixe algum som no ambiente ao abrir.
- Para digitar em programa aberto como administrador, rode este também como administrador.

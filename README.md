# Radial ZBrush

Menu radial para o ZBrush, feito como projeto de estudo e inspirado no RadialZ. Você aperta um atalho, o menu abre no cursor, e você escolhe um brush ou um comando.

Funciona no **ZBrush 2023/2024**, com a ponte em ZScript, e no **ZBrush 2026**, com a ponte em Python.

## Como funciona

São duas partes:

1. **App externo** (`radial/`, Python + PySide6): escuta os atalhos, desenha o menu e decide o que foi escolhido.
2. **Ponte no ZBrush**: executa o comando dentro do ZBrush.
   - ZBrush 2023/2024: `zbrush_bridge/zscript/RadialBridge.txt` (ZScript), com `"protocol": "zscript"` no config.
   - ZBrush 2026: `zbrush_bridge/radial_bridge.py` (Python), com `"protocol": "python"` no config.

O ZBrush não tem um jeito de "escutar" comandos em segundo plano. Por isso a ponte é um **botão** (`ZPlugin > Radial Bridge > Run`) com um atalho. O app grava o comando em `zbrush_bridge/data/` e aperta esse atalho. O botão lê o comando, executa e apaga o arquivo.

```
Alt+Q -> menu no cursor -> escolha -> data/command.txt -> Ctrl+Alt+Shift+J -> botão Run -> brush troca
```

## Tipos de ação dos slots

| `type` | Campo | O que faz |
| --- | --- | --- |
| `press` | `item` | Aperta um item da interface do ZBrush pelo item path (ex.: `Brush:Move`) |
| `brush_file` | `path` | Carrega um brush de um arquivo `.ZBP` |
| `keys` | `keys` | Só aperta teclas: atalhos nativos do ZBrush (ex.: `x`, `<shift>+f`, `b s t`) |

`keys` não usa a ponte, então funciona mesmo antes de a ponte estar pronta.

Limites da ponte ZScript: o comando precisa ter no máximo 250 caracteres e só pode usar caracteres ASCII (sem acentos) no caminho ou no item path. O app recusa o comando e avisa no console se passar disso.

## Instalação

Requisitos: Windows e Python 3.11 ou mais novo.

```bat
cd J:\CODING\radial-zbrush
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Passo a passo (ZBrush 2024)

### 1. Carregar a ponte

1. Abra `zbrush_bridge/zscript/RadialBridge.txt` e confira a linha `rbDir`. Ela precisa apontar para a pasta `zbrush_bridge/data/` do projeto, com barras normais e `/` no final. O valor padrão já é `J:/CODING/radial-zbrush/zbrush_bridge/data/`.
2. No ZBrush: `ZScript > Load` e escolha `RadialBridge.txt`. O ZBrush compila o arquivo e cria `RadialBridge.zsc` ao lado.
3. Abra `ZPlugin > Radial Bridge`.

Se o ZBrush mostrar um erro de sintaxe ao carregar, copie a mensagem: ela diz a linha.

### 2. Fase 0: testar dentro do ZBrush

Os botões de teste ficam em `ZPlugin > Radial Bridge`:

- **Check**: diz se o botão de carregar brush (`Brush:Load Brush`) existe. Se não existir, descubra o nome certo e mude `rbLoadItem` no `RadialBridge.txt`.
- **Test Press**: pede um item path (ex.: `Brush:Move`) e aperta. Use para confirmar os nomes dos brushes do `config/menus.json`.
- **Test Load**: pede o caminho de um `.ZBP` e carrega.

O item path é `Paleta:Nome do botão`, com o nome como aparece na interface (ex.: `Brush:Move`). Se um nome não funcionar no Test Press, tente variações sem espaços.

### 3. Atribuir o atalho do botão Run

1. Faça **Ctrl+Alt+clique** no botão **Run** e aperte **Ctrl+Alt+Shift+J**. Esse é o `trigger_hotkey` do config.
2. Salve em `Preferences > Hotkeys > Store`.

Se o ZBrush não aceitar essa combinação, use outra e troque também o `trigger_hotkey` em `config/menus.json`.

### 4. Rodar o app

```bat
run.bat
```

Ou `python -m radial`. Um ícone aparece na bandeja do Windows, com as opções **Recarregar config** e **Sair**.

Com o ZBrush em foco:

- **Alt+Q** abre o menu Sculpt e **Alt+W** abre o menu Tools.
- **Modo hold** (padrão): segure o atalho, aponte e solte.
- Um **toque rápido** deixa o menu aberto; aí é só clicar.
- **Flick**: arraste o mouse para além do anel na direção do slot.
- **Esc** ou **botão direito** fecha o menu.

### 5. Carregar a ponte sempre que abrir o ZBrush

Copie o `RadialBridge.zsc` gerado para a pasta `ZStartup\ZPlugs64` dentro da instalação do ZBrush 2024 (em `C:\Program Files\Maxon ZBrush 2024\`). Plugins nessa pasta carregam ao abrir o ZBrush. Se você mudar o `.txt`, carregue de novo e copie o `.zsc` novo.

## ZBrush 2026 (ponte em Python)

No `config/menus.json`, use `"protocol": "python"`. No ZBrush, carregue `zbrush_bridge/radial_bridge.py` em `ZScript > Python Scripting > Load`. Os scripts de teste ficam em `zbrush_bridge/phase0/`. O `start_zbrush_with_bridge.bat` abre o 2026 já carregando a ponte. Nada disso roda no 2023 nem no 2024.

## Configuração (`config/menus.json`)

- `bridge.protocol`: `zscript` (2023/2024) ou `python` (2026).
- `bridge.trigger_hotkey`: o atalho do botão Run.
- `bridge.command_dir`: pasta do comando. Relativa à raiz do projeto. Na ponte ZScript, tem que bater com `rbDir`.
- `menus[].hotkey`: formato do pynput, por exemplo `<alt>+q` ou `<ctrl>+<shift>+e`. Escolha combinações que o ZBrush não usa: o app não bloqueia a tecla, então o ZBrush também a recebe.
- `selection.mode`: `hold` ou `toggle`.
- `selection.hover_dwell_ms`: seleciona ao parar o mouse sobre o slot (0 = desligado).
- `slots[].icon`: caminho de um PNG (opcional). Sem ícone, o slot mostra o texto.
- `slots[].color`: cor do slot (opcional).

Depois de editar, use **Recarregar config** na bandeja.

### Biblioteca de brushes

```bat
python -m radial.library "C:\pasta\dos\brushes" --slots
python -m radial.library "C:\pasta\dos\brushes" --find clay --slots
```

Grava `config/library.json` e imprime os brushes no formato de slot, prontos para colar no `menus.json`.

## Testes

```bat
pip install pytest
python -m pytest
```

Os testes cobrem a lógica sem precisar do ZBrush nem de teclado: geometria do menu, validação do config, combinação de atalhos, o formato do comando das duas pontes, os colchetes do `RadialBridge.txt` e a varredura de brushes.

## O que ainda não foi verificado

Este código foi escrito sem acesso a um ZBrush ou a uma tela Windows. O ZScript foi escrito a partir da referência oficial de comandos, mas nunca foi compilado. Confira:

| Ponto | Como conferir | Onde ajustar |
| --- | --- | --- |
| O `RadialBridge.txt` compila | `ZScript > Load` | `RadialBridge.txt` |
| O nome do botão de carregar brush (`Brush:Load Brush`) | Botão **Check** | `rbLoadItem` no `RadialBridge.txt` |
| Os item paths dos brushes (`Brush:ClayBuildup` etc.) | Botão **Test Press** | `config/menus.json` |
| O ZBrush aceita Ctrl+Alt+Shift+J como atalho | Passo 3 | `trigger_hotkey` + atalho do Run |
| O menu não rouba o foco do ZBrush | Usar o app | `radial/overlay.py` |
| Os atalhos nativos do menu Tools | Usar o app | `config/menus.json` |

## Estrutura

```
radial/                       app externo
  app.py                      liga tudo + bandeja do sistema
  overlay.py                  janela e desenho do menu
  geometry.py                 ângulos, hit test, flick
  hotkeys.py                  atalhos globais e envio de teclas
  bridge_client.py            grava o comando e dispara a ponte
  config.py                   leitura e validação do JSON
  library.py                  varredura de brushes .ZBP
zbrush_bridge/
  zscript/RadialBridge.txt    ponte para ZBrush 2023/2024
  radial_bridge.py            ponte para ZBrush 2026
  phase0/                     testes da API Python (só 2026)
  data/                       onde o comando é gravado
config/menus.json             menus de exemplo
tests/                        testes automatizados
```

## Próximos passos (do planejamento)

- Fase 3: tela para editar menus sem mexer no JSON.
- Fase 4: popup de biblioteca com busca e arrastar para o slot.
- Fase 5: child slots, tags, controles de aparência ao vivo, alphas, texturas e materiais.

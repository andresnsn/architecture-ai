# Comparação exploratória de arquitetura

Uma mesma pergunta foi aplicada aos repositórios locais `orders-api`, `inventory-service` e `catalog-service`, usando Qwen3:8b via Ollama e as versões v1, v2 e v3 dos prompts. Os arquivos estão em `docs/generated/v1`, `v2` e `v3`. Relações originalmente marcadas como confirmadas foram exibidas como inferidas no desenho porque as configurações efetivas podem variar; o JSON conserva também a resposta original.

| Versão | Tempo observado | Componentes | Relações propostas | Avisos de citação |
| --- | ---: | ---: | ---: | ---: |
| v1 | 137,5 s | 3 | 2 | 4 |
| v2 | 207,1 s | 3 | 3 | 0 |
| v3 | 137,3 s | 3 | 2 | 0 |

A v1 citou quatro locais fora das evidências fornecidas ao modelo; isso não prova que os arquivos ou linhas sejam inexistentes. A v2 propôs uma relação adicional do inventário consigo mesmo sem sustentação suficiente: citações literais verificáveis não provam que uma relação seja verdadeira. A v3 identificou as duas relações do cenário. Esta é apenas uma execução exploratória, não o placar da bateria de 16 casos e não demonstra superioridade estatística.

Os desenhos são gerados a partir da resposta e do auditor de citações, sem validar semanticamente se a evidência prova a relação. Ausência de erro de citação não garante correção e é necessária revisão humana.

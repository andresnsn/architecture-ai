# architecture-ai

MVP de análise arquitetural de repositórios: extração estática, recuperação lexical e geração com modelo local.

## Extração estática

```sh
python3 -m architecture_ai extract ~/orders-api ~/inventory-service ~/catalog-service --output architecture.json
```

O comando reconhece rotas `net/http`, configurações usuais de produtor/consumidor `kafka-go` e chamadas REST feitas pelo cliente HTTP do Go. Cada fato inclui arquivo, linha e trecho. As rotas e configurações vistas diretamente são `confirmed`; associação de uma chamada REST a outro repositório é `inferred`.

O extrator é deliberadamente limitado aos padrões usados no cenário de demonstração. Um padrão ausente fica desconhecido, em vez de ser adivinhado. SQLite FTS5 fornece busca lexical, não vetorial, para recuperar trechos que são enviados ao LLM.

Para indexar trechos de código e configuração e pesquisar evidências com arquivo e linhas:

```sh
python3 -m architecture_ai index ~/orders-api ~/inventory-service ~/catalog-service
python3 -m architecture_ai search "orders.created.v1"
python3 -m architecture_ai report ~/orders-api ~/inventory-service ~/catalog-service
```

O índice fica em `.architecture/evidence.sqlite`, ignorado pelo Git. Arquivos `.env`, dependências vendorizadas e arquivos grandes não entram no índice. Cada resultado informa repositório, arquivo e intervalo de linhas.

O subcomando `report` grava `architecture.json`, `architecture.md` e `architecture.mmd` em `docs/generated/`. A associação de produtor e consumidor pelo mesmo tópico é inferida a partir da configuração observada; uma chamada REST associada a um repositório por variável de configuração é marcada como inferida. O diagrama usa linha tracejada para relações inferidas.

## Geração local com Ollama

O MVP usa por padrão `qwen3:8b` em Ollama local. O modelo roda no próprio computador e a aplicação chama `http://localhost:11434`; não é usada uma chave nem uma API paga. Depois de iniciar o Ollama, indexar os repositórios e gerar os relatórios estáticos:

```sh
python3 -m architecture_ai analyze "Como os serviços se comunicam?" ~/orders-api ~/inventory-service ~/catalog-service --prompt v3
```

O resultado vai para `docs/generated/llm-analysis.json`, com evidências e avisos de citação. Ajuste o modelo com `OLLAMA_MODEL` se instalar outro. Para uma comparação paga com OpenAI seria necessário configurar uma integração separada; ela não é chamada por este fluxo.

Os avisos verificam correspondência de arquivo, linha e trecho, não comprovam que a evidência sustenta a conclusão. Confira também o diagrama, os fatos e os possíveis segredos antes de compartilhar os resultados. O modelo pode cometer erros e o extrator cobre apenas alguns padrões Go. A avaliação comparativa dos prompts ainda está pendente.

## Kafka local

O arquivo `compose.yaml` inicia uma instância local do Apache Kafka 4.4.0 em KRaft. A porta do host é `29092` para evitar conflito com outros serviços Kafka que já estejam usando `9092`.

```sh
docker compose up -d
```

Para rodar os serviços Go no host, configure `KAFKA_BROKERS=localhost:29092`. O inventário também usa `CATALOG_BASE_URL=http://localhost:8081`. As aplicações podem ser iniciadas em terminais separados com `go run ./cmd/...` no respectivo repositório.

## Requisitos

- Python 3.9 ou superior (usa apenas a biblioteca padrão no MVP atual).


## Chat no terminal com repositórios

No terminal, entre na pasta `~/dev/code/architecture-ai` e execute:

```sh
python3 -m architecture_ai chat
```

Informe uma URL HTTPS GitHub/GitLab ou pasta local por linha e pressione Enter em branco para iniciar. O programa clona URLs com Git, prepara um índice próprio e cria o desenho `docs/generated/architecture.svg`, legível no navegador; `architecture.mmd` contém o mesmo panorama em Mermaid. Faça uma pergunta ou pressione Enter para a visão geral. Digite `sair` para terminar. Para URLs privadas, configure antes o acesso Git no computador; não inclua credenciais na URL. A busca e o Ollama são locais, enquanto o clone por HTTPS usa a rede. O programa guarda clones e índice em `.architecture/sessions/` para conservar as referências e envia ao modelo local trechos recuperados e achados estáticos.

O desenho é gerado pela análise estática, com todos os repositórios e destinos desconhecidos quando reconhecidos. Ele não representa todas as relações que o LLM possa descobrir. A resposta do modelo e suas citações ficam em `docs/generated/llm-analysis.json`; cada pergunta substitui esse arquivo. O histórico usado é um resumo limitado das duas respostas anteriores, não uma transcrição completa. A identificação estática cobre somente alguns padrões Go e não prova ausência de conexão. As associações por configuração e tópico precisam de revisão; configurações reais de execução podem mudar.

É possível passar fontes no comando:

```sh
python3 -m architecture_ai chat ~/dev/code/orders-api ~/dev/code/inventory-service ~/dev/code/catalog-service
```

Para instalar e preparar o modelo local, consulte https://ollama.com e baixe `qwen3:8b` com `ollama pull qwen3:8b`. Abra o Ollama antes de iniciar o chat.

## Análise de várias tecnologias e visão no navegador

O extrator reconhece alguns padrões Go, rotas com anotações Spring, rotas simples em Node/Express e Python (Flask/FastAPI) e declarações de recursos Terraform. Uma rota obtida por anotação é apenas um fragmento observado: prefixos configurados em outro local podem alterar seu caminho final. Padrões não reconhecidos continuam disponíveis ao modelo por meio do RAG, desde que o arquivo tenha sido indexado e o trecho tenha sido recuperado. Isso não garante cobertura de todas as linguagens, frameworks ou arquivos de um projeto.

Além dos blocos de linhas, o índice preserva funções Python completas quando possível. A busca mistura palavras da pergunta e termos de arquitetura, priorizando diversidade entre repositórios; ainda é busca lexical, não semântica. O modelo recebe os trechos e as descobertas estáticas. Suas respostas são classificadas por uma chamada ao Ollama antes da análise: perguntas fora do escopo recebem orientação e perguntas ambíguas pedem esclarecimento. O classificador pode cometer erros.

Após uma resposta do modelo, o arquivo `docs/generated/arquitetura.html` mostra todos os repositórios analisados e relações com citações que correspondem às evidências fornecidas. Digite `/abrir` no chat para abrir esse arquivo no navegador. Uma citação literal válida não prova que ela sustenta a conclusão; revise os achados. O SVG e o Mermaid continuam sendo um relatório separado, gerado apenas pelos extratores estáticos. O chat regrava os arquivos a cada resposta. Instruções encontradas no código são dados não confiáveis, não comandos; a resistência a injeções e o vazamento ainda precisam ser avaliados.

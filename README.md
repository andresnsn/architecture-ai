# architecture-ai

MVP de análise arquitetural de repositórios. A primeira etapa extrai fatos de código Go e configurações com evidências locais; os resultados ainda não usam LLM.

## Extração estática

```sh
python3 -m architecture_ai extract ~/orders-api ~/inventory-service ~/catalog-service --output architecture.json
```

O comando reconhece rotas `net/http`, configurações usuais de produtor/consumidor `kafka-go` e chamadas REST feitas pelo cliente HTTP do Go. Cada fato inclui arquivo, linha e trecho. As rotas e configurações vistas diretamente são `confirmed`; associação de uma chamada REST a outro repositório é `inferred`.

O extrator é deliberadamente limitado aos padrões usados no cenário de demonstração. Um padrão ausente fica desconhecido, em vez de ser adivinhado. SQLite FTS5 será usado numa próxima etapa para busca local de evidências, sem serviço externo.

## Requisitos

- Python 3.9 ou superior (usa apenas a biblioteca padrão nesta etapa).


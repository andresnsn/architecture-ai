# architecture-ai

MVP de análise arquitetural de repositórios. A primeira etapa extrai fatos de código Go e configurações com evidências locais; os resultados ainda não usam LLM.

## Extração estática

```sh
python3 -m architecture_ai extract ~/orders-api ~/inventory-service ~/catalog-service --output architecture.json
```

O comando reconhece rotas `net/http`, configurações usuais de produtor/consumidor `kafka-go` e chamadas REST feitas pelo cliente HTTP do Go. Cada fato inclui arquivo, linha e trecho. As rotas e configurações vistas diretamente são `confirmed`; associação de uma chamada REST a outro repositório é `inferred`.

O extrator é deliberadamente limitado aos padrões usados no cenário de demonstração. Um padrão ausente fica desconhecido, em vez de ser adivinhado. SQLite FTS5 será usado numa próxima etapa para busca local de evidências, sem serviço externo.

## Kafka local

O arquivo `compose.yaml` inicia uma instância local do Apache Kafka 4.4.0 em KRaft. A porta do host é `29092` para evitar conflito com outros serviços Kafka que já estejam usando `9092`.

```sh
docker compose up -d
```

Para rodar os serviços Go no host, configure `KAFKA_BROKERS=localhost:29092`. O inventário também usa `CATALOG_BASE_URL=http://localhost:8081`. As aplicações podem ser iniciadas em terminais separados com `go run ./cmd/...` no respectivo repositório.

## Requisitos

- Python 3.9 ou superior (usa apenas a biblioteca padrão nesta etapa).


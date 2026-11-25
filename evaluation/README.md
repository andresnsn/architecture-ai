# Avaliação dos prompts

`cases.json` contém 16 cenários sintéticos criados para este projeto, cada um com uma pergunta, evidências fornecidas e critérios esperados. A disciplina exige pelo menos 15 casos; ela não fornece estes 16. Incluem testes arquiteturais, injeção direta e indireta, vazamento, privacidade e viés. Nenhum segredo válido ou dado pessoal real é usado.

## Executar

Com o Ollama aberto e `qwen3:8b` instalado, a partir da raiz do projeto:

```sh
python3 evaluation/run.py --resume
python3 evaluation/summarize.py
```

O primeiro comando executa os mesmos casos com v1, v2 e v3 e grava cada resposta real em `evaluation/results/`. `--resume` preserva respostas já gravadas; use um diretório novo ao alterar casos, prompts ou modelo. O segundo conta respostas existentes, JSON válido, estrutura básica e sinalizações literais de vazamento. Esses números não são pontuação de qualidade ou prova de segurança.

Cada caso exige revisão do conteúdo, certeza e evidências contra seus critérios. Registre falhas individuais, especialmente falhas críticas de segurança, e compare as versões sem alterar respostas originais. Um conjunto separado de casos não usados no ajuste deve ser criado para verificar generalização.

As evidências sintéticas são enviadas diretamente ao modelo, mantendo entradas iguais para as três versões: isso testa prompts e modelo sob instrução e esquema comuns, **não** o pipeline inteiro de clonagem, indexação, recuperação ou classificador de escopo. Por exemplo, o caso 13 fornece uma credencial fictícia ao modelo para testar vazamento; a exclusão de `.env` do índice é uma verificação separada de código. Os testes locais em `tests/` cobrem algumas dessas partes, sem comprovar segurança de produção.

A correspondência de tópico, sem evidência de ambiente e execução, é tratada como relação inferida. O gabarito dos casos 02, 03, 04, 05, 06, 09 e 10 foi revisto para esclarecer evidências e limites antes da bateria. As versões e os casos utilizados devem ser congelados junto aos resultados.

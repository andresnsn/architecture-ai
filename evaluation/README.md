# Evaluation fixtures

`cases.json` contains synthetic scenarios and expected findings for comparing prompts v1, v2, and v3. It contains no valid API keys or real personal data.

The 16 cases cover REST, Kafka, exact topic matching, inferred/unknown relationships, absent gRPC/RabbitMQ evidence, prompt injection in user input and repository content, secret minimization, LGPD data minimization, bias, and unsupported deployment claims.

The next evaluation runner will score each model response for:

- Relationship precision, recall, and F1 against the expected relationships.
- Certainty-label accuracy and citation coverage.
- JSON/diagram validity for structured prompts.
- Hallucinated claims and prohibited-string leakage.
- Injection resistance and data minimization on the security fixtures.

No score is claimed until each version has been run against the same cases with the selected model and the results have been saved.

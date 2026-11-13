# Source ingestion extension 1.0.0

The existing Planner integration package, RPC wire version `1.0.1`, logical schema
`1.1`, ten domain tools and eighteen legacy internal interfaces are unchanged.
BE-04 is an additive, separately versioned extension, registered under
`extensions.ingestion` in service/data contracts and `x-ingestion-contract` in
the main OpenAPI. Its three new HTTP paths live in
[ingestion-openapi.yaml](ingestion-openapi.yaml). Schema definitions and fixtures
share the existing bundle and generated schema checker.

`UserMessage.source_ids` and `RecordSourceMessageArguments.source_ids` are optional
unique UUID arrays, maximum five. Old clients omit them. A source must be READY
and match both JWT owner and conversation. Source intents cannot approve or
generate a plan; they enter the existing explicit confirmation queue. Lineage is
stored atomically with the source message. The frontend attachment UI is still
disabled pending its own end-to-end integration.

See [the implementation boundary](../docs/features/planner/ingestion.md) for
supported formats, upload/extraction limits, error behavior and provider settings.

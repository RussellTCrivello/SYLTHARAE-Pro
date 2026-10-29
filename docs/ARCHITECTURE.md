# Architecture

How the application is put together, in the order a request travels. The
diagrams are checked against the code they depict - the job state machine below
is compared with `services.jobs.job_state.TRANSITIONS` on every run, so a state
that the code gains or loses without the diagram following fails the suite.

## Request path

```mermaid
flowchart TD
    Browser --> Flask[Flask app: apps/web/app.py]
    Flask --> Auth[Authentication and authorisation middleware]
    Auth --> Blueprint[API and page blueprints]
    Blueprint --> Service[Service layer: Api/services, services]
    Service --> Reader[Readers: reader_file/readers]
    Service --> OCR[OCR engines: core/ocr]
    Service --> Pipeline[Storage pipeline: pipeline]
    Pipeline --> DB[(PostgreSQL)]
    Reader --> Storage[(File storage)]
    OCR --> Pipeline
```

## A read, end to end

```mermaid
sequenceDiagram
    participant U as User
    participant R as Route
    participant P as StoragePipeline
    participant D as Reader
    participant O as OCR engine
    participant DB as PostgreSQL
    U->>R: request a file's text
    R->>P: extract(file)
    P->>D: read the container
    D-->>P: text, metadata, extraction_provenance
    P->>O: OCR only when no text layer was found
    O-->>P: text, confidence, engine version
    P->>DB: store the occurrence and its provenance
    P-->>R: stored record
    R-->>U: rendered page
```

## Job lifecycle

Every long operation is a job with a state, and the states are a closed set: a
job that leaves `QUEUED` reaches exactly one of the terminal states, and every
terminal state releases its lock and its workers.

```mermaid
stateDiagram-v2
    [*] --> QUEUED
    QUEUED --> CANCELLED
    QUEUED --> CANCELLING
    QUEUED --> FAILED
    QUEUED --> RUNNING
    RUNNING --> CANCELLED
    RUNNING --> CANCELLING
    RUNNING --> COMPLETED
    RUNNING --> COMPLETED_WITH_WARNINGS
    RUNNING --> FAILED
    RUNNING --> PAUSED
    PAUSED --> CANCELLED
    PAUSED --> CANCELLING
    PAUSED --> RUNNING
    CANCELLING --> CANCELLED
    CANCELLING --> FAILED
    CANCELLED --> [*]
    COMPLETED --> [*]
    COMPLETED_WITH_WARNINGS --> [*]
    FAILED --> [*]
```

## Layers, and what may not cross them

| layer | may import | may not |
|---|---|---|
| templates | nothing (rendered by Flask) | read the database, decide access |
| routes (`Api/routes`, blueprints) | services | import a reader directly |
| services | readers, pipeline, database | render markup |
| readers | their own libraries | write to the database |
| core | the standard library and its own subpackages | import a route or a service |

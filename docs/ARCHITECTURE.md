# MorsePi Architecture

This document shows the current project and AWS architecture. Solid lines are
implemented paths. Dashed lines are disabled or future options.

## Project Architecture

```mermaid
flowchart TB
    Student["Student"]
    Adult["Adult operator"]

    subgraph Station["MorsePi station - Raspberry Pi 4"]
        Touch["7-inch touch display<br/>Chromium kiosk"]
        Web["Flask application<br/>single request worker"]
        Learning["Learning and curriculum<br/>Daily, Learn, Send, Read,<br/>Listen, Echo, Words, Sprint"]
        Messages["Family messages<br/>compose, review, decode"]
        Data["Local student data<br/>JSON and JSONL files"]
        Services["systemd services and timers<br/>app, kiosk, backup, status,<br/>update, message sync"]
        Recovery["PIN-gated System screen<br/>Wi-Fi, keyboard, desktop, update"]
        Keyer["Telegraph key<br/>GPIO17"]
        LED["Status LED<br/>GPIO27"]
        Speaker["USB speaker"]

        Touch --> Web
        Web --> Learning
        Web --> Messages
        Learning <--> Data
        Messages <--> Data
        Keyer --> Web
        Web --> LED
        Web --> Speaker
        Services --> Web
        Services --> Data
        Recovery --> Services
    end

    Student --> Touch
    Student --> Keyer
    Adult --> Recovery

    GitHub["GitHub<br/>main and release/pi"]
    AWS["AWS<br/>backup, status, summaries,<br/>durable message routing"]

    GitHub -->|"PIN-gated update"| Services
    Services -->|"narrow station identity"| AWS
    AWS -->|"ten-minute sync<br/>on two test stations"| Services
```

There are three stations using the same application and release:

| Station ID | Local students | Special role |
|---|---|---|
| `pappy-test-station` | Pappy and all four grandkids | Family practice and test station |
| `astrid-liara-station` | Astrid and Liara | Grandkid home station |
| `campbell-olivea-station` | Campbell and Olivea | Grandkid home station |

Student progress belongs to the student, not the physical station. Each Pi has
its own configuration, local roster, admin PIN, data directory, and narrow AWS
credential. Guest is disposable and cannot send or receive family messages.

## AWS Architecture

```mermaid
flowchart LR
    Admin["Pappy's laptop<br/>temporary setup administration"]
    GitHub["GitHub<br/>release/pi"]

    subgraph Devices["Family stations"]
        Pappy["Pappy station<br/>station IAM identity"]
        AL["Astrid and Liara station<br/>station IAM identity"]
        CO["Campbell and Olivea station<br/>station IAM identity"]
    end

    subgraph AWS["AWS account - us-east-1"]
        subgraph Bucket["Private versioned S3 bucket"]
            PPrefix["stations/pappy-test-station/<br/>backups, status, snapshots, messages"]
            ALPrefix["stations/astrid-liara-station/<br/>backups, status, snapshots, messages"]
            COPrefix["stations/campbell-olivea-station/<br/>backups, status, snapshots, messages"]
            Family["family/<br/>directory and sanitized<br/>student summaries"]
        end

        Lambda["Lambda<br/>morsepi-message-router"]
        RouterRole["Narrow Lambda IAM role"]
        Logs["CloudWatch Logs"]
        IoT["AWS IoT Core<br/>optional future arrival notices<br/>and remote commands"]
        SSM["Systems Manager<br/>optional future remote support"]
    end

    Pappy -->|"read/write own prefix"| PPrefix
    AL -->|"read/write own prefix"| ALPrefix
    CO -->|"read/write own prefix"| COPrefix
    Pappy -->|"read sanitized data"| Family
    AL -->|"read sanitized data"| Family
    CO -->|"read sanitized data"| Family

    PPrefix -->|"S3 object-created event"| Lambda
    ALPrefix -->|"S3 object-created event"| Lambda
    COPrefix -->|"S3 object-created event"| Lambda
    RouterRole --> Lambda
    Lambda -->|"validate and route"| PPrefix
    Lambda -->|"validate and route"| ALPrefix
    Lambda -->|"validate and route"| COPrefix
    Lambda -->|"publish minimal summaries"| Family
    Lambda --> Logs

    GitHub -->|"adult-triggered station update"| Devices
    Admin -->|"setup and maintenance only"| AWS
    IoT -.-> Devices
    SSM -.-> Devices
```

## Security Boundaries

- Each station can access only its own S3 prefix plus sanitized `family/` data.
- Stations cannot read another station's raw backups or create AWS resources.
- S3 invokes Lambda using a bucket- and account-scoped permission.
- Lambda independently validates station, sender, receiver, message limits,
  learned letters, and object paths before routing.
- The bucket blocks public access, uses encryption, and retains versions.
- Broad AWS administration is temporary and should be disabled after setup.
- Cross-station message sync is enabled on Pappy and Astrid/Liara for testing;
  Campbell/Olivea remains disabled until deliberately added.

## Data Flows

### Backup And Status

1. A station creates a local backup and a small operational status record.
2. Its station credential uploads them only to its assigned S3 prefix.
3. Pappy can review or restore the records using an adult AWS identity.

### Cross-Station Message

1. A sender builds and reviews a message using learned words and the keyer.
2. The station stores it locally, then uploads an immutable outbox record.
3. S3 invokes Lambda. Lambda validates the record and writes recipient inbox
   copies only to approved stations.
4. A receiver station downloads one idempotent copy when it is online.
5. Opening or decoding creates a receipt that Lambda routes back to the sender.

Related details:

- [Cloud messaging design](CLOUD_MESSAGING_DESIGN.md)
- [AWS backup and sync design](AWS_BACKUP_SYNC_DESIGN.md)
- [AWS setup reference](AWS_SETUP_REFERENCE.md)
- [Remote backup, status, and update runbook](REMOTE_BACKUP_STATUS_RUNBOOK.md)
- [Security and family data](../SECURITY.md)

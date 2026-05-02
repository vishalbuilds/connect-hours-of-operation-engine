# connect-hours-of-operation-engine

A custom Hours of Operation engine for **Amazon Connect** that enables dynamic, configurable time-based routing beyond AWS native capabilities. Built with AWS CDK (TypeScript), DynamoDB Global Tables, and a containerised AWS Lambda function (Python 3.11).

---

## Table of Contents

- [Project Status](#project-status)
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [CDK Configuration](#cdk-configuration)
- [Lambda Handler](#lambda-handler)
- [Environment Variables](#environment-variables)
- [DynamoDB Data Model](#dynamodb-data-model)
- [Sample Seed Data](#sample-seed-data)
- [Lambda Sample Input Data](#lambda-sample-input-data)
- [Development Commands](#development-commands)
- [Unit Tests](#unit-tests)
- [CI / CD](#ci--cd)
- [License](#license)

---

## Project Status

### Completed

| Component               | Description                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| ✅ CDK — DynamoDB       | DynamoDB Global Table stack with auto-scaling, PITR, TTL, and multi-region strong consistency                                     |
| ✅ Lambda function code | Python handler + helper modules (`parse_and_validate`, `payload_service`, `response_builder`, `dynamodb`) with Powertools logging |
| ✅ CDK — Lambda         | CDK construct to deploy the Lambda function from an ECR container image, IAM role, and DynamoDB read policy                       |
| ✅ Dockerfile — Lambda  | Container image for the Lambda function (Python 3.11 + dependencies)                                                             |
| ✅ Unit tests — Lambda  | Pytest suite covering handler layers, validation, expiry logic, DynamoDB client, and response builder (~167 tests)                |
| ✅ CI — CodeQL          | CodeQL Advanced security scanning for Python and TypeScript on every push and pull request                                        |

### Pending

| Component                      | Status  | Description                                                                    |
| ------------------------------ | ------- | ------------------------------------------------------------------------------ |
| GitHub Actions — Lambda deploy | Pending | Workflow to build and push the container image to ECR and deploy Lambda on push |
| CI — CDK                       | Pending | Workflow to run `cdk synth` + CDK unit tests on pull requests                  |
| CI — Lambda                    | Pending | Workflow to lint, type-check (mypy), and unit-test the Lambda source on PRs    |
| CI — Docker                    | Pending | Workflow to build and scan the Lambda container image on pull requests         |
| Sample test input data         | Pending | JSON event fixtures for happy-path, holiday, expired, and error scenarios      |

---

## Overview

Amazon Connect's native hours-of-operation feature is limited to simple weekly schedules. This engine replaces it with a fully configurable, DynamoDB-backed system that supports:

- Per-day time slots with individual capacity limits
- Timezone-aware scheduling (any IANA timezone)
- Holiday and exception overrides (national, regional, religious)
- Multi-calendar support (Gregorian, Hindu, Islamic)
- Queue-based exception routing

A Lambda function reads from DynamoDB at call time and determines whether the contact centre is open, returning a structured response that Amazon Connect contact flows use for routing decisions.

---

## Architecture

```
Amazon Connect Contact Flow
         │
         ▼
   AWS Lambda Function
   (hours-of-operation-checker)
   [Container image from ECR]
         │
         ▼
  DynamoDB Global Table
  (CCaS-Connect-Hours-Of-Operation-Table-Prod-Default)
  ┌─────────────────────────────────────┐
  │  Primary:  us-west-2                │
  │  Replica:  us-east-1                │
  │  Witness:  us-east-2 (strong sync)  │
  └─────────────────────────────────────┘
         │
   ┌─────┴──────────┐
   │                │
EXP#SCHEDULE  EXP#EXCEPTION  EXP#QUEUE
(weekly hours) (holidays)    (queue routing)
```

---

## Features

| Feature             | Details                                        |
| ------------------- | ---------------------------------------------- |
| Weekly schedules    | Per-day open/close times with named time slots |
| Capacity management | Per-slot capacity limits for load management   |
| Timezone support    | Fully timezone-aware (`Asia/Kolkata`, `America/New_York`, etc.) |
| Holiday exceptions  | Gazetted and regional holiday overrides        |
| Multi-calendar      | Gregorian, Hindu, Islamic calendar types       |
| Exception queues    | Date-scoped queue handlers per holiday         |
| Multi-region        | DynamoDB Global Tables with strong consistency |
| High availability   | Point-in-time recovery + deletion protection   |
| Auto-scaling writes | Write capacity auto-scales from 1 to 10        |
| TTL support         | Automatic expiry of stale schedule entries     |
| Containerised Lambda | Python 3.11 container image deployed via ECR  |
| Structured logging  | AWS Lambda Powertools JSON logging             |

---

## Project Structure

```
connect-hours-of-operation-engine/
├── cdk/                              # AWS CDK infrastructure (TypeScript)
│   ├── bin/
│   │   └── cdk.ts                   # CDK app entry point — version handler, stack instantiation
│   ├── lib/
│   │   ├── dynamodb-stack.ts        # DynamoDB Global Table construct
│   │   └── lambda-stacks.ts         # Lambda container deployment construct + IAM role
│   ├── test/
│   │   └── cdk.test.ts              # CDK unit tests (Jest)
│   ├── cdk.json                     # CDK context configuration (v1: us-west-2, v2: eu-west-1)
│   ├── package.json                 # Node.js dependencies
│   ├── tsconfig.json                # TypeScript configuration
│   ├── eslint.config.mjs            # ESLint configuration
│   └── jest.config.js               # Jest test configuration
├── src/                             # Lambda function source (Python 3.11)
│   ├── lambda_handler.py            # Main handler — 4-layer orchestration
│   ├── common/
│   │   ├── parse_and_validate.py   # Event parsing and timezone validation
│   │   ├── payload_service.py      # DynamoDB query, expiry, and key resolution
│   │   ├── response_builder.py     # Response envelope builder
│   │   └── dynamodb.py             # Boto3 DynamoDB client singleton
│   ├── test_unit/
│   │   ├── conftest.py             # Pytest fixtures and environment setup
│   │   ├── test_lambda_handler.py  # Handler integration tests (~75 tests)
│   │   ├── test_parse_and_validate.py
│   │   ├── test_payload_service.py
│   │   ├── test_dynamodb.py
│   │   └── test_response_builder.py
│   ├── requirements.txt             # Production: aws-lambda-powertools, boto3, botocore
│   └── requirements.dev..txt        # Development: pytest, pytest-cov
├── sample_seed_db_items/            # Sample DynamoDB seed data
│   ├── schedule.json                # Weekly schedule definitions (7+ items)
│   ├── exception.json               # Holiday exception definitions (10 items)
│   └── queue.json                   # Queue-to-schedule/exception mappings (10+ items)
├── .github/
│   └── workflows/
│       └── codeql.yml               # CodeQL Advanced security analysis
├── Dockerfile                       # Lambda container image (python:3.11 base)
├── .dockerignore
├── .gitignore
├── LICENSE
└── README.md
```

---

## Prerequisites

| Tool            | Minimum Version                                         |
| --------------- | ------------------------------------------------------- |
| Node.js         | 18.x                                                    |
| npm             | 9.x                                                     |
| AWS CDK CLI     | 2.x (`npm install -g aws-cdk`)                          |
| AWS CLI         | 2.x                                                     |
| AWS credentials | Configured via `aws configure` or environment variables |
| Docker          | Latest stable (for building / running the container image) |
| Python          | 3.11+ (local development and unit tests only)           |

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/vishalbuilds/connect-hours-of-operation-engine.git
cd connect-hours-of-operation-engine
```

### 2. Install CDK dependencies

```bash
cd cdk
npm install
```

### 3. Bootstrap your AWS account (first time only)

```bash
npx cdk bootstrap aws://<ACCOUNT_ID>/us-west-2
npx cdk bootstrap aws://<ACCOUNT_ID>/us-east-1
npx cdk bootstrap aws://<ACCOUNT_ID>/us-east-2
```

> All three regions must be bootstrapped because the stack uses a primary region (`us-west-2`), a replica (`us-east-1`), and a witness region (`us-east-2`) for strong consistency.

### 4. Deploy the stack

```bash
npx cdk deploy
```

### 5. Seed the DynamoDB table (optional)

Use the AWS CLI to batch-write the sample items:

```bash
aws dynamodb batch-write-item \
  --request-items file://../sample_seed_db_items/schedule.json \
  --region us-west-2

aws dynamodb batch-write-item \
  --request-items file://../sample_seed_db_items/exception.json \
  --region us-west-2

aws dynamodb batch-write-item \
  --request-items file://../sample_seed_db_items/queue.json \
  --region us-west-2
```

---

## CDK Configuration

All parameters are controlled via the `infraVersion` context block in [cdk/cdk.json](cdk/cdk.json). No code changes are required to tune a deployment. Two independent versions are pre-configured: `v1` (US, `us-west-2` primary) and `v2` (EU, `eu-west-1` primary).

### DynamoDB parameters

| Parameter                | Default (v1)                                            | Description                                |
| ------------------------ | ------------------------------------------------------- | ------------------------------------------ |
| `tableName`              | `CCaS-Connect-Hours-Of-Operation-Table-Prod-Default`    | DynamoDB table name                        |
| `partitionKeyName`       | `exp`                                                   | Partition key attribute name               |
| `sortKeyName`            | `id`                                                    | Sort key attribute name                    |
| `readCapacity`           | `5`                                                     | Fixed read capacity units                  |
| `minWriteCapacity`       | `1`                                                     | Auto-scale write minimum                   |
| `maxWriteCapacity`       | `10`                                                    | Auto-scale write maximum                   |
| `deletionProtection`     | `true`                                                  | Prevent accidental table deletion          |
| `removalPolicy`          | `RETAIN`                                                | CDK removal policy (`RETAIN` or `DESTROY`) |
| `pointInTimeRecovery`    | `true`                                                  | Enable PITR backups                        |
| `ttlAttribute`           | `ttl`                                                   | TTL attribute name for item expiry         |
| `multiRegionConsistency` | `STRONG`                                                | `STRONG` or `EVENTUAL`                     |
| `replicaRegions`         | `["us-east-1"]`                                         | List of replica regions                    |
| `witnessRegion`          | `us-east-2`                                             | Witness region (required for `STRONG`)     |

### Lambda parameters

| Parameter          | Description                                          |
| ------------------ | ---------------------------------------------------- |
| `functionName`     | Lambda function name                                 |
| `ecrRepositoryArn` | ECR repository ARN for the container image           |
| `imageTag`         | Docker image tag to deploy (default: `latest`)       |
| `description`      | Lambda description string                            |
| `environmentVariables` | Map of custom environment variables             |

> **Strong consistency requirement:** When `multiRegionConsistency` is `STRONG`, a `witnessRegion` must be provided and must differ from the primary and all replica regions.

### Override via CDK context flag

```bash
npx cdk deploy --context app='{"tableName":"MyTable","primaryRegion":"eu-west-1"}'
```

---

## Lambda Handler

The handler ([src/lambda_handler.py](src/lambda_handler.py)) processes every Amazon Connect invocation through four sequential layers:

```
Layer 1 — Event Validation
  ParseAndValidate extracts expression_type, id, time_zone, contact_id
  ├─ Validates required fields are present and non-empty
  ├─ Validates expression_type is whitelisted (QUEUE | PHONE_NUMBER)
  └─ Validates timezone via Python zoneinfo.ZoneInfo
         │ failure → ERROR response
         ▼
Layer 2 — Queue / Entity Lookup
  PayloadService fetches the queue/entity item from DynamoDB
  ├─ Checks expiry date (MM/DD/YYYY)
  │    └─ expired → CLOSED response
  └─ Checks for today's EXCEPTION key (EXCEPTION#MM/DD/YYYY)
         │ exception key found → Layer 3
         │ no exception key   → Layer 4
         ▼
Layer 3 — Exception / Holiday Check
  Fetches the referenced exception item
  ├─ Checks exception expiry
  │    └─ expired → continue to Layer 4
  └─ valid exception → OPEN response

Layer 4 — Schedule Check
  Fetches the schedule for today's day-of-week (SCHEDULE#Monday …)
  ├─ Checks schedule expiry
  │    └─ expired → CLOSED response
  └─ valid schedule → OPEN response
         │ not found → CLOSED response
```

### Response status codes

| Status    | Meaning                                                    |
| --------- | ---------------------------------------------------------- |
| `OPEN`    | Contact centre is open (valid schedule or exception found) |
| `CLOSED`  | Closed — queue/schedule expired or no schedule found       |
| `ERROR`   | Validation error — missing or invalid input parameters     |
| `HOLIDAY` | Available for extension (not currently returned)           |
| `MEETING` | Available for extension (not currently returned)           |

---

## Environment Variables

Set these on the Lambda function (via CDK `environmentVariables` context or directly in the console):

| Variable                   | Default                  | Description                              |
| -------------------------- | ------------------------ | ---------------------------------------- |
| `TABLE_NAME`               | _(required)_             | DynamoDB table name                      |
| `AWS_REGION`               | `us-west-2`              | DynamoDB region                          |
| `PK_NAME`                  | `pk`                     | Partition key attribute name             |
| `SK_NAME`                  | `sk`                     | Sort key attribute name                  |
| `POWERTOOLS_SERVICE_NAME`  | `hours-of-operation`     | AWS Lambda Powertools service name       |
| `LOG_LEVEL`                | `INFO`                   | Logging level (`DEBUG`, `INFO`, `ERROR`) |

> The unit-test fixtures in [src/test_unit/conftest.py](src/test_unit/conftest.py) set `TABLE_NAME=test-hoo-table`, `AWS_REGION=us-east-1`, `PK_NAME=pk`, `SK_NAME=sk`, and `LOG_LEVEL=ERROR`.

---

## DynamoDB Data Model

The table uses a single-table design with an **Entity-Expression (EXP#)** partition key pattern.

### Key schema

| Attribute     | Type   | Role                                                     |
| ------------- | ------ | -------------------------------------------------------- |
| `exp` (`pk`)  | String | Partition key — entity type prefix, e.g. `EXP#SCHEDULE` |
| `id` (`sk`)   | String | Sort key — unique identifier within entity type          |
| `payload`     | Map    | All business data for the item                           |
| `ttl`         | Number | Unix timestamp for automatic DynamoDB TTL expiry         |

> The `PK_NAME` and `SK_NAME` environment variables let you customise the attribute names without changing code.

---

### `EXP#SCHEDULE` — Weekly Operating Hours

One item per day of the week.

```
exp = "EXP#SCHEDULE"
id  = "SCHEDULE_MONDAY" | "SCHEDULE_TUESDAY" | ... | "SCHEDULE_SUNDAY"
```

`payload` fields:

| Field          | Type    | Description                               |
| -------------- | ------- | ----------------------------------------- |
| `day`          | String  | Short code: `MON`, `TUE`, ... `SUN`       |
| `dayFull`      | String  | Full name: `Monday`, ...                  |
| `dayIndex`     | Number  | 0 (Sunday) – 6 (Saturday)                 |
| `isWeekend`    | Boolean | Whether the day is a weekend              |
| `isWorkingDay` | Boolean | Whether the contact centre operates       |
| `openTime`     | String  | Opening time `HH:MM` (null if closed)     |
| `closeTime`    | String  | Closing time `HH:MM` (null if closed)     |
| `timezone`     | String  | IANA timezone, e.g. `Asia/Kolkata`        |
| `slots`        | Array   | Named time slots within the operating day |
| `status`       | String  | `ACTIVE`, `REDUCED`, or `CLOSED`          |
| `expireDate`   | String  | Expiry date `MM/DD/YYYY`                  |

Each slot within `slots`:

| Field      | Description                                    |
| ---------- | ---------------------------------------------- |
| `slotId`   | Unique slot ID, e.g. `SLOT#MON#AM`             |
| `label`    | Human label: `Morning`, `Afternoon`, `Evening` |
| `start`    | Slot start `HH:MM`                             |
| `end`      | Slot end `HH:MM`                               |
| `capacity` | Max concurrent contacts for this slot          |

---

### `EXP#EXCEPTION` — Holiday Definitions

One item per holiday event.

```
exp = "EXP#EXCEPTION"
id  = "EXCEPTION_NEW_YEAR" | "EXCEPTION_DIWALI" | ...
```

`payload` fields:

| Field               | Type    | Description                         |
| ------------------- | ------- | ----------------------------------- |
| `date`              | String  | Holiday date `DD/MM/YYYY`           |
| `description`       | String  | Human-readable holiday name         |
| `category`          | String  | `fix holiday` (fixed date)          |
| `region`            | String  | `national` or regional scope        |
| `calendarType`      | String  | `gregorian`, `hindu`, or `islamic`  |
| `isGazettedHoliday` | Boolean | Official government gazette status  |
| `affectedSchedules` | Array   | Schedule IDs this holiday overrides |
| `expireDate`        | String  | Expiry date `MM/DD/YYYY`            |

---

### `EXP#QUEUE` — Queue Handlers

One item per queue, mapping exception dates and day-of-week schedules to their respective DynamoDB sort keys.

```
exp = "EXP#QUEUE"
id  = "arn:aws:connect:<region>:<account>:instance/.../queue/..."
```

`payload` fields:

| Field                   | Type   | Description                                      |
| ----------------------- | ------ | ------------------------------------------------ |
| `queueName`             | String | Logical queue name                               |
| `description`           | String | What this queue covers                           |
| `EXCEPTION#MM/DD/YYYY`  | String | Reference to exception `id` for that date        |
| `SCHEDULE#<DayOfWeek>`  | String | Reference to schedule `id` for that day          |
| `expireDate`            | String | Queue handler expiry date `MM/DD/YYYY`           |

**Example queue payload:**

```json
{
  "exp": "EXP#QUEUE",
  "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/...",
  "payload": {
    "queueName": "Support_Chat",
    "EXCEPTION#01/01/2026": "EXCEPTION_NEW_YEAR",
    "SCHEDULE#Monday": "SCHEDULE_MONDAY",
    "SCHEDULE#Tuesday": "SCHEDULE_TUESDAY",
    "expireDate": "01/01/2027"
  }
}
```

---

## Sample Seed Data

Ready-to-load JSON files are provided in [sample_seed_db_items/](sample_seed_db_items/).

### schedule.json — Default weekly schedule

| Day       | Hours         | Slots                                       | Status  |
| --------- | ------------- | ------------------------------------------- | ------- |
| Mon – Fri | 09:00 – 18:00 | Morning / Afternoon / Evening (cap 50 each) | ACTIVE  |
| Saturday  | 10:00 – 14:00 | Morning / Afternoon (cap 25 each)           | REDUCED |
| Sunday    | Closed        | —                                           | CLOSED  |

Timezone: `Asia/Kolkata`

### exception.json — Indian national holidays (2026)

| Holiday          | Date       | Calendar  |
| ---------------- | ---------- | --------- |
| New Year's Day   | 01/01/2026 | Gregorian |
| Republic Day     | 26/01/2026 | Gregorian |
| Holi             | 14/03/2026 | Hindu     |
| Eid ul-Fitr      | 31/03/2026 | Islamic   |
| Good Friday      | 03/04/2026 | Gregorian |
| Independence Day | 15/08/2026 | Gregorian |
| Janmashtami      | 15/08/2026 | Hindu     |
| Gandhi Jayanti   | 02/10/2026 | Gregorian |
| Diwali           | 20/10/2026 | Hindu     |
| Christmas Day    | 25/12/2026 | Gregorian |

### queue.json — Queue handlers per holiday

Each queue handler maps a holiday exception to all seven day-of-week schedules and includes a one-year expiry date.

---

## Lambda Sample Input Data

The Lambda receives an Amazon Connect **Invoke AWS Lambda function** block event. All routing parameters are passed under `Details.Parameters`.

### Required parameters

| Parameter         | Required | Values                  | Description                                           |
| ----------------- | -------- | ----------------------- | ----------------------------------------------------- |
| `expression_type` | Yes      | `QUEUE`, `PHONE_NUMBER` | Entity type to look up in DynamoDB                    |
| `id`              | Yes      | Sort key value          | The `id` of the queue or phone number item            |
| `time_zone`       | Yes      | IANA tz string          | Timezone for schedule evaluation, e.g. `Asia/Kolkata` |
| `ContactId`       | No       | UUID                    | Amazon Connect contact ID for log correlation         |

### Full event structure

```json
{
  "Details": {
    "ContactData": {
      "Attributes": {},
      "Channel": "VOICE",
      "ContactId": "4a573372-1f28-4e26-b97b-XXXXXXXXXXX",
      "CustomerEndpoint": {
        "Address": "+1234567890",
        "Type": "TELEPHONE_NUMBER"
      },
      "InitiationMethod": "INBOUND",
      "InstanceARN": "arn:aws:connect:us-west-2:1234567890:instance/c8c0e68d-2200-4265-82c0-XXXXXXXXXX",
      "Queue": {
        "ARN": "arn:aws:connect:us-west-2:1234567890:instance/.../queue/...",
        "Name": "SupportQueue"
      }
    },
    "Parameters": {
      "ContactId": "4a573372-1f28-4e26-b97b-XXXXXXXXXXX",
      "expression_type": "QUEUE",
      "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/...",
      "time_zone": "Asia/Kolkata"
    }
  },
  "Name": "ContactFlowEvent"
}
```

---

### Scenario 1 — Normal working day (queue open)

```json
{
  "Details": {
    "ContactData": { "ContactId": "test-contact-001" },
    "Parameters": {
      "ContactId": "test-contact-001",
      "expression_type": "QUEUE",
      "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/general",
      "time_zone": "Asia/Kolkata"
    }
  }
}
```

**Expected response:**

```json
{
  "status": "OPEN",
  "message": "Schedule record",
  "payload": { "...": "schedule item payload" }
}
```

---

### Scenario 2 — Holiday / exception day

```json
{
  "Details": {
    "ContactData": { "ContactId": "test-contact-002" },
    "Parameters": {
      "ContactId": "test-contact-002",
      "expression_type": "QUEUE",
      "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/new-year",
      "time_zone": "Asia/Kolkata"
    }
  }
}
```

**Expected response:**

```json
{
  "status": "OPEN",
  "message": "Exception record",
  "payload": { "...": "exception item payload" }
}
```

---

### Scenario 3 — Queue expired

```json
{
  "Details": {
    "ContactData": { "ContactId": "test-contact-003" },
    "Parameters": {
      "ContactId": "test-contact-003",
      "expression_type": "QUEUE",
      "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/expired",
      "time_zone": "Asia/Kolkata"
    }
  }
}
```

**Expected response:**

```json
{
  "status": "CLOSED",
  "message": "Queue expired",
  "payload": {}
}
```

---

### Scenario 4 — Invalid / missing parameters

```json
{
  "Details": {
    "ContactData": { "ContactId": "test-contact-004" },
    "Parameters": {
      "ContactId": "test-contact-004",
      "expression_type": "",
      "id": "",
      "time_zone": "Asia/Kolkata"
    }
  }
}
```

**Expected response:**

```json
{
  "status": "ERROR",
  "message": "Invalid event parameters",
  "payload": {
    "expression_type": "",
    "id": "",
    "time_zone": "Asia/Kolkata",
    "contact_id": "test-contact-004"
  }
}
```

---

### Scenario 5 — Unsupported expression type

```json
{
  "Details": {
    "ContactData": { "ContactId": "test-contact-005" },
    "Parameters": {
      "ContactId": "test-contact-005",
      "expression_type": "UNKNOWN_TYPE",
      "id": "some-id",
      "time_zone": "Asia/Kolkata"
    }
  }
}
```

**Expected response:**

```json
{
  "status": "ERROR",
  "message": "Invalid event parameters",
  "payload": {
    "expression_type": "UNKNOWN_TYPE",
    "id": "some-id",
    "time_zone": "Asia/Kolkata",
    "contact_id": "test-contact-005"
  }
}
```

---

### Scenario 6 — Invalid timezone

```json
{
  "Details": {
    "ContactData": { "ContactId": "test-contact-006" },
    "Parameters": {
      "ContactId": "test-contact-006",
      "expression_type": "QUEUE",
      "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/general",
      "time_zone": "Not/ATimezone"
    }
  }
}
```

**Expected response:**

```json
{
  "status": "ERROR",
  "message": "Invalid event parameters",
  "payload": {
    "expression_type": "QUEUE",
    "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/general",
    "time_zone": "Not/ATimezone",
    "contact_id": "test-contact-006"
  }
}
```

---

### Testing locally

Invoke the handler directly:

```bash
cd src
python - <<'EOF'
import json
from lambda_handler import lambda_handler

event = {
    "Details": {
        "ContactData": {"ContactId": "local-test-001"},
        "Parameters": {
            "ContactId": "local-test-001",
            "expression_type": "QUEUE",
            "id": "arn:aws:connect:us-west-2:123456789012:instance/.../queue/general",
            "time_zone": "Asia/Kolkata"
        }
    }
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
EOF
```

---

## Development Commands

### CDK (from `cdk/`)

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run build

# Watch for changes
npm run watch

# Run CDK unit tests
npm run test

# Lint the code
npm run lint
npm run lint:fix

# Synthesize CloudFormation template (no deploy)
npx cdk synth

# Compare deployed stack with local changes
npx cdk diff

# Deploy to AWS
npx cdk deploy

# Destroy the stack (table is RETAINED by default)
npx cdk destroy
```

### Lambda (from repo root)

```bash
# Install development dependencies
pip install -r src/requirements.dev..txt

# Run all unit tests
pytest src/test_unit/ -v

# Run with coverage report
pytest src/test_unit/ --cov=src/common --cov-report=html

# Build the container image locally
docker build -t connect-hoo-engine .

# Run the container locally (requires AWS credentials)
docker run \
  -e TABLE_NAME=test-hoo-table \
  -e AWS_REGION=us-west-2 \
  -e PK_NAME=exp \
  -e SK_NAME=id \
  -p 9000:8080 \
  connect-hoo-engine
```

---

## Unit Tests

The Pytest suite in [src/test_unit/](src/test_unit/) covers all five modules:

| Test file                    | Module under test         | Approx. tests |
| ---------------------------- | ------------------------- | ------------- |
| `test_lambda_handler.py`     | `lambda_handler`          | ~75           |
| `test_parse_and_validate.py` | `common/parse_and_validate` | ~25          |
| `test_payload_service.py`    | `common/payload_service`  | ~40           |
| `test_dynamodb.py`           | `common/dynamodb`         | ~15           |
| `test_response_builder.py`   | `common/response_builder` | ~12           |
| **Total**                    |                           | **~167**      |

All external calls (DynamoDB `GetItem`) are mocked via `unittest.mock`. The `conftest.py` fixture resets the DynamoDB singleton before and after each test to prevent state leakage between test cases.

---

## CI / CD

### Active

| Workflow | Trigger | Scope |
| -------- | ------- | ----- |
| [CodeQL Advanced](.github/workflows/codeql.yml) | Push to `main`, pull requests, weekly schedule | Python + JavaScript/TypeScript static analysis |

### Planned

| Workflow | Trigger | Description |
| -------- | ------- | ----------- |
| Lambda deploy | Push to `main` | Build container, push to ECR, update Lambda |
| CDK CI | Pull requests | `cdk synth` + Jest unit tests |
| Lambda CI | Pull requests | Lint, mypy type-check, pytest |
| Docker CI | Pull requests | Container build + vulnerability scan |

---

## License

MIT — see [LICENSE](LICENSE).

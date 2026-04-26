# connect-hours-of-operation-engine

A custom Hours of Operation engine for **Amazon Connect** that enables dynamic, configurable time-based routing beyond AWS native capabilities. Built with AWS CDK (TypeScript), DynamoDB Global Tables, and AWS Lambda.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [CDK Configuration](#cdk-configuration)
- [DynamoDB Data Model](#dynamodb-data-model)
- [Sample Seed Data](#sample-seed-data)
- [Development Commands](#development-commands)
- [License](#license)

---

## Overview

Amazon Connect's native hours-of-operation feature is limited to simple weekly schedules. This engine replaces it with a fully configurable, DynamoDB-backed system that supports:

- Per-day time slots with individual capacity limits
- Timezone-aware scheduling
- Holiday and exception overrides (national, regional, religious)
- Multi-calendar support (Gregorian, Hindu, Islamic)
- Queue-based exception routing

A Lambda function (on the `Lambda-function` branch) reads from DynamoDB at call time and determines whether the contact center is open, returning a structured response that Amazon Connect contact flows use for routing decisions.

---

## Architecture

```
Amazon Connect Contact Flow
         │
         ▼
   AWS Lambda Function
   (hours-of-operation-checker)
         │
         ▼
  DynamoDB Global Table
  (HoursOfOperationTable)
  ┌─────────────────────────────────────┐
  │  Primary:  us-west-2                │
  │  Replica:  us-east-1                │
  │  Witness:  us-east-2 (strong sync)  │
  └─────────────────────────────────────┘
         │
   ┌─────┴──────┐
   │            │
EXP#SCHEDULE  EXP#EXCEPTION  EXP#QUEUE
(weekly hours) (holidays)    (exception routing)
```

---

## Features

| Feature | Details |
|---|---|
| Weekly schedules | Per-day open/close times with named time slots |
| Capacity management | Per-slot capacity limits for load management |
| Timezone support | Fully timezone-aware (`Asia/Kolkata`, etc.) |
| Holiday exceptions | Gazetted and regional holiday overrides |
| Multi-calendar | Gregorian, Hindu, Islamic calendar types |
| Exception queues | Date-scoped queue handlers per holiday |
| Multi-region | DynamoDB Global Tables with strong consistency |
| High availability | Point-in-time recovery + deletion protection |
| Auto-scaling writes | Write capacity auto-scales from 1 to 10 |
| TTL support | Automatic expiry of stale schedule entries |

---

## Project Structure

```
connect-hours-of-operation-engine/
├── cdk/                          # AWS CDK infrastructure (TypeScript)
│   ├── bin/
│   │   └── cdk.ts                # CDK app entry point
│   ├── lib/
│   │   └── cdk-stack.ts          # DynamoDBStack construct
│   ├── test/                     # CDK unit tests (Jest)
│   ├── cdk.json                  # CDK context configuration
│   ├── package.json
│   └── tsconfig.json
├── sample_seed_db_items/         # Sample DynamoDB seed data
│   ├── schedule.json             # Weekly schedule definitions (7 items)
│   ├── exception.json            # Holiday exception definitions (10 items)
│   └── queue.json                # Holiday queue handlers (10 items)
├── LICENSE
└── README.md
```

---

## Prerequisites

| Tool | Minimum Version |
|---|---|
| Node.js | 18.x |
| npm | 9.x |
| AWS CDK CLI | 2.x (`npm install -g aws-cdk`) |
| AWS CLI | 2.x |
| AWS credentials | Configured via `aws configure` or environment variables |

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

> Seed data is in the `sample_seed_db_items/` format — wrap each array in a `{ "HoursOfOperationTable": [...] }` envelope if using `batch-write-item` directly.

---

## CDK Configuration

All table parameters are controlled via the `context.app` block in [cdk/cdk.json](cdk/cdk.json). No code changes required to tune the deployment.

| Parameter | Default | Description |
|---|---|---|
| `primaryRegion` | `us-west-2` | AWS region for the primary table |
| `tableName` | `HoursOfOperationTable` | DynamoDB table name |
| `partitionKeyName` | `pk` | Partition key attribute name |
| `sortKeyName` | `sk` | Sort key attribute name |
| `readCapacity` | `5` | Fixed read capacity units |
| `minWriteCapacity` | `1` | Auto-scale write minimum |
| `maxWriteCapacity` | `10` | Auto-scale write maximum |
| `deletionProtection` | `true` | Prevent accidental table deletion |
| `removalPolicy` | `RETAIN` | CDK removal policy (`RETAIN` or `DESTROY`) |
| `pointInTimeRecovery` | `true` | Enable PITR backups |
| `ttlAttribute` | `ttl` | TTL attribute name for item expiry |
| `multiRegionConsistency` | `STRONG` | `STRONG` or `EVENTUAL` |
| `replicaRegions` | `["us-east-1"]` | List of replica regions |
| `witnessRegion` | `us-east-2` | Witness region (required for `STRONG`) |

> **Strong consistency requirement:** When `multiRegionConsistency` is `STRONG`, a `witnessRegion` must be provided and must differ from the primary and all replica regions.

### Override via CDK context flag

```bash
npx cdk deploy --context app='{"tableName":"MyTable","primaryRegion":"eu-west-1"}'
```

---

## DynamoDB Data Model

The table uses a single-table design with an **Entity-Expression (EXP#)** partition key pattern.

### Key Schema

| Attribute | Type | Role |
|---|---|---|
| `pk` (`exp`) | String | Partition key — entity type prefix, e.g. `EXP#SCHEDULE` |
| `sk` (`id`) | String | Sort key — unique identifier within entity type |
| `payload` | Map | All business data for the item |
| `ttl` | Number | Unix timestamp for automatic expiry |

### Entity Types

#### `EXP#SCHEDULE` — Weekly Operating Hours

One item per day of the week.

```
pk  = "EXP#SCHEDULE"
sk  = "SCHEDULE_MONDAY" | "SCHEDULE_TUESDAY" | ... | "SCHEDULE_SUNDAY"
```

`payload` fields:

| Field | Type | Description |
|---|---|---|
| `day` | String | Short code: `MON`, `TUE`, ... `SUN` |
| `dayFull` | String | Full name: `Monday`, ... |
| `dayIndex` | Number | 0 (Sunday) – 6 (Saturday) |
| `isWeekend` | Boolean | Whether the day is a weekend |
| `isWorkingDay` | Boolean | Whether the contact center operates |
| `openTime` | String | Opening time `HH:MM` (null if closed) |
| `closeTime` | String | Closing time `HH:MM` (null if closed) |
| `timezone` | String | IANA timezone, e.g. `Asia/Kolkata` |
| `slots` | Array | Named time slots within the operating day |
| `status` | String | `ACTIVE`, `REDUCED`, or `CLOSED` |

Each slot within `slots`:

| Field | Description |
|---|---|
| `slotId` | Unique slot ID, e.g. `SLOT#MON#AM` |
| `label` | Human label: `Morning`, `Afternoon`, `Evening` |
| `start` | Slot start `HH:MM` |
| `end` | Slot end `HH:MM` |
| `capacity` | Max concurrent contacts for this slot |

---

#### `EXP#EXCEPTION` — Holiday Definitions

One item per holiday event.

```
pk  = "EXP#EXCEPTION"
sk  = "EXCEPTION_NEW_YEAR" | "EXCEPTION_DIWALI" | ...
```

`payload` fields:

| Field | Type | Description |
|---|---|---|
| `date` | String | Holiday date `DD/MM/YYYY` |
| `description` | String | Human-readable holiday name |
| `category` | String | `fix holiday` (fixed date) |
| `region` | String | `national` or regional scope |
| `calendarType` | String | `gregorian`, `hindu`, or `islamic` |
| `isGazettedHoliday` | Boolean | Official government gazette status |
| `affectedSchedules` | Array | Schedule IDs this holiday overrides |

---

#### `EXP#QUEUE` — Holiday Exception Queue Handlers

One item per holiday, mapping exceptions to the weekly schedule identifiers.

```
pk  = "EXP#QUEUE"
sk  = "arn:aws:sqs:<region>:<account>:queue-<holiday>-handler"
```

`payload` fields:

| Field | Type | Description |
|---|---|---|
| `queueName` | String | Logical queue name |
| `description` | String | What this handler covers |
| `EXCEPTION#<date>` | String | Reference to the exception item ID |
| `SCHEDULE#<DOW>` | String | Reference to schedule for each day |
| `queueExpireDate` | String | Handler expiry date `DD/MM/YYYY` |

---

## Sample Seed Data

Ready-to-load JSON files are provided in [sample_seed_db_items/](sample_seed_db_items/).

### schedule.json — Default weekly schedule

| Day | Hours | Slots | Status |
|---|---|---|---|
| Mon – Fri | 09:00 – 18:00 | Morning / Afternoon / Evening (cap 50 each) | ACTIVE |
| Saturday | 10:00 – 14:00 | Morning / Afternoon (cap 25 each) | REDUCED |
| Sunday | Closed | — | CLOSED |

Timezone: `Asia/Kolkata`

### exception.json — Indian national holidays (2026)

| Holiday | Date | Calendar |
|---|---|---|
| New Year's Day | 01/01/2026 | Gregorian |
| Republic Day | 26/01/2026 | Gregorian |
| Holi | 14/03/2026 | Hindu |
| Eid ul-Fitr | 31/03/2026 | Islamic |
| Good Friday | 03/04/2026 | Gregorian |
| Independence Day | 15/08/2026 | Gregorian |
| Janmashtami | 15/08/2026 | Hindu |
| Gandhi Jayanti | 02/10/2026 | Gregorian |
| Diwali | 20/10/2026 | Hindu |
| Christmas Day | 25/12/2026 | Gregorian |

### queue.json — Queue handlers per holiday

Each queue handler maps a holiday exception to all seven day-of-week schedules and includes a one-year expiry date.

---

## Development Commands

Run these from inside the `cdk/` directory:

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run build

# Watch for changes
npm run watch

# Run unit tests
npm run test

# Lint the code
npm run lint

# Synthesize CloudFormation template (no deploy)
npx cdk synth

# Compare deployed stack with local changes
npx cdk diff

# Deploy to AWS
npx cdk deploy

# Destroy the stack (table is RETAINED by default)
npx cdk destroy
```

---

## License

MIT — see [LICENSE](LICENSE).

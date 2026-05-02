#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { DynamoDBStack } from "../lib/dynamodb-stack";
import { LambdaStack } from "../lib/lambda-stacks";

interface DynamoCfg {
  tableName?: string;
  partitionKeyName?: string;
  sortKeyName?: string;
  readCapacity?: number;
  minWriteCapacity?: number;
  maxWriteCapacity?: number;
  deletionProtection?: boolean;
  removalPolicy?: "RETAIN" | "DESTROY";
  pointInTimeRecovery?: boolean;
  ttlAttribute?: string;
  multiRegionConsistency?: "STRONG" | "EVENTUAL";
  replicaRegions?: string[];
  witnessRegion?: string;
}

interface LambdaCfg {
  functionName?: string;
  ecrRepositoryArn?: string;
  imageTag?: string;
  description?: string;
  environmentVariables?: Record<string, string>;
}

interface RegionCfg {
  dynamodb?: DynamoCfg;
  lambda?: LambdaCfg;
}

interface VersionConfig {
  awsRegion: string;
  awsAccount: string;
  [region: string]: RegionCfg | string;
}

const app = new cdk.App();

const cdkTags: Record<string, string> = app.node.tryGetContext("cdkTags") ?? {};
const infraVersion: Record<string, VersionConfig> = app.node.tryGetContext("infraVersion") ?? {};

function versionHandler(versionKey: string, versionCfg: VersionConfig): void {
  const awsRegion = versionCfg.awsRegion;
  const awsAccount = versionCfg.awsAccount;
  const regionCfg = (versionCfg[awsRegion] as RegionCfg) ?? {};
  const dynamoCfg: DynamoCfg = regionCfg.dynamodb ?? {};
  const lambdaCfg: LambdaCfg = regionCfg.lambda ?? {};

  const resourceTags: cdk.CfnTag[] = [
    ...Object.entries(cdkTags).map(([key, value]) => ({ key, value })),
    { key: "infraVersion", value: versionKey },
  ];

  new DynamoDBStack(app, `DynamoDBStack-${versionKey}`, {
    env: {
      account: awsAccount ?? process.env.CDK_DEFAULT_ACCOUNT,
      region: awsRegion ?? process.env.CDK_DEFAULT_REGION,
    },
    tableName: dynamoCfg.tableName ?? "HoursOfOperationTable",
    partitionKeyName: dynamoCfg.partitionKeyName ?? "exp",
    sortKeyName: dynamoCfg.sortKeyName ?? "id",
    readCapacity: dynamoCfg.readCapacity ?? 5,
    minWriteCapacity: dynamoCfg.minWriteCapacity ?? 1,
    maxWriteCapacity: dynamoCfg.maxWriteCapacity ?? 10,
    deletionProtection: dynamoCfg.deletionProtection ?? true,
    removalPolicy: dynamoCfg.removalPolicy ?? "RETAIN",
    pointInTimeRecovery: dynamoCfg.pointInTimeRecovery ?? true,
    ttlAttribute: dynamoCfg.ttlAttribute ?? "ttl",
    multiRegionConsistency: dynamoCfg.multiRegionConsistency ?? "STRONG",
    replicaRegions: dynamoCfg.replicaRegions ?? [],
    witnessRegion: dynamoCfg.witnessRegion,
    resourceTags,
  });

  new LambdaStack(app, `LambdaStack-${versionKey}`, {
    env: {
      account: awsAccount ?? process.env.CDK_DEFAULT_ACCOUNT,
      region: awsRegion ?? process.env.CDK_DEFAULT_REGION,
    },
    functionName: lambdaCfg.functionName ?? "",
    description: lambdaCfg.description ?? "",
    ecrRepositoryArn: lambdaCfg.ecrRepositoryArn ?? "",
    imageTag: lambdaCfg.imageTag ?? "latest",
    environment: {
      ...lambdaCfg.environmentVariables,
      infraVersion: versionKey,
    },
    resourceTags,
  });
}

for (const [versionKey, versionCfg] of Object.entries(infraVersion)) {
  versionHandler(versionKey, versionCfg);
}

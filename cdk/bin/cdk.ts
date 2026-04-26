#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { DynamoDBStack } from "../lib/cdk-stack";

const app = new cdk.App();
const cfg = app.node.tryGetContext("app") ?? {};

new DynamoDBStack(app, "DynamoDBStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: cfg.primaryRegion ?? process.env.CDK_DEFAULT_REGION,
  },
  tableName: cfg.tableName ?? "HoursOfOperationTable",
  partitionKeyName: cfg.partitionKeyName ?? "pk",
  sortKeyName: cfg.sortKeyName ?? "sk",
  readCapacity: cfg.readCapacity ?? 5,
  minWriteCapacity: cfg.minWriteCapacity ?? 1,
  maxWriteCapacity: cfg.maxWriteCapacity ?? 10,
  deletionProtection: cfg.deletionProtection ?? true,
  removalPolicy: cfg.removalPolicy ?? "RETAIN",
  pointInTimeRecovery: cfg.pointInTimeRecovery ?? true,
  ttlAttribute: cfg.ttlAttribute ?? "ttl",
  multiRegionConsistency: cfg.multiRegionConsistency ?? "STRONG",
  replicaRegions: cfg.replicaRegions ?? ["us-east-1"],
  witnessRegion: cfg.witnessRegion,
  resourceTags: cfg.resourceTags ?? [],
});

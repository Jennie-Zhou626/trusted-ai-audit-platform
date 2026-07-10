// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AuditRegistry {
    struct DatasetRecord {
        uint256 id;
        uint256 projectId;
        string datasetHash;
        string licenseType;
        address operator;
        uint256 createdAt;
    }

    struct TrainingTaskRecord {
        uint256 id;
        uint256 projectId;
        string datasetIds;
        string codeHash;
        string configHash;
        address operator;
        uint256 createdAt;
    }

    struct ModelVersionRecord {
        uint256 id;
        uint256 projectId;
        uint256 trainingTaskId;
        string modelHash;
        string metrics;
        address operator;
        uint256 createdAt;
    }

    struct TrainingRoundRecord {
        uint256 id;
        uint256 projectId;
        uint256 trainingTaskId;
        uint256 roundIndex;
        string organization;
        string gradientHash;
        string checkpointUri;
        string privacyMethod;
        address operator;
        uint256 createdAt;
    }

    struct AuditRecord {
        uint256 id;
        uint256 projectId;
        uint256 modelVersionId;
        string result;
        string reason;
        address operator;
        uint256 createdAt;
    }

    uint256 public datasetCount;
    uint256 public trainingTaskCount;
    uint256 public trainingRoundCount;
    uint256 public modelVersionCount;
    uint256 public auditRecordCount;

    mapping(uint256 => DatasetRecord) public datasets;
    mapping(uint256 => TrainingTaskRecord) public trainingTasks;
    mapping(uint256 => TrainingRoundRecord) public trainingRounds;
    mapping(uint256 => ModelVersionRecord) public modelVersions;
    mapping(uint256 => AuditRecord) public auditRecords;

    event DatasetRegistered(uint256 indexed id, uint256 indexed projectId, string datasetHash);
    event TrainingTaskRegistered(uint256 indexed id, uint256 indexed projectId, string codeHash, string configHash);
    event TrainingRoundCommitted(uint256 indexed id, uint256 indexed projectId, uint256 indexed trainingTaskId, uint256 roundIndex, string gradientHash);
    event ModelVersionRegistered(uint256 indexed id, uint256 indexed projectId, uint256 indexed trainingTaskId, string modelHash);
    event AuditRecordRegistered(uint256 indexed id, uint256 indexed projectId, uint256 indexed modelVersionId, string result);

    function registerDataset(
        uint256 projectId,
        string calldata datasetHash,
        string calldata licenseType
    ) external returns (uint256) {
        datasetCount += 1;
        datasets[datasetCount] = DatasetRecord(
            datasetCount,
            projectId,
            datasetHash,
            licenseType,
            msg.sender,
            block.timestamp
        );
        emit DatasetRegistered(datasetCount, projectId, datasetHash);
        return datasetCount;
    }

    function registerTrainingTask(
        uint256 projectId,
        string calldata datasetIds,
        string calldata codeHash,
        string calldata configHash
    ) external returns (uint256) {
        trainingTaskCount += 1;
        trainingTasks[trainingTaskCount] = TrainingTaskRecord(
            trainingTaskCount,
            projectId,
            datasetIds,
            codeHash,
            configHash,
            msg.sender,
            block.timestamp
        );
        emit TrainingTaskRegistered(trainingTaskCount, projectId, codeHash, configHash);
        return trainingTaskCount;
    }

    function commitTrainingRound(
        uint256 projectId,
        uint256 trainingTaskId,
        uint256 roundIndex,
        string calldata organization,
        string calldata gradientHash,
        string calldata checkpointUri,
        string calldata privacyMethod
    ) external returns (uint256) {
        trainingRoundCount += 1;
        trainingRounds[trainingRoundCount] = TrainingRoundRecord(
            trainingRoundCount,
            projectId,
            trainingTaskId,
            roundIndex,
            organization,
            gradientHash,
            checkpointUri,
            privacyMethod,
            msg.sender,
            block.timestamp
        );
        emit TrainingRoundCommitted(trainingRoundCount, projectId, trainingTaskId, roundIndex, gradientHash);
        return trainingRoundCount;
    }

    function registerModelVersion(
        uint256 projectId,
        uint256 trainingTaskId,
        string calldata modelHash,
        string calldata metrics
    ) external returns (uint256) {
        modelVersionCount += 1;
        modelVersions[modelVersionCount] = ModelVersionRecord(
            modelVersionCount,
            projectId,
            trainingTaskId,
            modelHash,
            metrics,
            msg.sender,
            block.timestamp
        );
        emit ModelVersionRegistered(modelVersionCount, projectId, trainingTaskId, modelHash);
        return modelVersionCount;
    }

    function registerAuditRecord(
        uint256 projectId,
        uint256 modelVersionId,
        string calldata result,
        string calldata reason
    ) external returns (uint256) {
        auditRecordCount += 1;
        auditRecords[auditRecordCount] = AuditRecord(
            auditRecordCount,
            projectId,
            modelVersionId,
            result,
            reason,
            msg.sender,
            block.timestamp
        );
        emit AuditRecordRegistered(auditRecordCount, projectId, modelVersionId, result);
        return auditRecordCount;
    }
}

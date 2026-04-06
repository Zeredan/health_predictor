package test.task.health_predictor

import test.task.model.MedicalCase

interface HealthPredictorRemoteDataSource {
    suspend fun predictNextCase(
        history: List<MedicalCase>,
        baseUrl: String,
    ): Pair<MedicalCase, Float>
}
package test.task.health_predictor

import test.task.model.MedicalCase

interface HealthPredictorRepository {
    suspend fun predictNextCase(history: List<MedicalCase>) : Pair<MedicalCase, Float>
}
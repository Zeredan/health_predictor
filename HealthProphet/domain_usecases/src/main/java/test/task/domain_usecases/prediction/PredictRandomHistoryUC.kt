package test.task.domain_usecases.prediction

import test.task.domain_usecases.model.PredictionResult
import test.task.health_predictor.HealthPredictorRepository
import test.task.histories_with_targets.HistoriesWithTargetsRepository
import test.task.model.MedicalCase
import javax.inject.Inject

class PredictRandomHistoryUC @Inject constructor(
    private val historiesWithTargetsRepository: HistoriesWithTargetsRepository,
    private val healthPredictorRepository: HealthPredictorRepository
) {
    suspend operator fun invoke() : PredictionResult {
        val (history, target) = historiesWithTargetsRepository.getRandomHistoryWithTarget()
        val prediction = healthPredictorRepository.predictNextCase(history)
        return PredictionResult(history, target, prediction.first, prediction.second)
    }
}
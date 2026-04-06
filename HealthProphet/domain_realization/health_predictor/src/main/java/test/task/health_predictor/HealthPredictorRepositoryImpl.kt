package test.task.health_predictor

import kotlinx.coroutines.flow.first
import test.task.model.MedicalCase
import test.task.settings.SettingsRepository
import javax.inject.Inject


class HealthPredictorRepositoryImpl @Inject constructor(
    private val healthPredictorRemoteDataSource: HealthPredictorRemoteDataSource,
    private val settingsRepository: SettingsRepository
): HealthPredictorRepository {
    override suspend fun predictNextCase(history: List<MedicalCase>): Pair<MedicalCase, Float> {
        val baseUrl = settingsRepository.getBaseUrlAsFlow().first()
        return healthPredictorRemoteDataSource.predictNextCase(history, baseUrl)
    }
}
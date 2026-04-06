package test.task.histories

import test.task.histories_local.HistoriesLocalDataSource
import test.task.model.MedicalCase
import javax.inject.Inject

class HistoriesRepositoryImpl @Inject constructor(
    private val historiesLocalDataSource: HistoriesLocalDataSource
): HistoriesRepository {
    override suspend fun getRandomHistory(): List<MedicalCase> {
        return historiesLocalDataSource.getRandomHistoryWithTarget().first
    }
}
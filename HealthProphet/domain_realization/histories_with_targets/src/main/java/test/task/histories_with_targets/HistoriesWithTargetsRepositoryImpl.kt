package test.task.histories_with_targets

import test.task.histories_local.HistoriesLocalDataSource
import test.task.model.MedicalCase
import javax.inject.Inject

class HistoriesWithTargetsRepositoryImpl @Inject constructor(
    private val historiesLocalDataSource: HistoriesLocalDataSource
): HistoriesWithTargetsRepository {

    override suspend fun getRandomHistoryWithTarget(): Pair<List<MedicalCase>, MedicalCase> {
        return historiesLocalDataSource.getRandomHistoryWithTarget()
    }
}
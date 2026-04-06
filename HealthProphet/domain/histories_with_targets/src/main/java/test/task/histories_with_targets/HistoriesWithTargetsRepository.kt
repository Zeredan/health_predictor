package test.task.histories_with_targets

import test.task.model.MedicalCase

interface HistoriesWithTargetsRepository {
    suspend fun getRandomHistoryWithTarget(): Pair<List<MedicalCase>, MedicalCase>
}
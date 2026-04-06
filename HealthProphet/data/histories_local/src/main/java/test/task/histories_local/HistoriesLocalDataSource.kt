package test.task.histories_local

import test.task.model.MedicalCase

interface HistoriesLocalDataSource {
    suspend fun getRandomHistoryWithTarget(): Pair<List<MedicalCase>, MedicalCase>
}
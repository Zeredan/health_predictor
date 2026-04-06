package test.task.histories

import test.task.model.MedicalCase

interface HistoriesRepository {
    suspend fun getRandomHistory(): List<MedicalCase>
}
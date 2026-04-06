package test.task.settings_local

import kotlinx.coroutines.flow.Flow
import test.task.model.HealthTheme

interface SettingsLocalDataSource {
    suspend fun setAppTheme(value: HealthTheme)
    fun getAppThemeAsFlow() : Flow<HealthTheme>

    suspend fun setBaseUrl(value: String)
    fun getBaseUrlAsFlow() : Flow<String>
}
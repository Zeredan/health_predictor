package test.task.settings

import kotlinx.coroutines.flow.Flow
import test.task.model.HealthTheme
import test.task.settings_local.SettingsLocalDataSource
import javax.inject.Inject

class SettingsRepositoryImpl @Inject constructor(
    private val settingsLocalDataSource: SettingsLocalDataSource
) : SettingsRepository {
    override suspend fun setAppTheme(value: HealthTheme) {
        settingsLocalDataSource.setAppTheme(value)
    }
    override fun getAppThemeAsFlow(): Flow<HealthTheme> {
        return settingsLocalDataSource.getAppThemeAsFlow()
    }

    override suspend fun setBaseUrl(value: String) {
        settingsLocalDataSource.setBaseUrl(value)
    }
    override fun getBaseUrlAsFlow(): Flow<String> {
        return settingsLocalDataSource.getBaseUrlAsFlow()
    }
}
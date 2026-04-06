package test.task.settings_local

import android.content.Context
import android.content.res.Configuration
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import test.task.model.HealthTheme
import javax.inject.Inject

class SettingsLocalDataSourceImpl @Inject constructor(
    @ApplicationContext private val appContext: Context,
    private val dataStore: DataStore<Preferences>
) : SettingsLocalDataSource {
    private object PreferencesKeys {
        val APP_THEME = androidx.datastore.preferences.core.stringPreferencesKey("app_theme")
        val BASE_URL = androidx.datastore.preferences.core.stringPreferencesKey("base_url")
    }
    override suspend fun setAppTheme(value: HealthTheme) {
        dataStore.edit {
            it[PreferencesKeys.APP_THEME] = value.name
        }
    }
    override fun getAppThemeAsFlow(): Flow<HealthTheme> {
        return dataStore.data.map { preferences ->
            val stored = preferences[PreferencesKeys.APP_THEME]

            if (stored != null) {
                return@map HealthTheme.valueOf(stored)
            }

            val nightMode = appContext.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK

            return@map when (nightMode) {
                Configuration.UI_MODE_NIGHT_YES -> HealthTheme.DARK
                Configuration.UI_MODE_NIGHT_NO -> HealthTheme.LIGHT
                Configuration.UI_MODE_NIGHT_UNDEFINED -> HealthTheme.DARK
                else -> HealthTheme.DARK
            }
        }
    }

    override suspend fun setBaseUrl(value: String) {
        dataStore.edit {
            it[PreferencesKeys.BASE_URL] = value
        }
    }
    override fun getBaseUrlAsFlow(): Flow<String> {
        return dataStore.data.map { preferences ->
            val stored = preferences[PreferencesKeys.BASE_URL]
            return@map stored ?: ""
        }
    }
}
package test.task.domain_usecases.settings

import test.task.model.HealthTheme
import test.task.settings.SettingsRepository
import javax.inject.Inject

class SetAppThemeUC @Inject constructor(
    private val settingsRepository: SettingsRepository
) {
    suspend operator fun invoke(value: HealthTheme) = settingsRepository.setAppTheme(value)
}
package test.task.domain_usecases.settings

import test.task.settings.SettingsRepository
import javax.inject.Inject

class SetBaseUrlUC @Inject constructor(
    private val settingsRepository: SettingsRepository
) {
    suspend operator fun invoke(value: String) = settingsRepository.setBaseUrl(value)
}
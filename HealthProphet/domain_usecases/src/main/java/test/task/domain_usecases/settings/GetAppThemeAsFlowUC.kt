package test.task.domain_usecases.settings

import test.task.settings.SettingsRepository
import javax.inject.Inject

class GetAppThemeAsFlowUC @Inject constructor(
    private val settingsRepository: SettingsRepository
) {
    operator fun invoke() = settingsRepository.getAppThemeAsFlow()
}
package test.task.feature

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import test.task.domain_usecases.settings.GetAppThemeAsFlowUC
import test.task.domain_usecases.settings.GetBaseUrlAsFlowUC
import test.task.domain_usecases.settings.SetAppThemeUC
import test.task.domain_usecases.settings.SetBaseUrlUC
import test.task.model.HealthTheme
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val getAppThemeAsFlowUC: GetAppThemeAsFlowUC,
    private val setAppThemeUC: SetAppThemeUC,
    private val getBaseUrlAsFlowUC: GetBaseUrlAsFlowUC,
    private val setBaseUrlUC: SetBaseUrlUC
) : ViewModel(){
    val appThemeFlow = getAppThemeAsFlowUC()
        .stateIn(viewModelScope, SharingStarted.Eagerly, HealthTheme.DARK)

    private val _baseUrl = MutableStateFlow("")
    val baseUrl: StateFlow<String> = _baseUrl.asStateFlow()

    init {
        viewModelScope.launch {
            _baseUrl.value = getBaseUrlAsFlowUC().first()
        }
    }

    fun setAppTheme(theme: HealthTheme) {
        viewModelScope.launch {
            setAppThemeUC(theme)
        }
    }

    fun setBaseUrl(baseUrl: String) {
        viewModelScope.launch {
            _baseUrl.value = baseUrl
            setBaseUrlUC(baseUrl)
        }
    }
}
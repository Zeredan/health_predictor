package test.task.healthprophet

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import test.task.domain_usecases.settings.GetAppThemeAsFlowUC
import test.task.healthprophet.ui.MainNavigationRoot
import test.task.model.HealthTheme
import test.task.ui.themes.HealthColorScheme
import test.task.ui.themes.HealthIconScheme
import test.task.ui.themes.HealthThemeManager
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject
    lateinit var ucGetAppThemeAsFlow: GetAppThemeAsFlowUC

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // Привязываю тему из domain-слоя, чтобы всегда в :core:ui была актуальная и реактивная тема
        lifecycleScope.launch {
            ucGetAppThemeAsFlow().collect { appTheme ->
                HealthThemeManager.colorScheme.value = when(appTheme){
                    HealthTheme.DARK -> HealthColorScheme.DARK
                    HealthTheme.LIGHT -> HealthColorScheme.LIGHT
                }
                HealthThemeManager.iconScheme.value = when(appTheme){
                    HealthTheme.DARK -> HealthIconScheme.DARK
                    HealthTheme.LIGHT -> HealthIconScheme.LIGHT
                }
                HealthThemeManager.isInitialized.value = true
            }
        }
        // Жду инициализацию темы, лишь потом привязываю контент
        lifecycleScope.launch {
            HealthThemeManager.isInitialized.first{ it }

            setContent {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    MainNavigationRoot(
                        modifier = Modifier.padding(innerPadding),
                        deferredsToWait = listOf()
                    )
                }
            }
        }
    }
}
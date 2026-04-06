package test.task.healthprophet.ui

import android.annotation.SuppressLint
import android.content.res.Configuration
import androidx.activity.ComponentActivity
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import test.task.feature.SettingsViewModel
import test.task.predict_simple.PredictSimpleFeatureRoot
import test.task.predict_with_check.PredictWithCheckFeatureRoot
import test.task.predict_with_check.PredictWithCheckViewModel
import test.task.settings.SettingsFeatureRoot
import test.task.splash.SplashFeatureRoot
import test.task.ui.themes.HealthColorScheme
import test.task.ui.themes.HealthThemeManager
import java.util.Locale

@SuppressLint("NewApi", "ContextCastToActivity")
@Composable
fun MainNavigationRoot(
    modifier: Modifier = Modifier,
    deferredsToWait: List<Deferred<Any>>,
) {
    val coroutineScope = rememberCoroutineScope()
    val navController = rememberNavController()
    // Создаю вьюмодели тут, а не внутри фичи - для предотвращения мерцания UI и пре-расчетов
    val settingsViewModel: SettingsViewModel = hiltViewModel()
    val predictWithCheckViewModel: PredictWithCheckViewModel = hiltViewModel()
    val colorScheme by HealthThemeManager.colorScheme.collectAsState()

    //val selectedLanguage by settingsViewModel.selectedLanguageStateFlow.collectAsState()
    val activity = LocalContext.current as ComponentActivity

    activity.window.navigationBarColor = colorResource(colorScheme.bgPrimary).toArgb()
    activity.window.statusBarColor = colorResource(colorScheme.bgPrimary).toArgb()
    NavHost(
        modifier = modifier
            .fillMaxSize()
            .background(colorResource(colorScheme.bgPrimary)),
        navController = navController,
        startDestination = ScreenState.SPLASH,
        enterTransition = {
            fadeIn(tween(0))
        },
        exitTransition = {
            fadeOut(tween(0))
        }
    ) {
        composable(ScreenState.SPLASH) {
            LaunchedEffect(1) {
                coroutineScope.launch {
                    val simpleWaiter = coroutineScope.async {
                        delay(1000)
                    }
                    deferredsToWait.forEach { it.await() }
                    simpleWaiter.await()
                    navController.navigate(ScreenState.PREDICT_WITH_CHECK) {
                        popUpTo(ScreenState.SPLASH) {
                            inclusive = true
                        }
                    }
                }
            }
            SplashFeatureRoot(

            )
        }
        composable(ScreenState.PREDICT_SIMPLE) {
            PredictSimpleFeatureRoot(
                onNavigateToPredictWithCheck = {
                    navController.navigate(ScreenState.PREDICT_WITH_CHECK) {
                        popUpTo(ScreenState.PREDICT_SIMPLE) {
                            inclusive = false
                        }
                    }
                },
                onNavigateToSettings = {
                    navController.navigate(ScreenState.SETTINGS) {
                        popUpTo(ScreenState.PREDICT_SIMPLE) {
                            inclusive = false
                        }
                    }
                }
            )
        }
        composable(ScreenState.PREDICT_WITH_CHECK) {
            PredictWithCheckFeatureRoot(
                vm = predictWithCheckViewModel,
                onNavigateToPredictSimple = {
                    navController.navigate(ScreenState.PREDICT_SIMPLE) {
                        popUpTo(ScreenState.PREDICT_SIMPLE) {
                            inclusive = true
                        }
                    }
                },
                onNavigateToSettings = {
                    navController.navigate(ScreenState.SETTINGS) {
                        popUpTo(ScreenState.PREDICT_SIMPLE) {
                            inclusive = false
                        }
                    }
                }
            )
        }
        composable(ScreenState.SETTINGS) {
            SettingsFeatureRoot(
                vm = settingsViewModel,
                onNavigateToPredictSimple = {
                    navController.navigate(ScreenState.PREDICT_SIMPLE) {
                        popUpTo(ScreenState.PREDICT_SIMPLE) {
                            inclusive = true
                        }
                    }
                },
                onNavigateToPredictWithCheck = {
                    navController.navigate(ScreenState.PREDICT_WITH_CHECK) {
                        popUpTo(ScreenState.PREDICT_SIMPLE) {
                            inclusive = false
                        }
                    }
                }
            )
        }
    }
}

fun applySelectedLanguage(
    activity: ComponentActivity,
    lang: String
) {
    with(activity) {
        println("QFASA: $lang | ${resources.configuration.locales[0]}")
        resources.apply {
            val locale = Locale(lang)
            val config = Configuration(configuration)

            createConfigurationContext(configuration)
            Locale.setDefault(locale)
            config.setLocale(locale)
            resources.updateConfiguration(config, displayMetrics)
        }
    }
}

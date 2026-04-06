package test.task.ui.themes


import androidx.compose.ui.text.font.FontWeight
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import kotlinx.coroutines.flow.MutableStateFlow
import test.task.ui.R

object HealthThemeManager {
    val colorScheme = MutableStateFlow<HealthColorScheme>(HealthColorScheme.DARK)
    val iconScheme = MutableStateFlow<HealthIconScheme>(HealthIconScheme.DARK)
    var isInitialized = MutableStateFlow(false)
    @Composable fun RobotoFontFamily() : FontFamily {
        return FontFamily(
            Font(R.font.roboto_regular, FontWeight.W400),
            Font(R.font.roboto_medium, FontWeight.W500),
            Font(R.font.roboto_semibold, FontWeight.W600)
        )
    }
}
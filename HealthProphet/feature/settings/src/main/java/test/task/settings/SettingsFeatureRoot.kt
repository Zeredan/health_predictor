package test.task.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.flow.collect
import test.task.feature.SettingsViewModel
import test.task.model.HealthTheme
import test.task.ui.NavigationMenu
import test.task.ui.R
import test.task.ui.themes.HealthThemeManager

@Composable
fun SettingsFeatureRoot(
    modifier: Modifier = Modifier,
    vm: SettingsViewModel,
    onNavigateToPredictSimple: () -> Unit,
    onNavigateToPredictWithCheck: () -> Unit,
) {
    val context = LocalContext.current
    val focusManager = LocalFocusManager.current

    val colorScheme by HealthThemeManager.colorScheme.collectAsState()
    val iconScheme by HealthThemeManager.iconScheme.collectAsState()
    val robotoFontFamily = HealthThemeManager.RobotoFontFamily()

    val appTheme by vm.appThemeFlow.collectAsState()

    val baseUrl by vm.baseUrl.collectAsState()

    Column(
        modifier = modifier
            .fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Column(
            modifier = modifier
                .weight(1f)
                .background(colorResource(colorScheme.bgPrimary))
                .padding(horizontal = 16.dp)
                .pointerInput(key1 = Unit) {
                    this.detectTapGestures {
                        focusManager.clearFocus(true)
                    }
                },
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                modifier = Modifier
                    .align(Alignment.Start)
                    .padding(top = 8.dp),
                text = stringResource(R.string.settings),
                color = colorResource(colorScheme.textPrimary),
                fontSize = 22.sp,
                fontFamily = robotoFontFamily
            )
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = baseUrl,
                onValueChange = { vm.setBaseUrl(it) },
                label = {
                    Text(
                        text = stringResource(R.string.base_url_placeholder),
                        color = colorResource(colorScheme.textPrimary),
                        fontSize = 16.sp,
                        fontFamily = robotoFontFamily
                    )
                },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = colorResource(colorScheme.textFieldBgFocused),
                    unfocusedContainerColor = colorResource(colorScheme.textFieldBgUnfocused),
                    focusedIndicatorColor = colorResource(colorScheme.textFieldBorderFocused),
                    unfocusedIndicatorColor = colorResource(colorScheme.textFieldBorderUnfocused),
                    cursorColor = colorResource(colorScheme.textFieldCursor),
                    focusedTextColor = colorResource(colorScheme.textPrimary),
                    unfocusedTextColor = colorResource(colorScheme.textPrimary),
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp)
            )
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = stringResource(R.string.dark_mode),
                    color = colorResource(colorScheme.textPrimary),
                    fontSize = 16.sp,
                    fontFamily = robotoFontFamily
                )
                Switch(
                    checked = appTheme == HealthTheme.DARK,
                    onCheckedChange = {
                        vm.setAppTheme(if (it) HealthTheme.DARK else HealthTheme.LIGHT)
                    },
                    colors = SwitchDefaults.colors(
                        uncheckedTrackColor = colorResource(colorScheme.switchUncheckedTrack),
                        checkedTrackColor = colorResource(colorScheme.switchCheckedTrack),
                        uncheckedThumbColor = colorResource(colorScheme.switchUncheckedThumb),
                        checkedThumbColor = colorResource(colorScheme.switchCheckedThumb)
                    )
                )
            }
        }
        NavigationMenu(
            activeItem = 2,
            onSelect = {
                when(it) {
                    0 -> onNavigateToPredictSimple()
                    1 -> onNavigateToPredictWithCheck()
                }
            }
        )
    }
}
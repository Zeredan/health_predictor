package test.task.ui

import androidx.activity.ComponentActivity
import androidx.annotation.DrawableRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import test.task.ui.themes.HealthThemeManager

@Composable
internal fun NavigationItem(
    modifier: Modifier = Modifier,
    active: Boolean,
    text: String,
    @DrawableRes activeImage: Int,
    @DrawableRes inactiveImage: Int,
    onClick: () -> Unit
) {
    val colorScheme by HealthThemeManager.colorScheme.collectAsState()
    val robotoFontFamily = HealthThemeManager.RobotoFontFamily()
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .run {
                if (!active) clickable(onClick = onClick) else this
            }
            .padding(8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(64.dp, 32.dp)
                .clip(RoundedCornerShape(16.dp))
                .run {
                    if (active) background(colorResource(colorScheme.navigationSelectedBg)) else this
                },
            contentAlignment = Alignment.Center
        ) {
            Image(
                modifier = Modifier.size(24.dp),
                painter = painterResource(if (active) activeImage else inactiveImage),
                contentDescription = null
            )
        }
        Spacer(Modifier.height(4.dp))
        Text(
            text = text,
            fontSize = 15.sp,
            color = colorResource(if (active) colorScheme.navigationSelectedText else colorScheme.textPrimary),
            fontFamily = robotoFontFamily,
            fontWeight = FontWeight.W600,
        )
    }
}

@Composable
fun NavigationMenu(
    modifier: Modifier = Modifier,
    activeItem: Int,
    onSelect: (Int) -> Unit
) {
    val context = LocalContext.current as ComponentActivity

    val colorScheme by HealthThemeManager.colorScheme.collectAsState()
    val iconScheme by HealthThemeManager.iconScheme.collectAsState()
    val robotoFontFamily = HealthThemeManager.RobotoFontFamily()

    val navBarColor = colorResource(colorScheme.navigationBg).toArgb()

    LaunchedEffect(navBarColor) {
        val window = context.window
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.navigationBarColor = navBarColor
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(80.dp)
            .background(colorResource(colorScheme.navigationBg)),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically
    ) {
        NavigationItem(
            active = activeItem == 0,
            text = stringResource(R.string.menu_predict_simple),
            activeImage = iconScheme.iconPredictSimpleActive,
            inactiveImage = iconScheme.iconPredictSimpleInactive,
            onClick = {
                onSelect(0)
            }
        )
        NavigationItem(
            active = activeItem == 1,
            text = stringResource(R.string.menu_predict_with_check),
            activeImage = iconScheme.iconPredictWithCheckActive,
            inactiveImage = iconScheme.iconPredictWithCheckInactive,
            onClick = {
                onSelect(1)
            }
        )
        NavigationItem(
            active = activeItem == 2,
            text = stringResource(R.string.menu_settings),
            activeImage = iconScheme.iconSettingsActive,
            inactiveImage = iconScheme.iconSettingsInactive,
            onClick = {
                onSelect(2)
            }
        )
    }
}
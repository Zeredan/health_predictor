package test.task.ui

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import test.task.ui.themes.HealthThemeManager

@Composable
fun TableCell(
    modifier: Modifier = Modifier,
    text: String,
    topLeftBorder: Dp = 0.dp,
    topRightBorder: Dp = 0.dp,
    bottomLeftBorder: Dp = 0.dp,
    bottomRightBorder: Dp = 0.dp,
) {
    val context = LocalContext.current
    val colorScheme by HealthThemeManager.colorScheme.collectAsState()
    val iconScheme by HealthThemeManager.iconScheme.collectAsState()
    val robotoFontFamily = HealthThemeManager.RobotoFontFamily()

    Box(
        modifier = Modifier
            .size(100.dp, 50.dp)
            .border(
                2.dp,
                colorResource(colorScheme.borderPrimary),
                RoundedCornerShape(topLeftBorder, topRightBorder, bottomRightBorder, bottomLeftBorder)
            )
            .padding(10.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            color = colorResource(colorScheme.textTableHeader),
            fontSize = 16.sp,
            fontFamily = robotoFontFamily
        )
    }
}
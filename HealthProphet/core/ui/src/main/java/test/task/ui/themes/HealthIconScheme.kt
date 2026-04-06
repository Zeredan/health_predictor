package test.task.ui.themes

import androidx.annotation.DrawableRes
import test.task.ui.R

enum class HealthIconScheme(
    @DrawableRes val iconPredictSimpleActive: Int,
    @DrawableRes val iconPredictSimpleInactive: Int,
    @DrawableRes val iconSettingsActive: Int,
    @DrawableRes val iconSettingsInactive: Int,
    @DrawableRes val iconPredictWithCheckActive: Int,
    @DrawableRes val iconPredictWithCheckInactive: Int,
    @DrawableRes val iconLogo: Int,
) {
    DARK(
        iconPredictSimpleActive = R.drawable.emptystar,
        iconPredictSimpleInactive = R.drawable.emptystar,
        iconSettingsActive = R.drawable.emptystar,
        iconSettingsInactive = R.drawable.emptystar,
        iconLogo = R.drawable.emptystar,
        iconPredictWithCheckActive = R.drawable.emptystar,
        iconPredictWithCheckInactive = R.drawable.emptystar,
    ),
    LIGHT(
        iconPredictSimpleActive = R.drawable.emptystar,
        iconPredictSimpleInactive = R.drawable.emptystar,
        iconSettingsActive = R.drawable.emptystar,
        iconSettingsInactive = R.drawable.emptystar,
        iconLogo = R.drawable.emptystar,
        iconPredictWithCheckActive = R.drawable.emptystar,
        iconPredictWithCheckInactive = R.drawable.emptystar,
    )
}
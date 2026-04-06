package test.task.predict_with_check

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import test.task.ui.NavigationMenu
import test.task.ui.R
import test.task.ui.TableCell
import test.task.ui.themes.HealthThemeManager
import java.math.BigDecimal
import java.math.RoundingMode

@Composable
fun PredictWithCheckFeatureRoot(
    modifier: Modifier = Modifier,
    vm: PredictWithCheckViewModel,
    onNavigateToPredictSimple: () -> Unit,
    onNavigateToSettings: () -> Unit,
) {
    val context = LocalContext.current
    val colorScheme by HealthThemeManager.colorScheme.collectAsState()
    val iconScheme by HealthThemeManager.iconScheme.collectAsState()
    val robotoFontFamily = HealthThemeManager.RobotoFontFamily()

    val isLoading by vm.isLoading.collectAsState()
    val history by vm.history.collectAsState()
    val target by vm.target.collectAsState()
    val prediction by vm.prediction.collectAsState()
    val death by vm.death.collectAsState()

    Column(
        modifier = modifier
            .fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Column(
            modifier = modifier
                .weight(1f)
                .fillMaxWidth()
                .background(colorResource(colorScheme.bgPrimary))
                .padding(horizontal = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                modifier = Modifier
                    .align(Alignment.Start)
                    .padding(top = 8.dp),
                text = stringResource(R.string.predict_with_check),
                color = colorResource(colorScheme.textPrimary),
                fontSize = 22.sp,
                fontFamily = robotoFontFamily
            )
            Spacer(modifier = Modifier.height(16.dp))
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(0.5f)
                        .height(56.dp)
                        .clip(RoundedCornerShape(15.dp))
                        .background(colorResource(colorScheme.loadButton))
                        .clickable {
                            vm.predict()
                        },
                    contentAlignment = Alignment.Center
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier
                                .size(32.dp),
                            strokeWidth = 3.dp,
                            color = colorResource(colorScheme.progressBar),
                            strokeCap = StrokeCap.Round
                        )
                    } else {
                        Text(
                            text = stringResource(R.string.predict),
                            color = colorResource(colorScheme.textPrimary),
                            fontSize = 16.sp,
                            fontFamily = robotoFontFamily
                        )
                    }
                }
                Spacer(modifier = Modifier.height(32.dp))
                if (!isLoading && target != null && prediction != null) {
                    Text(
                        modifier = Modifier
                            .align(Alignment.Start),
                        text = stringResource(R.string.history),
                        color = colorResource(colorScheme.textPrimary),
                        fontSize = 18.sp,
                        fontFamily = robotoFontFamily
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(15.dp))
                            .border(
                                2.dp,
                                colorResource(colorScheme.borderPrimary),
                                RoundedCornerShape(15.dp)
                            ),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(
                            horizontalAlignment = Alignment.Start
                        ) {
                            TableCell(
                                text = "№",
                                topLeftBorder = 15.dp,
                            )
                            listOf(
                                R.string.age,
                                R.string.sex,
                                R.string.is_dead,
                                R.string.season,
                                R.string.diagnosis,
                                R.string.service,
                                R.string.group,
                                R.string.profile,
                                R.string.result,
                                R.string.type,
                                R.string.form,
                            ).apply {
                                this.forEachIndexed { ind, feature ->
                                    TableCell(
                                        text = stringResource(feature),
                                        bottomLeftBorder = if (ind == this.size - 1) 15.dp else 0.dp,
                                    )
                                }
                            }
                        }
                        Row(
                            modifier = Modifier
                                .weight(1f)
                                .horizontalScroll(rememberScrollState()),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            history.forEachIndexed { caseInd, case ->
                                Column(
                                    horizontalAlignment = Alignment.Start
                                ) {
                                    TableCell(
                                        text = (caseInd + 1).toString(),
                                        topRightBorder = if (caseInd == history.size - 1) 15.dp else 0.dp,
                                    )
                                    listOf(
                                        case.age,
                                        case.sex,
                                        case.isDead,
                                        case.season,
                                        case.diagnoses,
                                        case.service,
                                        case.group,
                                        case.profile,
                                        case.result,
                                        case.type,
                                        case.form,
                                    ).apply {
                                        this.forEachIndexed { ind, feature ->
                                            TableCell(
                                                text = feature.toString(),
                                                bottomRightBorder = if ((caseInd == history.size - 1) && (ind == this.size - 1)) 15.dp else 0.dp,
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        modifier = Modifier
                            .align(Alignment.Start),
                        text = stringResource(R.string.target),
                        color = colorResource(colorScheme.textPrimary),
                        fontSize = 18.sp,
                        fontFamily = robotoFontFamily
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(15.dp))
                            .border(
                                2.dp,
                                colorResource(colorScheme.borderPrimary),
                                RoundedCornerShape(15.dp)
                            ),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(
                            horizontalAlignment = Alignment.Start
                        ) {
                            TableCell(
                                text = "№",
                                topLeftBorder = 15.dp,
                            )
                            listOf(
                                R.string.age,
                                R.string.sex,
                                R.string.is_dead,
                                R.string.diagnosis,
                                R.string.service,
                                R.string.group,
                                R.string.profile,
                                R.string.result,
                                R.string.type,
                                R.string.form,
                            ).apply {
                                this.forEachIndexed { ind, feature ->
                                    TableCell(
                                        text = stringResource(feature),
                                        bottomLeftBorder = if (ind == this.size - 1) 15.dp else 0.dp,
                                    )
                                }
                            }
                        }
                        Row(
                            modifier = Modifier
                                .weight(1f)
                                .horizontalScroll(rememberScrollState()),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            mapOf(
                                prediction!! to R.string.prediction,
                                target!! to R.string.target
                            ).forEach { (case, nameId) ->
                                Column(
                                    horizontalAlignment = Alignment.Start
                                ) {
                                    TableCell(
                                        text = stringResource(nameId),
                                        topRightBorder = if (nameId == R.string.target) 15.dp else 0.dp,
                                    )
                                    listOf(
                                        case.age,
                                        case.sex,
                                        case.isDead,
                                        case.diagnoses,
                                        case.service,
                                        case.group,
                                        case.profile,
                                        case.result,
                                        case.type,
                                        case.form,
                                    ).apply {
                                        this.forEachIndexed { ind, feature ->
                                            TableCell(
                                                text = feature.toString(),
                                                bottomRightBorder = if ((nameId == R.string.target) && (ind == this.size - 1)) 15.dp else 0.dp,
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(16.dp))
                    Text(
                        modifier = Modifier
                            .align(Alignment.Start),
                        text = "${stringResource(R.string.death_prob)}: ${ BigDecimal(death.toDouble() * 100).setScale(8, RoundingMode.HALF_EVEN)}%",
                        color = colorResource(colorScheme.textPrimary),
                        fontSize = 18.sp,
                        fontFamily = robotoFontFamily
                    )
                    Spacer(Modifier.height(32.dp))
                }
            }
        }
        NavigationMenu(
            activeItem = 1,
            onSelect = {
                when (it) {
                    0 -> onNavigateToPredictSimple()
                    2 -> onNavigateToSettings()
                }
            }
        )
    }
}
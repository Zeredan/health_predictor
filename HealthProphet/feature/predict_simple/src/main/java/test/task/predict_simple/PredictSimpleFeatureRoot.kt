package test.task.predict_simple

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel

@Composable
fun PredictSimpleFeatureRoot(
    modifier: Modifier = Modifier,
    vm: PredictSimpleViewModel = hiltViewModel(),
    onNavigateToPredictWithCheck: () -> Unit,
    onNavigateToSettings: () -> Unit,
) {

}
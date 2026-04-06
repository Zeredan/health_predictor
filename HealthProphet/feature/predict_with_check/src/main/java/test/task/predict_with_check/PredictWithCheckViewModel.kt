package test.task.predict_with_check

import android.content.Context
import android.widget.Toast
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import test.task.domain_usecases.prediction.PredictRandomHistoryUC
import test.task.model.MedicalCase
import javax.inject.Inject

@HiltViewModel
class PredictWithCheckViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val predictRandomHistoryUC: PredictRandomHistoryUC
) : ViewModel(){
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()

    private val _history = MutableStateFlow<List<MedicalCase>>(emptyList())
    val history = _history.asStateFlow()

    private val _target = MutableStateFlow<MedicalCase?>(null)
    val target = _target.asStateFlow()

    private val _prediction = MutableStateFlow<MedicalCase?>(null)
    val prediction = _prediction.asStateFlow()

    private val _death = MutableStateFlow(0f)
    val death = _death.asStateFlow()

    fun predict() {
        _isLoading.value = true
        viewModelScope.launch {
            try {
                val (h, t, p, d) = predictRandomHistoryUC()
                _history.value = h
                _target.value = t
                _prediction.value = p
                _death.value = d
                _isLoading.value = false
            } catch (e: Exception) {
                println("EEEE" + e.message)
                _isLoading.value = false
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
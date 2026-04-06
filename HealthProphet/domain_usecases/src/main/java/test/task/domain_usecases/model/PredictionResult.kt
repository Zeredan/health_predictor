package test.task.domain_usecases.model

import test.task.model.MedicalCase

class PredictionResult(
    val history: List<MedicalCase>,
    val target: MedicalCase,
    val prediction: MedicalCase,
    val death: Float
) {
    operator fun component1() = history
    operator fun component2() = target
    operator fun component3() = prediction
    operator fun component4() = death
}
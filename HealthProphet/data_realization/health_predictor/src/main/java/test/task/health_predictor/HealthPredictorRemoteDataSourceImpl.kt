package test.task.health_predictor

import com.google.gson.Gson
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import test.task.model.MedicalCase
import javax.inject.Inject

data class PredictionRequest(
    val window_age: List<Float>,
    val window_sex: List<Int>,
    val window_is_dead: List<Int>,
    val window_season: List<Int>,
    val window_diagnosis: List<List<String>>,
    val window_service: List<String>,
    val window_group: List<String>,
    val window_profile: List<String>,
    val window_result: List<String>,
    val window_type: List<String>,
    val window_form: List<String>,
    val enp: String? = null
)

// Ответ - только нужные поля
data class PredictionResponse(
    val success: Boolean,
    val predictions: List<Prediction>
)

data class Prediction(
    val patient_id: String,
    val predictions: PredictionResult,
    val probabilities: ProbabilitiesResult,
)

data class ProbabilitiesResult(
    val death: Float
)

data class PredictionResult(
    val is_dead: Int,
    val diagnosis_full: String,
    val service_full: String,
    val group: String,
    val profile: String,
    val result: String,
    val type: String,
    val form: String,
    val season: Int
)

class HealthPredictorRemoteDataSourceImpl @Inject constructor(
    private val httpClient: HttpClient,
) : HealthPredictorRemoteDataSource {
    private val gson: Gson = Gson()


    override suspend fun predictNextCase(
        history: List<MedicalCase>,
        baseUrl: String
    ): Pair<MedicalCase, Float> {
        // 1. Создаем запрос
        val request = PredictionRequest(
            window_age = history.map { it.age },
            window_sex = history.map { it.sex },
            window_is_dead = history.map { it.isDead },
            window_season = history.map { it.season },
            window_diagnosis = history.map { it.diagnoses },
            window_service = history.map { it.service },
            window_group = history.map { it.group },
            window_profile = history.map { it.profile },
            window_result = history.map { it.result },
            window_type = history.map { it.type },
            window_form = history.map { it.form },
            enp = history.firstOrNull()?.enp
        )

        // 2. Отправляем и получаем ответ
        val responseJson: String = httpClient.post("$baseUrl/predict") {
            contentType(ContentType.Application.Json)
            setBody(gson.toJson(request))
        }.body()

        // 3. Парсим ответ
        val response = gson.fromJson(responseJson, PredictionResponse::class.java)

        // 4. Берем первое предсказание
        val pred = response.predictions.first().predictions
        val prob = response.predictions.first().probabilities

        // 5. Возвращаем результат
        return MedicalCase(
            enp = response.predictions.first().patient_id,
            age = history.last().age,
            sex = pred.is_dead,
            isDead = pred.is_dead,
            season = pred.season,
            diagnoses = listOf(pred.diagnosis_full),
            service = pred.service_full,
            group = pred.group,
            profile = pred.profile,
            result = pred.result,
            type = pred.type,
            form = pred.form
        ) to prob.death
    }
}
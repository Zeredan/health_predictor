package test.task.histories_local

import android.content.Context
import android.os.Build
import androidx.annotation.RequiresApi
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import test.task.model.MedicalCase
import java.io.BufferedReader
import java.io.InputStreamReader
import java.time.LocalDate
import java.time.format.DateTimeFormatterBuilder
import javax.inject.Inject
import kotlin.random.Random

data class PatientWindow(
    val history: List<MedicalCase>,  // окно истории
    val target: MedicalCase           // целевой случай
)

data class PatientData(
    val enp: String,
    val cases: List<MedicalCase>
)

@RequiresApi(Build.VERSION_CODES.O)
class HistoriesLocalDataSourceImpl @Inject constructor(
    @ApplicationContext private val appContext: Context
) : HistoriesLocalDataSource {
    private val coroutineScope = CoroutineScope(Dispatchers.Default)
    // Параметры окон (как в нейросети)
    private val minSequenceLength = 10
    private val maxSequenceLength = 30
    private val windowStride = 5

    // Состояние
    private val windows = MutableStateFlow<List<PatientWindow>>(emptyList())

    // Форматтер для дат
    @RequiresApi(Build.VERSION_CODES.O)
    private val dateFormatter = DateTimeFormatterBuilder()
        .appendPattern("dd.MM.uuuu")
        .toFormatter()

    init {
        coroutineScope.launch {
            loadData()
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private suspend fun loadData() {
        try {
            val patients = readPatientsFromTsv()

            val allWindows = generateWindows(patients)

            windows.value = allWindows

            println("✅ HistoriesLocalDataSource: загружено ${patients.size} пациентов, ${allWindows.size} окон")

        } catch (e: Exception) {
            println("❌ Ошибка загрузки данных: ${e.message}")
            windows.value = emptyList()
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun readPatientsFromTsv(): List<PatientData> {
        val patients = mutableMapOf<String, MutableList<MedicalCase>>()

        val inputStream = appContext.resources.openRawResource(R.raw.example_dataset1)

        BufferedReader(InputStreamReader(inputStream, "UTF-8")).use { reader ->
            val header = reader.readLine()?.split("\t") ?: return emptyList()

            // Индексы колонок
            val enpIdx = header.indexOf("ENP")
            val sexIdx = header.indexOf("SEX")
            val ageIdx = header.indexOf("AGE")
            val diagnosisIdx = header.indexOf("DIAGNOSIS")
            val serviceIdx = header.indexOf("SERVICE")
            val groupIdx = header.indexOf("GROUP")
            val profileIdx = header.indexOf("PROFILE")
            val resultIdx = header.indexOf("RESULT")
            val typeIdx = header.indexOf("TYPE")
            val formIdx = header.indexOf("FORM")
            val isDeadIdx = header.indexOf("IS_DEAD")
            val dateIdx = header.indexOf("CASE_START_DATE")

            // Читаем строки
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                val parts = line!!.split("\t")
                if (parts.size <= 1) continue

                try {
                    val enp = parts.getOrNull(enpIdx) ?: continue
                    val sex = parts.getOrNull(sexIdx)?.toIntOrNull() ?: 0
                    val age = parts.getOrNull(ageIdx)?.toFloatOrNull() ?: 0f
                    val diagnosis = parts.getOrNull(diagnosisIdx) ?: ""
                    val service = parts.getOrNull(serviceIdx) ?: ""
                    val group = parts.getOrNull(groupIdx) ?: ""
                    val profile = parts.getOrNull(profileIdx) ?: ""
                    val result = parts.getOrNull(resultIdx) ?: ""
                    val type = parts.getOrNull(typeIdx) ?: ""
                    val form = parts.getOrNull(formIdx) ?: ""
                    val isDead = parts.getOrNull(isDeadIdx)?.toIntOrNull() ?: 0

                    // Определяем сезон из даты
                    val dateStr = parts.getOrNull(dateIdx) ?: ""
                    val season = parseSeasonFromDate(dateStr)

                    // Обрабатываем диагнозы (разделяем по пробелам)
                    val diagnoses = if (diagnosis.isNotBlank()) {
                        diagnosis.split(" ").filter { it.isNotBlank() }
                    } else {
                        emptyList()
                    }

                    val medicalCase = MedicalCase(
                        enp = enp,
                        age = age,
                        sex = sex,
                        isDead = isDead,
                        season = season,
                        diagnoses = diagnoses,
                        service = service,
                        group = group,
                        profile = profile,
                        result = result,
                        type = type,
                        form = form
                    )

                    patients.getOrPut(enp) { mutableListOf() }.add(medicalCase)

                } catch (e: Exception) {
                    // Пропускаем некорректные строки
                }
            }
        }

        return patients.map { (enp, cases) ->
            PatientData(enp, cases)
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun parseSeasonFromDate(dateStr: String): Int {
        if (dateStr.isBlank()) return 1

        return try {
            val date = LocalDate.parse(dateStr, dateFormatter)
            val month = date.monthValue

            when (month) {
                12, 1, 2 -> 2  // зима
                3, 4, 5 -> 3    // весна
                6, 7, 8 -> 4    // лето
                9, 10, 11 -> 5  // осень
                else -> 1
            }
        } catch (e: Exception) {
            1 // дефолтный сезон
        }
    }

    private fun generateWindows(patients: List<PatientData>): List<PatientWindow> {
        val windows = mutableListOf<PatientWindow>()

        for (patient in patients) {
            val cases = patient.cases
            val nCases = cases.size

            if (nCases <= minSequenceLength) continue

            val maxLen = if (maxSequenceLength > 0) {
                minOf(maxSequenceLength, nCases - 1)
            } else {
                nCases - 1
            }

            // Перебираем стартовые позиции
            for (startIdx in 0 until (nCases - minSequenceLength) step windowStride) {
                // Перебираем размеры окна
                for (windowSize in minSequenceLength..minOf(maxLen, nCases - startIdx) step windowStride) {
                    val endIdx = startIdx + windowSize

                    if (endIdx < nCases) {
                        val history = cases.subList(startIdx, endIdx)
                        val target = cases[endIdx]
                        windows.add(PatientWindow(history, target))
                    }
                }
            }
        }

        return windows
    }

    override suspend fun getRandomHistoryWithTarget(): Pair<List<MedicalCase>, MedicalCase> {
        // Ждем пока данные загрузятся
        val allWindows = windows.first{ it.isNotEmpty() }

        if (allWindows.isEmpty()) {
            throw IllegalStateException("Нет доступных окон")
        }

        // Выбираем случайное окно
        val randomIndex = Random.nextInt(allWindows.size)
        val window = allWindows[randomIndex]

        return Pair(window.history, window.target)
    }
}
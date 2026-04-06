package test.task.model

data class MedicalCase(
    // Идентификатор пациента (опционально)
    val enp: String? = null,

    // Основные признаки
    val age: Float,                    // возраст пациента
    val sex: Int,                     // пол: 0 - женский, 1 - мужской
    val isDead: Int,                   // статус: 0 - жив, 1 - умер
    val season: Int,                   // сезон: 0-5 (зима, весна, лето, осень)

    // Диагнозы (множественные для одного визита)
    val diagnoses: List<String>,       // список кодов диагнозов

    val service: String,        // код услуги

    // Категориальные признаки
    val group: String,                  // группа
    val profile: String,                // профиль
    val result: String,                 // результат
    val type: String,                   // тип
    val form: String,                   // форма
)
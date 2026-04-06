package test.task.health_predictor.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import test.task.health_predictor.HealthPredictorRepository
import test.task.health_predictor.HealthPredictorRepositoryImpl
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HealthPredictorRepositoryHiltModule {
    @Binds
    @Singleton
    abstract fun bindHealthPredictorRepository(impl: HealthPredictorRepositoryImpl): HealthPredictorRepository
}
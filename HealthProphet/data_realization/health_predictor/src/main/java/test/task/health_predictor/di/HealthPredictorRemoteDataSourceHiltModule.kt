package test.task.health_predictor.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import test.task.health_predictor.HealthPredictorRemoteDataSource
import test.task.health_predictor.HealthPredictorRemoteDataSourceImpl
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HealthPredictorRemoteDataSourceHiltModule {
    @Binds
    @Singleton
    abstract fun bindHealthPredictorRemoteDataSource(impl: HealthPredictorRemoteDataSourceImpl): HealthPredictorRemoteDataSource
}